"""
Chatbot API Routes - REST and WebSocket endpoints for chatbot

Provides:
- POST /chat - Send message and get response
- GET /chat/health - Chatbot health status
- GET /chat/suggestions - Get initial suggestions
- WebSocket /chat/ws - Real-time chat connection
- DELETE /chat/session/{session_id} - End session
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import logging
import json

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from core.security import get_current_user, AuthenticatedUser
from infrastructure.db.mysql import mysql
from chatbot import get_chatbot, chatbot_config
from chatbot.providers.base import UserContext
from chatbot.security import RBACFilter, get_accessible_pages, get_allowed_actions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/chat", tags=["Chatbot"])


def get_db():
    """Get database session."""
    return next(mysql.get_db())


# ============================================================================
# DATABASE DEPENDENCY
# ============================================================================

def get_db():
    """Get database session."""
    return next(mysql.get_db())


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class ChatRequest(BaseModel):
    """Request to send a chat message."""
    message: str = Field(..., min_length=1, max_length=4000, description="User's message")
    session_id: Optional[str] = Field(None, description="Existing session ID")


class ChatActionResponse(BaseModel):
    """An action the chatbot wants to perform."""
    type: str  # navigate, execute, confirm, info, error
    payload: Dict[str, Any] = {}
    description: str = ""
    requires_confirmation: bool = False


class ChatMessageResponse(BaseModel):
    """Response from the chatbot."""
    message: str
    actions: List[ChatActionResponse] = []
    suggestions: List[str] = []
    provider: str
    processing_time_ms: int
    tokens_used: Optional[int] = None


class RoutingInfo(BaseModel):
    """Information about how the request was routed."""
    method: str = Field(description="Routing method used: analytics_template_sql, rule_based, text_to_sql_llm, llm_chat")
    elapsed_ms: int = Field(description="Total time to process request")


class ChatResponse(BaseModel):
    """Full chat response including session info."""
    session_id: str
    response: ChatMessageResponse
    message_count: int
    routing: Optional[RoutingInfo] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class SuggestionsResponse(BaseModel):
    """Initial suggestions for user."""
    suggestions: List[str]
    accessible_pages: List[Dict[str, str]]
    allowed_actions: List[Dict[str, str]]


class HealthResponse(BaseModel):
    """Chatbot health status."""
    enabled: bool
    provider: Dict[str, Any]
    sessions: Dict[str, Any]
    config: Dict[str, Any]
    cache: Optional[Dict[str, Any]] = None  # Redis cache status


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def build_user_context(user: AuthenticatedUser) -> UserContext:
    """Build UserContext from AuthenticatedUser."""
    return UserContext(
        user_id=user.user_id,
        email=user.email or "",
        role=user.role.value,
        organization_id=user.organization_id,
        organization_name=None,  # Could be fetched from DB if needed
        permissions=[p.value for p in user.permissions]
    )


def require_chatbot_enabled():
    """Dependency to check if chatbot is enabled."""
    if not chatbot_config.enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chatbot is currently disabled"
        )


# ============================================================================
# REST ENDPOINTS
# ============================================================================

@router.post("/", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db),
    _: None = Depends(require_chatbot_enabled)
):
    """
    Send a message to the chatbot and get a response.
    
    The chatbot respects RBAC - it will only suggest actions and 
    navigation the user has permission to access.
    
    PRODUCTION ROUTING (fast → slow):
    1. Analytics Template SQL (~50-100ms) - 80% of data queries
    2. Rule-based Navigation (~1ms) - greetings, navigation
    3. LangChain Text-to-SQL (~30s) - complex queries
    4. LLM Chat - general conversation
    """
    chatbot = get_chatbot()
    user_context = build_user_context(user)
    
    try:
        result = await chatbot.chat(
            message=request.message,
            user_context=user_context,
            session_id=request.session_id,
            db=db  # Pass database for fast analytics queries
        )
        
        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result["error"]
            )
        
        # Apply RBAC filter to actions
        rbac_filter = RBACFilter(user_context)
        response_data = result["response"]
        
        # Convert action dicts to ChatActionResponse
        actions = []
        for action_dict in response_data.get("actions", []):
            action = ChatActionResponse(**action_dict)
            actions.append(action)
        
        # Filter actions based on permissions (backend enforcement)
        from chatbot.providers.base import ChatAction, ActionType
        chat_actions = [
            ChatAction(
                type=ActionType(a.type),
                payload=a.payload,
                description=a.description,
                requires_confirmation=a.requires_confirmation
            )
            for a in actions
        ]
        filtered_actions = rbac_filter.filter_actions(chat_actions)
        
        # Build routing info if available
        routing_info = None
        if "routing" in result and result["routing"]:
            routing_info = RoutingInfo(
                method=result["routing"].get("method", "unknown"),
                elapsed_ms=result["routing"].get("elapsed_ms", 0)
            )
        
        return ChatResponse(
            session_id=result["session_id"],
            response=ChatMessageResponse(
                message=response_data["message"],
                actions=[
                    ChatActionResponse(
                        type=a.type.value,
                        payload=a.payload,
                        description=a.description,
                        requires_confirmation=a.requires_confirmation
                    )
                    for a in filtered_actions
                ],
                suggestions=response_data.get("suggestions", []),
                provider=response_data.get("provider", "unknown"),
                processing_time_ms=response_data.get("processing_time_ms", 0),
                tokens_used=response_data.get("tokens_used")
            ),
            message_count=result["message_count"],
            routing=routing_info
        )
        
    except Exception as e:
        logger.error(f"Chat error for user {user.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process chat message"
        )


@router.get("/suggestions", response_model=SuggestionsResponse)
async def get_suggestions(
    user: AuthenticatedUser = Depends(get_current_user),
    _: None = Depends(require_chatbot_enabled)
):
    """
    Get initial suggestions for the user based on their role.
    
    Returns quick-start suggestions, accessible pages, and allowed actions.
    """
    chatbot = get_chatbot()
    user_context = build_user_context(user)
    
    suggestions = await chatbot.get_suggestions(user_context)
    accessible_pages = get_accessible_pages(user_context)
    allowed_actions = get_allowed_actions(user_context)
    
    return SuggestionsResponse(
        suggestions=suggestions,
        accessible_pages=accessible_pages,
        allowed_actions=allowed_actions
    )


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Get chatbot health status.
    
    Shows provider health, session statistics, configuration, and Redis cache status.
    """
    chatbot = get_chatbot()
    health = await chatbot.health_check()
    
    # Add Redis cache status
    try:
        from infrastructure.redis_cache import redis_cache
        health['cache'] = redis_cache.health_check()
    except ImportError:
        health['cache'] = {"status": "not_installed", "backend": "none"}
    except Exception as e:
        health['cache'] = {"status": "error", "error": str(e)}
    
    return HealthResponse(**health)


# ============================================================================
# REDIS CACHE MANAGEMENT ENDPOINTS
# ============================================================================

@router.get("/cache/stats")
async def get_cache_stats(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get Redis cache statistics.
    
    Shows hits, misses, hit rate, and backend status.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view cache statistics"
        )
    
    try:
        from infrastructure.redis_cache import redis_cache
        return {
            "success": True,
            "data": redis_cache.health_check()
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis cache not installed",
            "data": {"status": "not_available"}
        }


@router.post("/cache/flush")
async def flush_cache(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Flush all chatbot-related caches.
    
    Use with caution - this will cause temporary performance degradation
    as caches need to be rebuilt.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can flush cache"
        )
    
    try:
        from infrastructure.redis_cache import redis_cache
        
        # Flush SQL query caches
        deleted = redis_cache.delete_pattern("*", prefix="sql")
        
        return {
            "success": True,
            "message": f"Cache flushed successfully. {deleted} keys deleted.",
            "deleted_keys": deleted
        }
    except ImportError:
        return {
            "success": False,
            "error": "Redis cache not installed"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Cache flush failed: {str(e)}"
        )


# ============================================================================
# INTELLIGENT TYPO CORRECTOR ENDPOINTS
# ============================================================================

class TypoCorrectionRequest(BaseModel):
    """Request to correct a query."""
    query: str = Field(..., min_length=1, max_length=500, description="Query to correct")
    use_ai: bool = Field(False, description="Use AI for ambiguous corrections")


class LearnCorrectionRequest(BaseModel):
    """Request to learn a new correction."""
    typo: str = Field(..., min_length=1, max_length=100, description="The typo")
    correction: str = Field(..., min_length=1, max_length=100, description="The correct word")


class AddVocabularyRequest(BaseModel):
    """Request to add words to vocabulary."""
    words: List[str] = Field(..., min_items=1, description="Words to add")


@router.get("/typo/stats")
async def get_typo_corrector_stats(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get intelligent typo corrector statistics.
    
    Shows vocabulary size, explicit corrections, learned corrections, and AI status.
    """
    try:
        from chatbot.intelligent_typo_corrector import get_intelligent_corrector
        
        corrector = get_intelligent_corrector()
        stats = corrector.get_stats()
        
        return {
            "success": True,
            "data": {
                **stats,
                "description": "Intelligent AI-powered typo corrector",
                "methods": {
                    "vocabulary": "Known domain words (fastest, 0ms)",
                    "explicit": "Known typo→correction mappings (~0ms)",
                    "learned": "AI-learned corrections from feedback (~0ms)",
                    "fuzzy": "Similarity matching for unknown words (~1ms)",
                    "ai": "LLM-powered contextual correction (~500ms)"
                }
            }
        }
    except Exception as e:
        logger.error(f"Failed to get typo corrector stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get typo corrector stats: {str(e)}"
        )


@router.post("/typo/correct")
async def correct_query(
    request: TypoCorrectionRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Correct a query for typos using intelligent correction.
    
    - Fast mode (default): Uses vocabulary + fuzzy matching (~1ms)
    - AI mode: Also uses LLM for ambiguous cases (~500ms)
    """
    try:
        from chatbot.intelligent_typo_corrector import get_intelligent_corrector
        
        corrector = get_intelligent_corrector()
        
        if request.use_ai:
            result = await corrector.correct_query_async(request.query)
        else:
            result = corrector.correct_query_sync(request.query)
        
        return {
            "success": True,
            "data": {
                "original": result.original,
                "corrected": result.corrected,
                "was_corrected": result.was_corrected,
                "method": result.method,
                "confidence": result.confidence,
                "corrections": result.corrections,
                "processing_time_ms": result.processing_time_ms
            }
        }
    except Exception as e:
        logger.error(f"Typo correction failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Typo correction failed: {str(e)}"
        )


@router.post("/typo/learn")
async def learn_typo_correction(
    request: LearnCorrectionRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Teach the corrector a new typo→correction mapping.
    
    Learned corrections are used in future queries.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can teach the typo corrector"
        )
    
    try:
        from chatbot.intelligent_typo_corrector import get_intelligent_corrector
        
        corrector = get_intelligent_corrector()
        corrector.learn_correction(request.typo, request.correction)
        
        return {
            "success": True,
            "message": f"Learned: '{request.typo}' → '{request.correction}'",
            "stats": corrector.get_stats()
        }
    except Exception as e:
        logger.error(f"Failed to learn correction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to learn correction: {str(e)}"
        )


@router.post("/typo/vocabulary")
async def add_to_vocabulary(
    request: AddVocabularyRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Add new words to the typo corrector vocabulary.
    
    Words in vocabulary won't be "corrected" to something else.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can modify vocabulary"
        )
    
    try:
        from chatbot.intelligent_typo_corrector import get_intelligent_corrector
        
        corrector = get_intelligent_corrector()
        corrector.add_to_vocabulary(request.words)
        
        return {
            "success": True,
            "message": f"Added {len(request.words)} words to vocabulary",
            "words_added": request.words,
            "stats": corrector.get_stats()
        }
    except Exception as e:
        logger.error(f"Failed to add vocabulary: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add vocabulary: {str(e)}"
        )


# ============================================================================
# SELF-HEALING AI ENDPOINTS
# ============================================================================

@router.get("/healing/stats")
async def get_healing_stats(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get self-healing AI system statistics.
    
    Shows errors detected, fixes applied, patterns learned, and pending reviews.
    """
    try:
        from chatbot.self_healing.advanced_healing import get_healer
        
        healer = get_healer()
        stats = healer.get_stats()
        
        return {
            "success": True,
            "data": {
                **stats,
                "description": "Advanced self-healing AI that learns from mistakes",
                "capabilities": [
                    "Auto-detect navigation vs data query mismatches",
                    "Generate and apply regex patterns automatically",
                    "Learn exclusion patterns to prevent routing errors",
                    "Queue complex fixes for human review"
                ]
            }
        }
    except Exception as e:
        logger.error(f"Failed to get healing stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get healing stats: {str(e)}"
        )


@router.get("/healing/pending")
async def get_pending_fixes(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get pending fixes that need human review.
    
    These are fixes that were detected but couldn't be auto-applied
    (low confidence or complex cases).
    """
    try:
        from chatbot.self_healing.advanced_healing import get_healer
        
        healer = get_healer()
        pending = healer.get_pending_fixes()
        
        return {
            "success": True,
            "count": len(pending),
            "fixes": pending
        }
    except Exception as e:
        logger.error(f"Failed to get pending fixes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get pending fixes: {str(e)}"
        )


@router.post("/healing/approve/{fix_index}")
async def approve_pending_fix(
    fix_index: int,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Approve and apply a pending fix.
    
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can approve fixes"
        )
    
    try:
        from chatbot.self_healing.advanced_healing import get_healer
        
        healer = get_healer()
        success = healer.approve_pending_fix(fix_index)
        
        if success:
            return {
                "success": True,
                "message": f"Fix #{fix_index} approved and applied",
                "stats": healer.get_stats()
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Fix #{fix_index} not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve fix: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to approve fix: {str(e)}"
        )


@router.get("/healing/patterns")
async def get_learned_patterns(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get all patterns learned by the self-healing system.
    
    Shows navigation patterns, exclusion patterns, and training examples.
    """
    try:
        from chatbot.self_healing.advanced_healing import get_healer
        
        healer = get_healer()
        patterns = healer.patterns_store.get_all()
        
        return {
            "success": True,
            "count": len(patterns),
            "patterns": [
                {
                    "id": p.id,
                    "type": p.pattern_type,
                    "pattern": p.pattern[:100],
                    "handler": p.target_handler,
                    "source_query": p.source_query,
                    "learned_at": p.learned_at,
                    "applied": p.applied,
                    "confidence": p.confidence
                }
                for p in patterns
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get learned patterns: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get learned patterns: {str(e)}"
        )


class TestHealingRequest(BaseModel):
    """Request to test the self-healing detection."""
    query: str = Field(..., min_length=1, max_length=500)
    response: str = Field(..., min_length=1, max_length=2000)
    routing_method: str = Field(default="llm_chat")


@router.post("/healing/test")
async def test_healing_detection(
    request: TestHealingRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Test the self-healing error detection without applying fixes.
    
    Useful for debugging and understanding how the system detects errors.
    """
    try:
        from chatbot.self_healing.advanced_healing import (
            AdvancedSelfHealingSystem,
            HealingConfig
        )
        
        # Create a test instance that doesn't auto-apply
        test_healer = AdvancedSelfHealingSystem(
            HealingConfig(auto_apply=False)
        )
        
        result = await test_healer.process_response(
            user_query=request.query,
            response=request.response,
            routing_method=request.routing_method,
            actions=[]
        )
        
        if result:
            return {
                "success": True,
                "error_detected": True,
                "error_type": result.error_report.error_type.value,
                "fix_type": result.fix_type.value,
                "pattern_generated": result.pattern_added,
                "message": result.message,
                "confidence": result.error_report.confidence
            }
        else:
            return {
                "success": True,
                "error_detected": False,
                "message": "No error detected - response appears correct"
            }
    except Exception as e:
        logger.error(f"Healing test failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Healing test failed: {str(e)}"
        )


# ============================================================================
# DSPy PROMPT OPTIMIZER ENDPOINTS
# ============================================================================

@router.get("/dspy/status")
async def get_dspy_status(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get DSPy prompt optimizer status.
    
    Shows whether DSPy is available, if it's optimized, and training data count.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view DSPy status"
        )
    
    try:
        from chatbot.hybrid_sql_agent import get_hybrid_sql_agent, HYBRID_SQL_AVAILABLE
        from chatbot.dspy_optimizer import DSPY_AVAILABLE, TRAINING_EXAMPLES
        
        if not DSPY_AVAILABLE:
            return {
                "available": False,
                "message": "DSPy not installed. Run: pip install dspy-ai"
            }
        
        if not HYBRID_SQL_AVAILABLE:
            return {
                "available": True,
                "hybrid_enabled": False,
                "message": "Hybrid SQL Agent not loaded"
            }
        
        agent = get_hybrid_sql_agent()
        status = agent.get_status()
        
        return {
            "available": True,
            "hybrid_enabled": True,
            "use_dspy": status["use_dspy"],
            "is_optimized": status["dspy_optimized"],
            "training_examples": len(TRAINING_EXAMPLES),
            "langchain_model": status["langchain_model"],
            "message": "DSPy optimizer ready" if status["dspy_optimized"] else "DSPy not yet optimized. Call POST /api/v1/chat/dspy/optimize to train."
        }
        
    except Exception as e:
        logger.error(f"DSPy status error: {e}", exc_info=True)
        return {
            "available": False,
            "error": str(e)
        }


@router.post("/dspy/optimize")
async def optimize_dspy(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Run DSPy optimization to improve SQL generation.
    
    This analyzes training examples and discovers optimal prompt patterns.
    May take 30-60 seconds. Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can optimize DSPy"
        )
    
    try:
        from chatbot.hybrid_sql_agent import get_hybrid_sql_agent, HYBRID_SQL_AVAILABLE
        
        if not HYBRID_SQL_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Hybrid SQL Agent not available"
            )
        
        agent = get_hybrid_sql_agent()
        result = agent.optimize_dspy()
        
        return {
            "success": result.get("success", False),
            "is_optimized": result.get("is_optimized", False),
            "validation_accuracy": result.get("validation_accuracy"),
            "training_examples": result.get("training_examples"),
            "validation_examples": result.get("validation_examples"),
            "error": result.get("error"),
            "message": "Optimization complete!" if result.get("success") else f"Optimization failed: {result.get('error')}"
        }
        
    except Exception as e:
        logger.error(f"DSPy optimization error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


class TrainingExampleRequest(BaseModel):
    """Request to add a training example."""
    question: str = Field(..., min_length=5, description="Natural language question")
    sql: str = Field(..., min_length=10, description="Correct SQL query")


@router.post("/dspy/training")
async def add_training_example(
    request: TrainingExampleRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Add a new training example for DSPy.
    
    Use this when a query produces wrong results and you want to teach
    the correct SQL. Re-run optimization after adding examples.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can add training examples"
        )
    
    try:
        from chatbot.hybrid_sql_agent import get_hybrid_sql_agent, HYBRID_SQL_AVAILABLE
        from chatbot.dspy_optimizer import TRAINING_EXAMPLES
        
        if not HYBRID_SQL_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Hybrid SQL Agent not available"
            )
        
        agent = get_hybrid_sql_agent()
        agent.add_training_example(request.question, request.sql)
        
        return {
            "success": True,
            "message": f"Training example added. Total examples: {len(TRAINING_EXAMPLES)}",
            "note": "Run POST /api/v1/chat/dspy/optimize to apply new examples"
        }
        
    except Exception as e:
        logger.error(f"Add training example error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/session/{session_id}")
async def end_session(
    session_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    End a chat session.
    
    Only the session owner can end their session.
    """
    chatbot = get_chatbot()
    
    success = chatbot.end_session(session_id, user.user_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return {"status": "success", "message": "Session ended"}


@router.get("/session/{session_id}/history")
async def get_session_history(
    session_id: str,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get chat history for a session.
    
    Only the session owner can view their history.
    """
    chatbot = get_chatbot()
    
    history = chatbot.get_session_history(session_id, user.user_id)
    if history is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or access denied"
        )
    
    return {"session_id": session_id, "history": history}


# ============================================================================
# SQL FEEDBACK & AUTO-LEARN ENDPOINTS (Enterprise)
# ============================================================================

class SQLFeedbackRequest(BaseModel):
    """Request to submit SQL correction feedback."""
    question: str = Field(..., description="Original natural language question")
    original_sql: Optional[str] = Field(None, description="SQL that chatbot generated")
    corrected_sql: str = Field(..., description="Correct SQL query")


class SQLFeedbackApprovalRequest(BaseModel):
    """Request to approve SQL feedback."""
    feedback_id: str
    question: str
    original_sql: Optional[str] = None
    corrected_sql: str


@router.post("/sql/feedback", tags=["SQL Feedback"])
async def submit_sql_feedback(
    request: SQLFeedbackRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Submit SQL correction feedback.
    
    When the chatbot generates incorrect SQL, admins can submit corrections.
    These corrections are stored for review and auto-learning.
    """
    import uuid
    from datetime import datetime
    
    feedback_id = str(uuid.uuid4())[:12]
    
    # Store feedback for review (in-memory for now, could use Redis/DB)
    try:
        from infrastructure.redis_cache import redis_cache
        feedback_data = {
            "id": feedback_id,
            "question": request.question,
            "original_sql": request.original_sql,
            "corrected_sql": request.corrected_sql,
            "submitted_by": user.user_id,
            "submitted_at": datetime.utcnow().isoformat(),
            "status": "pending"
        }
        redis_cache.set(f"sql_feedback:{feedback_id}", feedback_data, ttl=86400 * 7)  # 7 days
        
        return {
            "success": True,
            "feedback_id": feedback_id,
            "message": "Feedback submitted for review"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.post("/sql/feedback/approve", tags=["SQL Feedback"])
async def approve_sql_feedback(
    request: SQLFeedbackApprovalRequest,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Approve SQL feedback and trigger auto-learning.
    
    When an admin approves a correction:
    1. It's added to the RAG example store immediately
    2. It's queued for DSPy retraining
    3. Future queries benefit from this correction
    
    Requires super_admin role.
    """
    if user.role.value not in ["super_admin", "org_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve SQL feedback"
        )
    
    try:
        from chatbot.auto_learn_service import process_feedback_approval
        
        result = process_feedback_approval(
            feedback_id=request.feedback_id,
            question=request.question,
            original_sql=request.original_sql,
            corrected_sql=request.corrected_sql,
            approved_by=user.user_id
        )
        
        # Update feedback status in Redis
        try:
            from infrastructure.redis_cache import redis_cache
            redis_cache.delete(f"sql_feedback:{request.feedback_id}")
        except:
            pass
        
        return {
            "success": True,
            "feedback_id": request.feedback_id,
            "auto_learn_result": result,
            "message": "Feedback approved and added to training set"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process feedback: {str(e)}"
        )


@router.get("/sql/feedback/pending", tags=["SQL Feedback"])
async def get_pending_sql_feedback(
    user: AuthenticatedUser = Depends(get_current_user),
    limit: int = 50
):
    """
    Get pending SQL feedback awaiting approval.
    
    Requires admin role.
    """
    if user.role.value not in ["super_admin", "org_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view pending feedback"
        )
    
    try:
        from infrastructure.redis_cache import redis_cache
        # Get all pending feedback
        keys = redis_cache.get_keys("sql_feedback:*")
        pending = []
        for key in keys[:limit]:
            data = redis_cache.get(key.replace("fm:", ""))
            if data and data.get("status") == "pending":
                pending.append(data)
        
        return {
            "success": True,
            "count": len(pending),
            "pending": pending
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "pending": []
        }


@router.get("/auto-learn/stats", tags=["Auto-Learn"])
async def get_auto_learn_stats(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Get auto-learning statistics.
    
    Shows:
    - Pending feedback count
    - Training history
    - RAG store stats
    - Retrain readiness
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can view auto-learn stats"
        )
    
    try:
        from chatbot.auto_learn_service import get_auto_learn_service
        from chatbot.rag_example_store import get_rag_store
        
        auto_learn = get_auto_learn_service()
        rag_store = get_rag_store()
        
        return {
            "success": True,
            "auto_learn": auto_learn.get_stats(),
            "rag_store": rag_store.get_stats(),
            "training_history": auto_learn.get_training_history(limit=5)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/auto-learn/force-retrain", tags=["Auto-Learn"])
async def force_retrain(
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Force retrain the model with accumulated feedback.
    
    Use this to trigger immediate retraining regardless of thresholds.
    Requires super_admin role.
    """
    if user.role.value != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can force retrain"
        )
    
    try:
        from chatbot.auto_learn_service import get_auto_learn_service
        
        service = get_auto_learn_service()
        result = service.force_retrain()
        
        return {
            "success": result.get("success", False),
            "result": result,
            "message": "Retraining triggered" if result.get("success") else "Retraining failed"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Force retrain failed: {str(e)}"
        )


@router.get("/rag/search", tags=["RAG"])
async def search_rag_examples(
    query: str,
    top_k: int = 5,
    user: AuthenticatedUser = Depends(get_current_user)
):
    """
    Search RAG example store for similar queries.
    
    Useful for debugging and understanding what examples
    the system will use for a given query.
    """
    try:
        from chatbot.rag_example_store import get_rag_store
        
        store = get_rag_store()
        results = store.search_similar(query, top_k=top_k)
        
        return {
            "success": True,
            "query": query,
            "results": results,
            "count": len(results)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "results": []
        }


# ============================================================================
# WEBSOCKET ENDPOINT
# ============================================================================

class ConnectionManager:
    """Manages WebSocket connections for real-time chat."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"WebSocket connected: {user_id}")
    
    def disconnect(self, user_id: str):
        self.active_connections.pop(user_id, None)
        logger.info(f"WebSocket disconnected: {user_id}")
    
    async def send_message(self, user_id: str, message: dict):
        websocket = self.active_connections.get(user_id)
        if websocket:
            await websocket.send_json(message)


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    token: str = Query(...)
):
    """
    WebSocket endpoint for real-time chat.
    
    Connect with: ws://host/api/v1/chat/ws?token=<jwt_token>
    
    Messages:
    - Send: {"type": "message", "content": "Hello"}
    - Receive: {"type": "response", "data": {...}}
    """
    if not chatbot_config.enabled:
        await websocket.close(code=1008, reason="Chatbot disabled")
        return
    
    # Authenticate user from token
    from jose import JWTError, jwt
    from core.security import SECRET_KEY, ALGORITHM, Role
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=1008, reason="Invalid token")
            return
        
        user_context = UserContext(
            user_id=user_id,
            email=payload.get("email", ""),
            role=payload.get("role", "user"),
            organization_id=payload.get("org_id"),
            permissions=payload.get("permissions", [])
        )
        
    except JWTError as e:
        logger.error(f"WebSocket JWT error: {e}")
        await websocket.close(code=1008, reason="Invalid token")
        return
    except Exception as e:
        logger.error(f"WebSocket auth error: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    await manager.connect(websocket, user_id)
    chatbot = get_chatbot()
    session_id = None
    
    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to FileVault Assistant",
            "suggestions": await chatbot.get_suggestions(user_context)
        })
        
        while True:
            # Receive message
            data = await websocket.receive_json()
            msg_type = data.get("type", "message")
            
            if msg_type == "message":
                content = data.get("content", "")
                
                # Send typing indicator
                await websocket.send_json({"type": "typing"})
                
                # Process message
                result = await chatbot.chat(
                    message=content,
                    user_context=user_context,
                    session_id=session_id
                )
                
                if "error" in result:
                    await websocket.send_json({
                        "type": "error",
                        "message": result["error"]
                    })
                else:
                    session_id = result["session_id"]
                    
                    # Apply RBAC filter
                    rbac_filter = RBACFilter(user_context)
                    response_data = result["response"]
                    
                    from chatbot.providers.base import ChatAction, ActionType
                    chat_actions = [
                        ChatAction(
                            type=ActionType(a["type"]),
                            payload=a.get("payload", {}),
                            description=a.get("description", ""),
                            requires_confirmation=a.get("requires_confirmation", False)
                        )
                        for a in response_data.get("actions", [])
                    ]
                    filtered_actions = rbac_filter.filter_actions(chat_actions)
                    
                    await websocket.send_json({
                        "type": "response",
                        "session_id": session_id,
                        "data": {
                            "message": response_data["message"],
                            "actions": [
                                {
                                    "type": a.type.value,
                                    "payload": a.payload,
                                    "description": a.description,
                                    "requires_confirmation": a.requires_confirmation
                                }
                                for a in filtered_actions
                            ],
                            "suggestions": response_data.get("suggestions", []),
                            "provider": response_data.get("provider", "unknown"),
                            "processing_time_ms": response_data.get("processing_time_ms", 0)
                        }
                    })
            
            elif msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            
            elif msg_type == "end_session":
                if session_id:
                    chatbot.end_session(session_id, user_id)
                    session_id = None
                await websocket.send_json({
                    "type": "session_ended",
                    "message": "Chat session ended"
                })
    
    except WebSocketDisconnect:
        manager.disconnect(user_id)
        logger.info(f"WebSocket disconnected: {user_id}")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(user_id)
