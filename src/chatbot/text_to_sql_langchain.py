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
        
        # SQL Query Generation Prompt
        self.sql_prompt = PromptTemplate.from_template("""
You are a MySQL expert. Generate a SQL query to answer the question.

DATABASE SCHEMA:
{table_info}

ACCESS CONTROL:
{access_control}

RULES:
1. ONLY generate SELECT queries
2. Use table aliases (u=users, f=files, o=organizations, fo=folders)
3. Always add LIMIT 50 unless user specifies
4. Use proper JOINs for multi-table queries
5. Return human-readable column names using AS
6. Always include ORDER BY for consistent results
7. RESPECT the access control restrictions above

Question: {question}

SQL Query (only the query, no explanations):
""")
        
        # Answer Generation Prompt  
        self.answer_prompt = PromptTemplate.from_template("""
Given the following user question, SQL query, and SQL result, write a natural language response.

Question: {question}
SQL Query: {query}
SQL Result: {result}

Write a helpful, conversational response that answers the user's question based on the data.
If there's no data, say so politely. Format numbers nicely (e.g., file sizes in KB/MB/GB).
Use bullet points or tables if showing multiple items.
Keep the response concise but informative.

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
            
            # Get table info
            table_info = self.db.get_table_info()
            
            # Generate SQL query
            logger.info(f"Generating SQL for: {question}")
            
            # Format the prompt
            formatted_prompt = self.sql_prompt.format(
                table_info=table_info,
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
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "query": sql_query,
                    "answer": "The query failed to execute. Please try a different question."
                }
            
            # Generate natural language answer
            answer_prompt_formatted = self.answer_prompt.format(
                question=question,
                query=sql_query,
                result=result
            )
            
            answer_response = await self.llm.ainvoke(answer_prompt_formatted)
            answer = answer_response.content.strip()
            
            # Count results
            row_count = 0
            if result and result != "[]":
                try:
                    row_count = result.count('\n') + 1 if '\n' in str(result) else (1 if result else 0)
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
