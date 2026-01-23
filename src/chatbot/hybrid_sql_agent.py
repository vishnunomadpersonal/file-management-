"""
Hybrid SQL Agent - DSPy + LangChain
===================================
Combines DSPy's automatic prompt optimization with LangChain's SQL execution.

Strategy:
1. If OpenAI is available: Use LangChain directly (GPT-4o is excellent at SQL)
2. If Ollama only: DSPy generates optimized SQL queries (learned from examples)
3. LangChain handles database connection and query execution
4. Falls back to pure LangChain if DSPy unavailable

This gives you the best of both worlds:
- OpenAI: Superior intelligence, excellent SQL generation
- DSPy: Automatic prompt tuning for smaller models
- LangChain: Reliable DB connection, safety checks, result formatting
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Flag to indicate this module loaded successfully
HYBRID_SQL_AVAILABLE = True

# Import existing LangChain agent
from .text_to_sql_langchain import LangChainSQLAgent, AccessControlLayer

# Try to import DSPy optimizer
try:
    from .dspy_optimizer import (
        get_dspy_sql_generator,
        DSPyTextToSQL,
        DSPY_AVAILABLE
    )
except ImportError:
    DSPY_AVAILABLE = False
    logger.warning("DSPy optimizer not available")


class HybridSQLAgent:
    """
    Hybrid Text-to-SQL agent that uses:
    1. DSPy for optimized SQL generation (if available)
    2. LangChain for execution and fallback
    
    The key insight: DSPy learns optimal prompt patterns from examples,
    while LangChain provides robust DB infrastructure.
    """
    
    def __init__(
        self,
        db_url: str = None,
        ollama_base_url: str = None,
        model: str = "gemma2:2b",
        use_dspy: bool = True
    ):
        """
        Initialize hybrid agent.
        
        Args:
            db_url: Database connection URL
            ollama_base_url: Ollama server URL
            model: LLM model name
            use_dspy: Whether to use DSPy optimization (default True)
        """
        # Check if OpenAI is available - if so, skip DSPy (GPT-4o is better)
        openai_api_key = os.getenv("OPENAI_API_KEY")
        llm_provider = os.getenv("LLM_PROVIDER", "auto").lower()
        
        # Disable DSPy when using OpenAI (it's smarter without optimization)
        if llm_provider == "openai" or (llm_provider == "auto" and openai_api_key):
            logger.info("OpenAI available - using LangChain directly (skipping DSPy)")
            self.use_dspy = False
        else:
            self.use_dspy = use_dspy and DSPY_AVAILABLE
        
        self.ollama_base_url = ollama_base_url
        
        # Initialize LangChain agent (always needed for execution)
        self.langchain_agent = LangChainSQLAgent(
            db_url=db_url,
            ollama_base_url=ollama_base_url,
            model=model
        )
        
        # Initialize DSPy optimizer (optional)
        self.dspy_generator = None
        if self.use_dspy:
            try:
                self.dspy_generator = get_dspy_sql_generator(
                    model_name=f"ollama_chat/{model}",
                    ollama_base_url=ollama_base_url
                )
                logger.info("DSPy optimizer initialized successfully")
            except Exception as e:
                logger.warning(f"DSPy initialization failed: {e}, using LangChain only")
                self.use_dspy = False
        
        logger.info(f"HybridSQLAgent initialized (DSPy: {self.use_dspy})")
    
    async def ask(
        self,
        question: str,
        user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Answer a question using the best available method.
        
        Strategy:
        1. If DSPy available: Use DSPy to generate SQL, LangChain to execute
        2. If DSPy fails: Fall back to pure LangChain
        3. Always use LangChain for safety validation and execution
        
        Args:
            question: User's natural language question
            user_info: User context for access control
            
        Returns:
            Dict with answer, query, success status
        """
        dspy_sql = None
        used_dspy = False
        
        # Step 1: Try DSPy for SQL generation
        if self.use_dspy and self.dspy_generator:
            try:
                dspy_sql, meta = self.dspy_generator.generate_sql(question)
                if dspy_sql and meta.get("success"):
                    logger.info(f"DSPy generated SQL: {dspy_sql[:100]}...")
                    used_dspy = True
            except Exception as e:
                logger.warning(f"DSPy SQL generation failed: {e}")
                dspy_sql = None
        
        # Step 2: If DSPy produced SQL, execute with LangChain
        if dspy_sql:
            result = await self._execute_with_langchain(
                question=question,
                sql_query=dspy_sql,
                user_info=user_info
            )
            result["generation_method"] = "dspy"
            result["dspy_optimized"] = self.dspy_generator.is_optimized if self.dspy_generator else False
            return result
        
        # Step 3: Fall back to pure LangChain
        logger.info("Using LangChain for SQL generation and execution")
        result = await self.langchain_agent.ask(question, user_info)
        result["generation_method"] = "langchain"
        return result
    
    async def _execute_with_langchain(
        self,
        question: str,
        sql_query: str,
        user_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a SQL query using LangChain's safe execution.
        
        This reuses LangChain's:
        - Safety validation
        - Access control filtering
        - Result formatting
        """
        try:
            # Validate query
            is_valid, error = self.langchain_agent._validate_query(sql_query)
            if not is_valid:
                logger.warning(f"DSPy query failed validation: {error}")
                # Fall back to LangChain generation
                return await self.langchain_agent.ask(question, user_info)
            
            # Apply access control
            sql_query = AccessControlLayer.apply_filter_to_query(sql_query, user_info)
            
            # Ensure LIMIT
            if 'LIMIT' not in sql_query.upper():
                sql_query = f"{sql_query.rstrip(';')} LIMIT 50"
            
            logger.info(f"Executing DSPy SQL: {sql_query}")
            
            # Execute using LangChain's safe database
            try:
                result = self.langchain_agent.db.run(sql_query)
                logger.info(f"SQL Result: {str(result)[:300]}")
            except Exception as e:
                logger.error(f"Query execution failed: {e}")
                # Fall back to LangChain generation (might fix the SQL)
                return await self.langchain_agent.ask(question, user_info)
            
            # Handle empty result
            if not result or result == "[]" or result.strip() == "":
                return {
                    "success": True,
                    "answer": "No matching records found for your query.",
                    "query": sql_query,
                    "raw_result": result,
                    "row_count": 0,
                    "was_truncated": False
                }
            
            # Format result
            answer = self.langchain_agent._format_result_directly(question, result)
            row_count = str(result).count('(')
            
            return {
                "success": True,
                "answer": answer,
                "query": sql_query,
                "raw_result": result,
                "row_count": row_count,
                "was_truncated": row_count >= 50
            }
            
        except Exception as e:
            logger.error(f"Hybrid execution failed: {e}", exc_info=True)
            # Final fallback to pure LangChain
            return await self.langchain_agent.ask(question, user_info)
    
    def optimize_dspy(self) -> Dict[str, Any]:
        """
        Run DSPy optimization to improve SQL generation.
        
        This should be called:
        1. After initial setup
        2. After adding new training examples
        3. Periodically to maintain quality
        
        Returns:
            Optimization results dict
        """
        if not self.dspy_generator:
            return {
                "success": False,
                "error": "DSPy not available"
            }
        
        return self.dspy_generator.optimize()
    
    def add_training_example(self, question: str, sql: str):
        """
        Add a new training example for DSPy.
        
        Call this when:
        1. A user provides feedback that a query was wrong
        2. You want to teach new query patterns
        3. Building up training data
        """
        if self.dspy_generator:
            self.dspy_generator.add_training_example(question, sql)
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status for debugging."""
        return {
            "use_dspy": self.use_dspy,
            "dspy_available": DSPY_AVAILABLE,
            "dspy_optimized": self.dspy_generator.is_optimized if self.dspy_generator else False,
            "langchain_model": self.langchain_agent.model,
            "langchain_tables": self.langchain_agent.include_tables
        }


# Singleton instance
_hybrid_agent: Optional[HybridSQLAgent] = None


def get_hybrid_sql_agent(
    db_url: str = None,
    ollama_base_url: str = None,
    model: str = "gemma2:2b",
    use_dspy: bool = True
) -> HybridSQLAgent:
    """Get or create hybrid SQL agent singleton."""
    global _hybrid_agent
    
    if _hybrid_agent is None:
        _hybrid_agent = HybridSQLAgent(
            db_url=db_url,
            ollama_base_url=ollama_base_url,
            model=model,
            use_dspy=use_dspy
        )
    
    return _hybrid_agent
