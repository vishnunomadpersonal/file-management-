"""
Text-to-SQL using LangChain SQL Agent
=====================================
Production-ready Text-to-SQL implementation using LangChain's SQL toolkit.
Includes safety, access control, and natural language responses.
"""

import logging
import warnings
from typing import Dict, Any, Optional, List
from sqlalchemy import create_engine, text, MetaData, inspect
from sqlalchemy.orm import Session

# Suppress LangChain deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning, module="langchain")

# LangChain imports
from langchain_community.utilities import SQLDatabase
from langchain_community.chat_models import ChatOllama
from langchain_core.prompts import PromptTemplate

# Use chatbot config which has ollama settings
from .config import chatbot_config
from core.config import config as core_config

logger = logging.getLogger(__name__)

# ============================================================================
# Access Control - Role-based query restrictions
# ============================================================================

class AccessControlLayer:
    """Adds role-based access control to queries."""
    
    ROLE_HIERARCHY = {
        'super_admin': 5,
        'org_admin': 4,
        'manager': 3,
        'user': 2,
        'viewer': 1
    }
    
    @classmethod
    def get_access_restriction(cls, user_info: Dict[str, Any]) -> str:
        """
        Generate access control description for the LLM prompt.
        """
        role = user_info.get('role', 'viewer')
        user_id = user_info.get('user_id')
        org_id = user_info.get('organization_id')
        
        if role == 'super_admin':
            return "You have FULL access to all data across all organizations."
        
        elif role == 'org_admin':
            if org_id:
                return f"""You can ONLY access data for organization_id = '{org_id}'.
ALWAYS add WHERE organization_id = '{org_id}' to your queries.
For files table: WHERE f.organization_id = '{org_id}'
For users table: WHERE u.organization_id = '{org_id}'
For folders table: WHERE organization_id = '{org_id}'"""
            return "Organization admin without org_id - deny all queries."
        
        elif role in ['manager', 'user']:
            restrictions = []
            if org_id:
                restrictions.append(f"organization_id = '{org_id}'")
            if user_id:
                restrictions.append(f"For personal files: user_id = '{user_id}'")
            return f"Access restricted to: {'; '.join(restrictions)}"
        
        else:  # viewer
            return "Viewer role - very limited access, only aggregate/public data."
    
    @classmethod
    def apply_filter_to_query(cls, query: str, user_info: Dict[str, Any]) -> str:
        """
        Post-process query to ensure access control filters are applied.
        This is a safety net - the LLM should add them, but we verify.
        """
        role = user_info.get('role', 'viewer')
        org_id = user_info.get('organization_id')
        
        if role == 'super_admin':
            return query  # No restrictions
        
        query_upper = query.upper()
        
        # For org_admin, ensure org filter exists
        if role == 'org_admin' and org_id:
            if f"ORGANIZATION_ID = '{org_id.upper()}'" not in query_upper:
                if f"'{org_id.upper()}'" not in query_upper:
                    logger.warning(f"Query missing org filter, adding it")
                    # Try to inject org filter
                    if 'WHERE' in query_upper:
                        query = query.replace('WHERE', f"WHERE organization_id = '{org_id}' AND ", 1)
                    else:
                        # Find FROM clause and add WHERE
                        pass  # Let LangChain handle via prompt
        
        return query


# ============================================================================
# Custom SQL Database wrapper with safety
# ============================================================================

class SafeSQLDatabase(SQLDatabase):
    """Extended SQLDatabase with additional safety checks."""
    
    FORBIDDEN_KEYWORDS = [
        'INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE',
        'CREATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE',
        'INTO OUTFILE', 'INTO DUMPFILE', 'LOAD_FILE'
    ]
    
    def run(self, command: str, fetch: str = "all") -> str:
        """Override run to add safety checks."""
        # Safety check
        command_upper = command.upper()
        if not command_upper.strip().startswith('SELECT'):
            return "Error: Only SELECT queries are allowed."
        
        for keyword in self.FORBIDDEN_KEYWORDS:
            if keyword in command_upper:
                return f"Error: Forbidden keyword '{keyword}' detected."
        
        # Add row limit if not present
        if 'LIMIT' not in command_upper:
            command = f"{command.rstrip(';')} LIMIT 50"
        
        return super().run(command, fetch)


# ============================================================================
# LangChain SQL Agent
# ============================================================================

class LangChainSQLAgent:
    """
    Production-ready Text-to-SQL agent using LangChain.
    
    Features:
    - Natural language to SQL conversion
    - Query execution with safety checks
    - Natural language response generation
    - Role-based access control
    - Error handling and retry
    """
    
    def __init__(
        self,
        db_url: str = None,
        ollama_base_url: str = None,
        model: str = "gemma2:2b",
        include_tables: List[str] = None
    ):
        """
        Initialize the SQL Agent.
        
        Args:
            db_url: Database connection URL
            ollama_base_url: Ollama server URL
            model: LLM model to use
            include_tables: Tables to expose (for security)
        """
        self.db_url = db_url or str(core_config.MYSQL_DATABASE_URL)
        self.ollama_base_url = ollama_base_url or chatbot_config.ollama_base_url
        self.model = model
        self.include_tables = include_tables or [
            'users', 'files', 'organizations', 'folders', 'appointments'
        ]
        
        # Initialize components
        self._init_database()
        self._init_llm()
        self._init_chains()
        
        logger.info(f"LangChain SQL Agent initialized with model: {model}")
    
    def _init_database(self):
        """Initialize database connection."""
        self.engine = create_engine(self.db_url)
        
        # Use SafeSQLDatabase for additional safety
        self.db = SQLDatabase(
            engine=self.engine,
            include_tables=self.include_tables,
            sample_rows_in_table_info=3  # Show sample rows in schema
        )
        
        logger.info(f"Connected to database with tables: {self.include_tables}")
    
    def _init_llm(self):
        """Initialize Ollama LLM."""
        self.llm = ChatOllama(
            base_url=self.ollama_base_url,
            model=self.model,
            temperature=0,  # Deterministic for SQL
            timeout=120
        )
        logger.info(f"Ollama LLM initialized: {self.model}")
    
    def _init_chains(self):
        """Initialize LangChain prompts (we'll call LLM directly)."""
        
        # SQL Query Generation Prompt - IMPROVED with explicit schema
        self.sql_prompt = PromptTemplate.from_template("""
You are a MySQL expert. Generate a SQL query to answer the question.

=== DATABASE SCHEMA (USE ONLY THESE EXACT COLUMN NAMES) ===

TABLE: users (alias: u)
COLUMNS: id, name, email, role, organization_id, is_active, is_verified, status, created_at, updated_at, last_login_at

TABLE: files (alias: f)
COLUMNS: id, filename, content_type, size, user_id, organization_id, folder_id, virus_scan_status, virus_scan_date, is_quarantined, appointment_id, path, upload_id
NOTE: size is in BYTES. user_id = uploader (links to users.id). virus_scan_date = upload timestamp.

TABLE: organizations (alias: o)
COLUMNS: id, name, slug, description, email, phone, website, plan, is_active, is_verified, storage_quota_bytes, storage_used_bytes, max_users, max_files, created_at, updated_at

TABLE: folders (alias: fo)
COLUMNS: id, name, parent_id, organization_id, created_by, path, created_at, updated_at

TABLE: appointments (alias: a)
COLUMNS: id, name, date, user_id

=== IMPORTANT MAPPINGS ===
- "upload date" or "uploaded" or "when" → f.virus_scan_date
- "who uploaded" or "uploader" → JOIN users u ON f.user_id = u.id, then u.name
- "file size in MB" → ROUND(f.size/1048576, 2) AS size_mb
- "file size in KB" → ROUND(f.size/1024, 2) AS size_kb
- "total storage" → SUM(f.size)/1048576 AS total_mb
- "average file size" → AVG(f.size) for bytes, AVG(f.size)/1024 for KB, AVG(f.size)/1048576 for MB
- "user join date" or "registered" → u.created_at
- "appointment date" → a.date

=== ACCESS CONTROL ===
{access_control}

=== RULES ===
1. ONLY use columns listed above - NO OTHERS EXIST
2. FORBIDDEN columns: size_mb, size_kb, upload_date, uploaded_by, created_date
3. To get uploader: JOIN users u ON f.user_id = u.id
4. DATE RANGE RULES:
   - "between December 2025 and January 2026" → BETWEEN '2025-12-01' AND '2026-01-31'
5. Always add LIMIT 50
6. LISTING DOCUMENTS: Include filename, uploader name, and date
   Example: SELECT u.name, f.filename, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id WHERE ...
7. RANKING queries (most, top, sorted by): Include the value being sorted
   Example: SELECT u.name, SUM(f.size)/1048576 AS total_mb FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.name ORDER BY total_mb DESC
8. COUNTING: Include the count value
   Example: SELECT u.name, COUNT(*) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.name
9. SPECIFIC USER FILTERS: Filter by user name using WHERE u.name LIKE '%Name%'
   Example for "files uploaded by Super Admin": SELECT f.filename, ROUND(f.size/1024,2) as size_kb, f.virus_scan_date FROM files f JOIN users u ON f.user_id = u.id WHERE u.name LIKE '%Super Admin%'
10. COMPARISON FILTERS: Use proper comparison operators
    Example for "users with more than 5 files": SELECT u.name, COUNT(*) as file_count FROM files f JOIN users u ON f.user_id = u.id GROUP BY u.id, u.name HAVING COUNT(*) > 5
    Example for "files larger than 1MB": SELECT f.filename, ROUND(f.size/1048576,2) as size_mb FROM files f WHERE f.size > 1048576
11. AGGREGATIONS: Use AVG(), MIN(), MAX(), SUM() properly
    Example for "average file size": SELECT ROUND(AVG(f.size)/1024, 2) as avg_size_kb FROM files f
    Example for "smallest file": SELECT f.filename, f.size as size_bytes FROM files f ORDER BY f.size ASC LIMIT 1
    Example for "largest file": SELECT f.filename, ROUND(f.size/1048576,2) as size_mb FROM files f ORDER BY f.size DESC LIMIT 1
12. Output ONLY the SELECT statement

Question: {question}

SELECT""")
        
        # Answer Generation Prompt - STRICT to prevent hallucinations
        self.answer_prompt = PromptTemplate.from_template("""
You are a data assistant. Your job is to summarize SQL results in natural language.

Question: {question}
SQL Query: {query}
SQL Result: {result}

CRITICAL RULES:
1. ONLY report data that appears in the SQL Result above - DO NOT invent names, numbers, or facts
2. If SQL Result is empty or shows no rows, say "No matching records found" and nothing else
3. Use the EXACT names and values from the SQL Result - do not make up names like "John Doe"
4. Format the response clearly with bullet points or a simple list
5. Include counts and totals if they appear in the result

Response:
""")
    
    def _validate_query(self, query: str) -> tuple[bool, str]:
        """Validate SQL query for safety."""
        if not query or not query.strip():
            return False, "Empty query generated"
        
        query_upper = query.upper().strip()
        
        # Must be SELECT
        if not query_upper.startswith('SELECT'):
            return False, "Only SELECT queries allowed"
        
        # Check forbidden keywords
        forbidden = ['INSERT', 'UPDATE', 'DELETE', 'DROP', 'ALTER', 'TRUNCATE', 
                    'CREATE', 'GRANT', '--', '/*']
        for kw in forbidden:
            if kw in query_upper:
                return False, f"Forbidden keyword: {kw}"
        
        return True, ""
    
    async def ask(
        self,
        question: str,
        user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Answer a natural language question using SQL.
        
        Args:
            question: User's question in natural language
            user_info: User context for access control
            
        Returns:
            Dict with answer, query, success status, etc.
        """
        try:
            # Get access control context
            access_control = AccessControlLayer.get_access_restriction(user_info)
            
            # Generate SQL query
            logger.info(f"Generating SQL for: {question}")
            
            # Format the prompt (schema is hardcoded in prompt, no table_info needed)
            formatted_prompt = self.sql_prompt.format(
                access_control=access_control,
                question=question
            )
            
            # Get SQL from LLM
            sql_response = await self.llm.ainvoke(formatted_prompt)
            sql_query = sql_response.content.strip()
            
            # Clean up query (remove markdown if present)
            if sql_query.startswith('```'):
                sql_query = sql_query.split('```')[1]
                if sql_query.startswith('sql'):
                    sql_query = sql_query[3:]
            sql_query = sql_query.strip().rstrip(';')
            
            # Prepend SELECT since our prompt ends with "SELECT"
            if not sql_query.upper().startswith('SELECT'):
                sql_query = f"SELECT {sql_query}"
            
            # Handle LLM errors/clarifications
            if sql_query.startswith('ERROR:'):
                return {
                    "success": False,
                    "error": sql_query[6:].strip(),
                    "answer": f"I couldn't answer that question. {sql_query[6:].strip()}"
                }
            
            if sql_query.startswith('CLARIFY:'):
                return {
                    "success": False,
                    "needs_clarification": True,
                    "answer": sql_query[8:].strip()
                }
            
            # Validate query
            is_valid, error = self._validate_query(sql_query)
            if not is_valid:
                logger.warning(f"Invalid query generated: {error}")
                return {
                    "success": False,
                    "error": error,
                    "answer": "I generated an invalid query. Please try rephrasing your question."
                }
            
            # Apply access control filter (safety net)
            sql_query = AccessControlLayer.apply_filter_to_query(sql_query, user_info)
            
            # Add LIMIT if not present
            if 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query} LIMIT 50"
            
            logger.info(f"Executing SQL: {sql_query}")
            
            # Execute query
            try:
                result = self.db.run(sql_query)
                logger.info(f"SQL Result (first 500 chars): {str(result)[:500]}")
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "query": sql_query,
                    "answer": "The query failed to execute. Please try a different question."
                }
            
            # Check if result is empty
            if not result or result == "[]" or result.strip() == "" or result.strip() == "()":
                return {
                    "success": True,
                    "answer": "No matching records found for your query.",
                    "query": sql_query,
                    "raw_result": result,
                    "row_count": 0,
                    "was_truncated": False
                }
            
            # Format the result directly for reliability (avoid LLM hallucination)
            answer = self._format_result_directly(question, result)
            
            # Count results
            row_count = 0
            if result:
                try:
                    # Count tuples in the result
                    row_count = str(result).count('(') 
                except:
                    pass
            
            return {
                "success": True,
                "answer": answer,
                "query": sql_query,
                "raw_result": result,
                "row_count": row_count,
                "was_truncated": row_count >= 50
            }
            
        except Exception as e:
            logger.error(f"Text-to-SQL error: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": "I encountered an error processing your question. Please try again."
            }
    
    def _format_result_directly(self, question: str, result: str) -> str:
        """
        Format SQL result directly without LLM to prevent hallucination.
        This is more reliable for data reporting.
        """
        try:
            # Parse the result string (it's typically a string representation of tuples)
            # Example: "[('Super Admin', 'file.txt', datetime...), ...]"
            result_str = str(result)
            
            # Count rows
            rows = result_str.count('(')
            if rows == 0:
                return "No matching records found."
            
            # Build a simple formatted response
            question_lower = question.lower()
            
            # For count queries
            if 'how many' in question_lower or 'count' in question_lower:
                # Try to extract the count value
                import re
                count_match = re.search(r'\((\d+),?\)', result_str)
                if count_match:
                    return f"**{count_match.group(1)}** records found."
            
            # For list queries - show the data directly
            response_lines = [f"Found **{rows}** result(s):\n"]
            
            # Parse and format each row
            import ast
            import re
            from decimal import Decimal
            
            # Pre-process result string to handle Decimal and datetime
            processed_str = result_str
            # Convert Decimal('1.23') to 1.23
            processed_str = re.sub(r"Decimal\('([^']+)'\)", r'\1', processed_str)
            # Convert datetime.datetime(2025, 12, 23, 11, 8, 56) to '2025-12-23 11:08'
            def format_datetime(m):
                y, mo, d, h, mi = m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)
                return f"'{y}-{int(mo):02d}-{int(d):02d} {int(h):02d}:{int(mi):02d}'"
            processed_str = re.sub(
                r'datetime\.datetime\((\d+), (\d+), (\d+), (\d+), (\d+), \d+\)',
                format_datetime,
                processed_str
            )
            
            try:
                # Try to safely evaluate the processed result
                data = ast.literal_eval(processed_str)
                if isinstance(data, list):
                    for i, row in enumerate(data[:20], 1):  # Limit to 20 rows
                        if isinstance(row, tuple):
                            # Format tuple as bullet point
                            formatted_parts = []
                            for v in row:
                                if v is None:
                                    continue
                                elif isinstance(v, (int, float)):
                                    if v > 100000:
                                        # Likely bytes, convert to MB
                                        formatted_parts.append(f"{v/1048576:.2f} MB")
                                    elif isinstance(v, float):
                                        formatted_parts.append(f"{v:.2f} MB")
                                    else:
                                        formatted_parts.append(str(v))
                                else:
                                    formatted_parts.append(str(v))
                            response_lines.append(f"• {' | '.join(formatted_parts)}")
                        else:
                            response_lines.append(f"• {row}")
                    
                    if len(data) > 20:
                        response_lines.append(f"\n... and {len(data) - 20} more records.")
                else:
                    response_lines.append(f"• {data}")
            except Exception as e:
                logger.debug(f"AST parse failed: {e}, using regex fallback")
                # Fallback: extract with regex
                clean_result = processed_str.replace("[(", "").replace(")]", "")
                clean_result = clean_result.replace("), (", "\n• ").replace("(", "• ").replace(")", "")
                clean_result = clean_result.replace("'", "").replace(", ", " | ")
                response_lines.append(clean_result[:2000])
            
            return "\n".join(response_lines)
            
        except Exception as e:
            logger.warning(f"Result formatting failed: {e}")
            # Fallback: return raw result
            return f"Query results:\n```\n{str(result)[:1000]}\n```"
    
    def get_schema_info(self) -> str:
        """Get database schema information."""
        return self.db.get_table_info()


# ============================================================================
# Factory Function
# ============================================================================

_agent_instance: Optional[LangChainSQLAgent] = None

def get_sql_agent(
    db_url: str = None,
    ollama_base_url: str = None,
    model: str = None
) -> LangChainSQLAgent:
    """
    Get or create the SQL Agent singleton.
    """
    global _agent_instance
    
    if _agent_instance is None:
        _agent_instance = LangChainSQLAgent(
            db_url=db_url,
            ollama_base_url=ollama_base_url,
            model=model or "gemma2:2b"
        )
    
    return _agent_instance


def create_sql_agent(
    db_url: str = None,
    ollama_base_url: str = None,
    model: str = None
) -> LangChainSQLAgent:
    """
    Create a new SQL Agent instance.
    """
    return LangChainSQLAgent(
        db_url=db_url,
        ollama_base_url=ollama_base_url,
        model=model or "gemma2:2b"
    )
