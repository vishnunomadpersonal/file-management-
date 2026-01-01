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
    
    Shows provider health, session statistics, and configuration.
    """
    chatbot = get_chatbot()
    health = await chatbot.health_check()
    
    return HealthResponse(**health)


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
