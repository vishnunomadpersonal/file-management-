"""
Text-to-SQL Engine for FileVault AI Chatbot
============================================
Converts natural language questions to SQL queries using LLM.
Includes safety layer, access control, and query execution.
"""

import re
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# ============================================================================
# Database Schema Context for LLM
# ============================================================================

DATABASE_SCHEMA = """
You have access to a MySQL database with the following tables:

### Table: users
- id (VARCHAR 36, PK) - User's unique ID
- name (VARCHAR 255) - User's full name
- email (VARCHAR 255, UNIQUE) - User's email address
- role (VARCHAR 50) - Role: 'super_admin', 'org_admin', 'manager', 'user', 'viewer'
- status (VARCHAR 50) - Status: 'pending', 'approved', 'rejected', 'active'
- organization_id (VARCHAR 36, FK -> organizations.id) - User's organization
- created_at (DATETIME) - When user was created
- updated_at (DATETIME) - When user was last updated

### Table: files
- id (VARCHAR 36, PK) - File's unique ID
- filename (VARCHAR 255) - Original filename
- user_id (VARCHAR 36, FK -> users.id) - Who uploaded the file
- organization_id (VARCHAR 36, FK -> organizations.id) - Which organization owns it
- folder_id (VARCHAR 36, FK -> folders.id) - Parent folder (NULL = root)
- path (VARCHAR 255) - Storage path
- content_type (VARCHAR 32) - MIME type (e.g., 'image/png', 'application/pdf')
- size (INTEGER) - File size in bytes
- virus_scan_status (VARCHAR 20) - 'pending', 'clean', 'infected', 'error', 'disabled'
- virus_scan_date (DATETIME) - When virus scan was performed
- is_quarantined (BOOLEAN) - If file is quarantined
- quarantine_reason (VARCHAR 500) - Why file was quarantined
- created_at (DATETIME) - Upload timestamp

### Table: organizations
- id (VARCHAR 36, PK) - Organization's unique ID
- name (VARCHAR 255) - Organization name
- slug (VARCHAR 100, UNIQUE) - URL-friendly name
- email (VARCHAR 255) - Contact email
- plan (VARCHAR 50) - 'free', 'pro', 'enterprise'
- storage_quota_bytes (BIGINT) - Storage limit in bytes
- storage_used_bytes (BIGINT) - Storage used in bytes
- max_users (INTEGER) - Maximum allowed users
- max_files (INTEGER) - Maximum allowed files
- is_active (BOOLEAN) - If organization is active
- is_verified (BOOLEAN) - If organization is verified
- created_at (DATETIME) - When created
- updated_at (DATETIME) - When last updated

### Table: folders
- id (VARCHAR 36, PK) - Folder's unique ID
- name (VARCHAR 255) - Folder name
- organization_id (VARCHAR 36, FK -> organizations.id) - Which organization
- parent_folder_id (VARCHAR 36, FK -> folders.id) - Parent folder (NULL = root)
- created_by_user_id (VARCHAR 36, FK -> users.id) - Who created it
- created_at (DATETIME) - When created
- updated_at (DATETIME) - When last updated

### Table: appointments
- id (VARCHAR 36, PK) - Appointment's unique ID
- user_id (VARCHAR 36, FK -> users.id) - Associated user
- status (VARCHAR 50) - Appointment status
- created_at (DATETIME) - When created

### Common Relationships:
- files.user_id -> users.id (who uploaded)
- files.organization_id -> organizations.id (which org owns it)
- users.organization_id -> organizations.id (user's org)
- folders.organization_id -> organizations.id
"""

# ============================================================================
# SQL Generation Prompt
# ============================================================================

SQL_GENERATION_PROMPT = """You are a SQL expert. Generate a MySQL query to answer the user's question.

{schema}

### Rules:
1. ONLY generate SELECT queries - never INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE
2. Always use table aliases for clarity (e.g., u for users, f for files)
3. Limit results to 50 rows maximum unless user specifies otherwise
4. Use appropriate JOINs when data spans multiple tables
5. Format dates nicely using DATE_FORMAT() when displaying
6. Use human-readable column aliases (e.g., "File Name" instead of filename)
7. For file sizes, you can return raw bytes - the system will format them
8. Always include ORDER BY for consistent results
9. Use COALESCE for nullable fields when appropriate

### Access Control:
{access_control}

### User's Question:
{question}

### Response Format:
Return ONLY the SQL query, nothing else. No explanations, no markdown, just the raw SQL.
If the question cannot be answered with the available schema, return: ERROR: <reason>
If the question is ambiguous, return: CLARIFY: <what you need to know>
"""

# ============================================================================
# Safety Validator
# ============================================================================

class SQLSafetyValidator:
    """Validates SQL queries for safety before execution."""
    
    # Dangerous keywords that should never appear
    FORBIDDEN_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE',
        'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'CALL',
        'INTO OUTFILE', 'INTO DUMPFILE', 'LOAD_FILE', 'LOAD DATA',
        '--', '/*', '*/', 'UNION ALL SELECT', 'INFORMATION_SCHEMA',
        'SLEEP(', 'BENCHMARK(', 'WAITFOR', 'pg_sleep'
    ]
    
    # Allowed tables
    ALLOWED_TABLES = ['users', 'files', 'organizations', 'folders', 'appointments']
    
    @classmethod
    def validate(cls, sql: str) -> Tuple[bool, str]:
        """
        Validate SQL query for safety.
        Returns (is_safe, error_message)
        """
        if not sql or not sql.strip():
            return False, "Empty query"
        
        sql_upper = sql.upper().strip()
        
        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            return False, "Only SELECT queries are allowed"
        
        # Check for forbidden keywords
        for keyword in cls.FORBIDDEN_KEYWORDS:
            if keyword.upper() in sql_upper:
                return False, f"Forbidden keyword detected: {keyword}"
        
        # Check for multiple statements (;)
        # Allow semicolon only at the very end
        semicolon_count = sql.count(';')
        if semicolon_count > 1:
            return False, "Multiple statements not allowed"
        if semicolon_count == 1 and not sql.strip().endswith(';'):
            return False, "Semicolon only allowed at end of query"
        
        # Check for subqueries that might be dangerous
        if sql_upper.count('SELECT') > 3:
            return False, "Too many nested subqueries"
        
        return True, ""
    
    @classmethod
    def add_row_limit(cls, sql: str, max_rows: int = 50) -> str:
        """Add or enforce row limit on query."""
        sql_upper = sql.upper().strip()
        
        # Remove trailing semicolon for processing
        if sql.strip().endswith(';'):
            sql = sql.strip()[:-1]
        
        # Check if LIMIT already exists
        if 'LIMIT' in sql_upper:
            # Extract existing limit and enforce max
            limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
            if limit_match:
                existing_limit = int(limit_match.group(1))
                if existing_limit > max_rows:
                    sql = re.sub(r'LIMIT\s+\d+', f'LIMIT {max_rows}', sql, flags=re.IGNORECASE)
        else:
            sql = f"{sql} LIMIT {max_rows}"
        
        return sql


# ============================================================================
# Access Control Layer
# ============================================================================

class AccessControlLayer:
    """Adds role-based access control to SQL queries."""
    
    @staticmethod
    def get_access_control_context(user_context: Dict[str, Any]) -> str:
        """Generate access control instructions for LLM based on user role."""
        role = user_context.get('role', 'user')
        user_id = user_context.get('user_id', '')
        org_id = user_context.get('organization_id', '')
        
        if role in ['super_admin', 'platform_admin']:
            return """You have FULL ACCESS to all data across all organizations.
No filtering required - you can query any table without restrictions."""
        
        elif role in ['org_admin', 'admin']:
            return f"""You have ORGANIZATION-LEVEL access.
IMPORTANT: Always add these filters:
- For files: WHERE f.organization_id = '{org_id}'
- For users: WHERE u.organization_id = '{org_id}'
- For folders: WHERE folders.organization_id = '{org_id}'
You can see all data within organization '{org_id}' only."""
        
        else:  # Regular user, manager, viewer
            return f"""You have USER-LEVEL access only.
IMPORTANT: Always add these filters:
- For files: WHERE f.user_id = '{user_id}'
- For users: Only show the current user (WHERE u.id = '{user_id}')
- You cannot query other users' data
Organization ID for context: '{org_id}'"""
    
    @staticmethod
    def enforce_access_control(sql: str, user_context: Dict[str, Any]) -> str:
        """
        Post-process SQL to enforce access control.
        This is a safety net in case LLM doesn't add proper filters.
        """
        role = user_context.get('role', 'user')
        user_id = user_context.get('user_id', '')
        org_id = user_context.get('organization_id', '')
        
        # Super admin has no restrictions
        if role in ['super_admin', 'platform_admin']:
            return sql
        
        sql_upper = sql.upper()
        
        # For org_admin, ensure org filter exists for relevant tables
        if role in ['org_admin', 'admin'] and org_id:
            # Check if querying files without org filter
            if 'FILES' in sql_upper or ' F ' in sql_upper or 'F.' in sql_upper:
                if 'ORGANIZATION_ID' not in sql_upper:
                    # Add org filter
                    if 'WHERE' in sql_upper:
                        sql = re.sub(r'WHERE', f"WHERE (f.organization_id = '{org_id}' OR files.organization_id = '{org_id}') AND", sql, count=1, flags=re.IGNORECASE)
                    else:
                        # Find position to insert WHERE
                        sql = _insert_where_clause(sql, f"(f.organization_id = '{org_id}' OR files.organization_id = '{org_id}')")
        
        # For regular users, ensure user filter exists
        elif user_id:
            if 'FILES' in sql_upper or ' F ' in sql_upper or 'F.' in sql_upper:
                if f"USER_ID = '{user_id}'" not in sql_upper and f"USER_ID='{user_id}'" not in sql_upper:
                    if 'WHERE' in sql_upper:
                        sql = re.sub(r'WHERE', f"WHERE (f.user_id = '{user_id}' OR files.user_id = '{user_id}') AND", sql, count=1, flags=re.IGNORECASE)
                    else:
                        sql = _insert_where_clause(sql, f"(f.user_id = '{user_id}' OR files.user_id = '{user_id}')")
        
        return sql


def _insert_where_clause(sql: str, condition: str) -> str:
    """Helper to insert WHERE clause in appropriate position."""
    # Find FROM clause and insert WHERE after table references
    # This is a simplified version - might need refinement
    patterns = [
        (r'(FROM\s+\w+\s+\w+\s+)(ORDER BY)', r'\1WHERE ' + condition + r' \2'),
        (r'(FROM\s+\w+\s+\w+\s+)(GROUP BY)', r'\1WHERE ' + condition + r' \2'),
        (r'(FROM\s+\w+\s+\w+\s+)(LIMIT)', r'\1WHERE ' + condition + r' \2'),
        (r'(FROM\s+\w+\s+\w+)(\s*$)', r'\1 WHERE ' + condition + r'\2'),
    ]
    
    for pattern, replacement in patterns:
        if re.search(pattern, sql, re.IGNORECASE):
            return re.sub(pattern, replacement, sql, count=1, flags=re.IGNORECASE)
    
    return sql


# ============================================================================
# Text-to-SQL Engine
# ============================================================================

class TextToSQLEngine:
    """Main engine for converting natural language to SQL and executing queries."""
    
    def __init__(self, db: Session, llm_provider=None):
        self.db = db
        self.llm_provider = llm_provider
        self.validator = SQLSafetyValidator()
        self.access_control = AccessControlLayer()
    
    def generate_sql(self, question: str, user_context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate SQL from natural language question.
        
        Args:
            question: User's natural language question
            user_context: User's context (role, user_id, org_id)
            
        Returns:
            Dict with 'sql' or 'error' or 'clarification'
        """
        if not self.llm_provider:
            return {"error": "LLM provider not configured"}
        
        # Build prompt with schema and access control
        access_control_context = self.access_control.get_access_control_context(user_context)
        
        prompt = SQL_GENERATION_PROMPT.format(
            schema=DATABASE_SCHEMA,
            access_control=access_control_context,
            question=question
        )
        
        try:
            # Call LLM to generate SQL
            response = self.llm_provider.generate(prompt, max_tokens=500)
            sql = response.strip()
            
            # Handle special responses
            if sql.startswith('ERROR:'):
                return {"error": sql[6:].strip()}
            
            if sql.startswith('CLARIFY:'):
                return {"clarification": sql[8:].strip()}
            
            # Clean up the SQL
            sql = self._clean_sql(sql)
            
            return {"sql": sql}
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return {"error": f"Failed to generate query: {str(e)}"}
    
    def execute_query(
        self, 
        sql: str, 
        user_context: Dict[str, Any],
        timeout_seconds: int = 10,
        max_rows: int = 50
    ) -> Dict[str, Any]:
        """
        Safely execute a SQL query.
        
        Args:
            sql: The SQL query to execute
            user_context: User's context for access control
            timeout_seconds: Query timeout
            max_rows: Maximum rows to return
            
        Returns:
            Dict with 'results', 'columns', 'row_count' or 'error'
        """
        # Step 1: Validate safety
        is_safe, error = self.validator.validate(sql)
        if not is_safe:
            logger.warning(f"Unsafe SQL blocked: {sql} - Reason: {error}")
            return {"error": f"Query blocked for safety: {error}"}
        
        # Step 2: Enforce access control
        sql = self.access_control.enforce_access_control(sql, user_context)
        
        # Step 3: Add row limit
        sql = self.validator.add_row_limit(sql, max_rows)
        
        logger.info(f"Executing SQL: {sql}")
        
        try:
            # Execute with timeout
            result = self.db.execute(
                text(f"SET SESSION MAX_EXECUTION_TIME = {timeout_seconds * 1000}")
            )
            result = self.db.execute(text(sql))
            
            # Fetch results
            rows = result.fetchall()
            columns = list(result.keys()) if result.keys() else []
            
            # Convert to list of dicts
            data = []
            for row in rows:
                row_dict = {}
                for i, col in enumerate(columns):
                    value = row[i]
                    # Handle datetime serialization
                    if isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    row_dict[col] = value
                data.append(row_dict)
            
            return {
                "success": True,
                "columns": columns,
                "results": data,
                "row_count": len(data),
                "sql_executed": sql
            }
            
        except Exception as e:
            logger.error(f"Error executing SQL: {e}")
            return {"error": f"Query execution failed: {str(e)}"}
    
    def ask(
        self, 
        question: str, 
        user_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Full pipeline: Question -> SQL -> Execute -> Format Results
        
        Args:
            question: Natural language question
            user_context: User's context
            
        Returns:
            Dict with formatted results or error
        """
        # Generate SQL
        gen_result = self.generate_sql(question, user_context)
        
        if "error" in gen_result:
            return gen_result
        
        if "clarification" in gen_result:
            return {
                "needs_clarification": True,
                "message": gen_result["clarification"]
            }
        
        sql = gen_result["sql"]
        
        # Execute query
        exec_result = self.execute_query(sql, user_context)
        
        if "error" in exec_result:
            return exec_result
        
        # Format results for display
        return self._format_results(question, exec_result)
    
    def _clean_sql(self, sql: str) -> str:
        """Clean up LLM-generated SQL."""
        # Remove markdown code blocks if present
        sql = re.sub(r'```sql\s*', '', sql)
        sql = re.sub(r'```\s*', '', sql)
        
        # Remove leading/trailing whitespace
        sql = sql.strip()
        
        # Remove any explanation text after the query
        if ';' in sql:
            sql = sql.split(';')[0] + ';'
        
        return sql
    
    def _format_results(self, question: str, exec_result: Dict[str, Any]) -> Dict[str, Any]:
        """Format query results for chat display."""
        results = exec_result.get("results", [])
        columns = exec_result.get("columns", [])
        row_count = exec_result.get("row_count", 0)
        
        if row_count == 0:
            return {
                "success": True,
                "message": "No results found for your query.",
                "row_count": 0
            }
        
        # Format as markdown table for chat
        formatted = self._results_to_markdown(results, columns)
        
        return {
            "success": True,
            "message": f"Found {row_count} result{'s' if row_count != 1 else ''}:",
            "formatted_results": formatted,
            "raw_results": results,
            "columns": columns,
            "row_count": row_count,
            "sql_executed": exec_result.get("sql_executed", "")
        }
    
    def _results_to_markdown(self, results: List[Dict], columns: List[str]) -> str:
        """Convert results to markdown table."""
        if not results or not columns:
            return ""
        
        # Header
        lines = ["| " + " | ".join(str(col) for col in columns) + " |"]
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        
        # Rows
        for row in results[:20]:  # Limit display to 20 rows
            values = []
            for col in columns:
                val = row.get(col, "")
                # Format bytes as human-readable
                if 'size' in col.lower() and isinstance(val, (int, float)):
                    val = self._format_bytes(val)
                values.append(str(val) if val is not None else "")
            lines.append("| " + " | ".join(values) + " |")
        
        if len(results) > 20:
            lines.append(f"\n*... and {len(results) - 20} more rows*")
        
        return "\n".join(lines)
    
    def _format_bytes(self, bytes_val: int) -> str:
        """Format bytes to human-readable string."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if abs(bytes_val) < 1024.0:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"


# ============================================================================
# Simple LLM Wrapper for Ollama
# ============================================================================

class OllamaLLMProvider:
    """Simple wrapper for Ollama API for SQL generation."""
    
    def __init__(self, base_url: str = "http://host.docker.internal:11434", model: str = "gemma2:2b"):
        self.base_url = base_url
        self.model = model
    
    def generate(self, prompt: str, max_tokens: int = 500) -> str:
        """Generate text using Ollama."""
        import requests
        
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "temperature": 0.1,  # Low temperature for precise SQL
                }
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json().get("response", "")
        else:
            raise Exception(f"Ollama API error: {response.status_code}")


# ============================================================================
# Integration Function
# ============================================================================

def create_text_to_sql_engine(db: Session, ollama_base_url: str = None, model: str = None) -> TextToSQLEngine:
    """
    Factory function to create a Text-to-SQL engine.
    
    Args:
        db: SQLAlchemy database session
        ollama_base_url: Ollama API URL (default: host.docker.internal:11434)
        model: Model name (default: gemma2:2b)
        
    Returns:
        Configured TextToSQLEngine instance
    """
    from core.config import config
    
    base_url = ollama_base_url or getattr(config, 'OLLAMA_BASE_URL', 'http://host.docker.internal:11434')
    model_name = model or getattr(config, 'OLLAMA_MODEL', 'gemma2:2b')
    
    llm_provider = OllamaLLMProvider(base_url=base_url, model=model_name)
    
    return TextToSQLEngine(db=db, llm_provider=llm_provider)
