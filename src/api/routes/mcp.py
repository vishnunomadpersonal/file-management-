"""
MCP (Model Context Protocol) Server for Document Chat.

This module implements an MCP server that allows AI assistants to:
- Chat with uploaded documents
- Search document contents
- Get document summaries
- Answer questions about files

The server integrates with the file management system and uses
the incremental ML pipeline for intelligent document processing.
"""

import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from infrastructure.db.mysql import mysql
from entities.file import File
from core.security import get_current_user, AuthenticatedUser, Permission, require_permissions

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/mcp",
    tags=["mcp-server"]
)


# ============================================================================
# MCP PROTOCOL MODELS
# ============================================================================

class MCPTool(BaseModel):
    """MCP Tool definition."""
    name: str
    description: str
    inputSchema: Dict[str, Any]


class MCPResource(BaseModel):
    """MCP Resource definition."""
    uri: str
    name: str
    description: Optional[str] = None
    mimeType: Optional[str] = None


class MCPPrompt(BaseModel):
    """MCP Prompt definition."""
    name: str
    description: Optional[str] = None
    arguments: Optional[List[Dict[str, Any]]] = None


class MCPServerInfo(BaseModel):
    """MCP Server information."""
    name: str
    version: str
    protocolVersion: str = "2024-11-05"
    capabilities: Dict[str, Any]


class MCPToolCall(BaseModel):
    """Request to call an MCP tool."""
    name: str
    arguments: Dict[str, Any]


class MCPToolResult(BaseModel):
    """Result from an MCP tool call."""
    content: List[Dict[str, Any]]
    isError: bool = False


class ChatMessage(BaseModel):
    """Chat message for document conversation."""
    role: str  # user, assistant, system
    content: str


class ChatRequest(BaseModel):
    """Request to chat with documents."""
    messages: List[ChatMessage]
    file_ids: Optional[List[str]] = None  # Specific files to query
    context_limit: int = 4000  # Max context characters


class ChatResponse(BaseModel):
    """Response from document chat."""
    response: str
    sources: List[Dict[str, Any]]
    context_used: int


# ============================================================================
# DOCUMENT INDEX (Simple in-memory for demo, use vector DB in production)
# ============================================================================

@dataclass
class DocumentChunk:
    """A chunk of document content for retrieval."""
    file_id: str
    filename: str
    content: str
    chunk_index: int
    metadata: Dict[str, Any]
    embedding: Optional[List[float]] = None


class DocumentIndex:
    """
    Simple document index for retrieval.
    
    In production, replace with:
    - ChromaDB
    - Pinecone
    - Weaviate
    - pgvector
    """
    
    def __init__(self):
        self.documents: Dict[str, List[DocumentChunk]] = {}
        self.chunk_size = 1000
        self.overlap = 200
    
    def add_document(self, file_id: str, filename: str, content: str, metadata: Dict[str, Any] = None):
        """Index a document by chunking it."""
        chunks = []
        
        # Simple chunking by character count
        for i in range(0, len(content), self.chunk_size - self.overlap):
            chunk_content = content[i:i + self.chunk_size]
            if chunk_content.strip():
                chunks.append(DocumentChunk(
                    file_id=file_id,
                    filename=filename,
                    content=chunk_content,
                    chunk_index=len(chunks),
                    metadata=metadata or {}
                ))
        
        self.documents[file_id] = chunks
        logger.info(f"Indexed document {filename} with {len(chunks)} chunks")
    
    def remove_document(self, file_id: str):
        """Remove a document from the index."""
        if file_id in self.documents:
            del self.documents[file_id]
    
    def search(self, query: str, file_ids: Optional[List[str]] = None, top_k: int = 5) -> List[DocumentChunk]:
        """
        Search for relevant chunks.
        
        Simple keyword-based search. In production, use embedding similarity.
        """
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # Search through documents
        search_docs = file_ids if file_ids else list(self.documents.keys())
        
        for file_id in search_docs:
            if file_id not in self.documents:
                continue
            
            for chunk in self.documents[file_id]:
                # Simple relevance score based on keyword overlap
                chunk_lower = chunk.content.lower()
                score = sum(1 for word in query_words if word in chunk_lower)
                
                if score > 0:
                    results.append((score, chunk))
        
        # Sort by relevance and return top_k
        results.sort(key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in results[:top_k]]
    
    def get_document_summary(self, file_id: str) -> Optional[str]:
        """Get the first chunk as a summary."""
        if file_id in self.documents and self.documents[file_id]:
            return self.documents[file_id][0].content[:500]
        return None


# Global document index
document_index = DocumentIndex()


# ============================================================================
# MCP SERVER ENDPOINTS
# ============================================================================

def get_db():
    return next(mysql.get_db())


@router.get("/info", response_model=MCPServerInfo)
async def get_server_info():
    """Get MCP server information and capabilities."""
    return MCPServerInfo(
        name="document-intelligence-mcp",
        version="1.0.0",
        protocolVersion="2024-11-05",
        capabilities={
            "tools": True,
            "resources": True,
            "prompts": True,
            "logging": True
        }
    )


@router.get("/tools", response_model=List[MCPTool])
async def list_tools():
    """List available MCP tools."""
    return [
        MCPTool(
            name="search_documents",
            description="Search through uploaded documents for relevant information",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query"
                    },
                    "file_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific file IDs to search"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        ),
        MCPTool(
            name="get_document_info",
            description="Get information about a specific document",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The ID of the file"
                    }
                },
                "required": ["file_id"]
            }
        ),
        MCPTool(
            name="list_documents",
            description="List all uploaded documents for the current user",
            inputSchema={
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 20
                    }
                }
            }
        ),
        MCPTool(
            name="summarize_document",
            description="Get a summary of a document's content",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id": {
                        "type": "string",
                        "description": "The ID of the file to summarize"
                    }
                },
                "required": ["file_id"]
            }
        ),
        MCPTool(
            name="compare_documents",
            description="Compare two documents and highlight differences",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_id_1": {
                        "type": "string",
                        "description": "First file ID"
                    },
                    "file_id_2": {
                        "type": "string",
                        "description": "Second file ID"
                    }
                },
                "required": ["file_id_1", "file_id_2"]
            }
        )
    ]


@router.post("/tools/call", response_model=MCPToolResult)
async def call_tool(
    tool_call: MCPToolCall,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Execute an MCP tool."""
    try:
        if tool_call.name == "search_documents":
            return await _search_documents(tool_call.arguments, current_user, db)
        elif tool_call.name == "get_document_info":
            return await _get_document_info(tool_call.arguments, current_user, db)
        elif tool_call.name == "list_documents":
            return await _list_documents(tool_call.arguments, current_user, db)
        elif tool_call.name == "summarize_document":
            return await _summarize_document(tool_call.arguments, current_user, db)
        elif tool_call.name == "compare_documents":
            return await _compare_documents(tool_call.arguments, current_user, db)
        else:
            return MCPToolResult(
                content=[{"type": "text", "text": f"Unknown tool: {tool_call.name}"}],
                isError=True
            )
    except Exception as e:
        logger.error(f"Tool call error: {e}")
        return MCPToolResult(
            content=[{"type": "text", "text": f"Error: {str(e)}"}],
            isError=True
        )


async def _search_documents(args: Dict, user: AuthenticatedUser, db: Session) -> MCPToolResult:
    """Search documents for relevant content."""
    query = args.get("query", "")
    file_ids = args.get("file_ids")
    limit = args.get("limit", 5)
    
    # Get user's files if no specific files requested
    if not file_ids:
        files = db.query(File).filter(File.user_id == user.user_id).all()
        file_ids = [f.id for f in files]
    
    # Search the index
    results = document_index.search(query, file_ids, limit)
    
    if not results:
        return MCPToolResult(
            content=[{
                "type": "text",
                "text": f"No results found for query: '{query}'"
            }]
        )
    
    # Format results
    result_text = f"Found {len(results)} relevant sections for '{query}':\n\n"
    for i, chunk in enumerate(results, 1):
        result_text += f"**{i}. {chunk.filename}**\n"
        result_text += f"{chunk.content[:300]}...\n\n"
    
    return MCPToolResult(
        content=[{"type": "text", "text": result_text}]
    )


async def _get_document_info(args: Dict, user: AuthenticatedUser, db: Session) -> MCPToolResult:
    """Get information about a specific document."""
    file_id = args.get("file_id")
    
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == user.user_id
    ).first()
    
    if not file:
        return MCPToolResult(
            content=[{"type": "text", "text": f"File not found: {file_id}"}],
            isError=True
        )
    
    info = {
        "id": file.id,
        "filename": file.filename,
        "content_type": file.content_type,
        "size": file.size,
        "virus_scan_status": file.virus_scan_status,
        "is_quarantined": file.is_quarantined
    }
    
    return MCPToolResult(
        content=[{
            "type": "text",
            "text": f"**Document: {file.filename}**\n\n" + 
                   f"- Type: {file.content_type}\n" +
                   f"- Size: {file.size} bytes\n" +
                   f"- Virus Scan: {file.virus_scan_status}\n" +
                   f"- Quarantined: {file.is_quarantined}"
        }]
    )


async def _list_documents(args: Dict, user: AuthenticatedUser, db: Session) -> MCPToolResult:
    """List user's documents."""
    limit = args.get("limit", 20)
    
    files = db.query(File).filter(
        File.user_id == user.user_id
    ).limit(limit).all()
    
    if not files:
        return MCPToolResult(
            content=[{"type": "text", "text": "No documents found."}]
        )
    
    result_text = f"Found {len(files)} documents:\n\n"
    for f in files:
        result_text += f"- **{f.filename}** ({f.content_type}, {f.size} bytes)\n"
        result_text += f"  ID: `{f.id}`\n"
    
    return MCPToolResult(
        content=[{"type": "text", "text": result_text}]
    )


async def _summarize_document(args: Dict, user: AuthenticatedUser, db: Session) -> MCPToolResult:
    """Summarize a document."""
    file_id = args.get("file_id")
    
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == user.user_id
    ).first()
    
    if not file:
        return MCPToolResult(
            content=[{"type": "text", "text": f"File not found: {file_id}"}],
            isError=True
        )
    
    summary = document_index.get_document_summary(file_id)
    
    if not summary:
        return MCPToolResult(
            content=[{
                "type": "text",
                "text": f"No content indexed for {file.filename}. The document may not have been processed yet."
            }]
        )
    
    return MCPToolResult(
        content=[{
            "type": "text",
            "text": f"**Summary of {file.filename}:**\n\n{summary}"
        }]
    )


async def _compare_documents(args: Dict, user: AuthenticatedUser, db: Session) -> MCPToolResult:
    """Compare two documents."""
    file_id_1 = args.get("file_id_1")
    file_id_2 = args.get("file_id_2")
    
    file1 = db.query(File).filter(File.id == file_id_1, File.user_id == user.user_id).first()
    file2 = db.query(File).filter(File.id == file_id_2, File.user_id == user.user_id).first()
    
    if not file1 or not file2:
        return MCPToolResult(
            content=[{"type": "text", "text": "One or both files not found."}],
            isError=True
        )
    
    # Simple comparison based on metadata
    comparison = f"**Comparing Documents:**\n\n"
    comparison += f"| Property | {file1.filename} | {file2.filename} |\n"
    comparison += f"|----------|------------------|------------------|\n"
    comparison += f"| Size | {file1.size} bytes | {file2.size} bytes |\n"
    comparison += f"| Type | {file1.content_type} | {file2.content_type} |\n"
    
    return MCPToolResult(
        content=[{"type": "text", "text": comparison}]
    )


# ============================================================================
# CHAT ENDPOINT
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Chat with your documents using natural language.
    
    This endpoint:
    1. Takes your question/message
    2. Searches through your documents for relevant context
    3. Returns an answer based on the document contents
    """
    if not request.messages:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one message is required"
        )
    
    # Get the last user message as the query
    user_message = None
    for msg in reversed(request.messages):
        if msg.role == "user":
            user_message = msg.content
            break
    
    if not user_message:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No user message found"
        )
    
    # Get user's files if no specific files requested
    file_ids = request.file_ids
    if not file_ids:
        files = db.query(File).filter(File.user_id == current_user.user_id).all()
        file_ids = [f.id for f in files]
    
    # Search for relevant context
    relevant_chunks = document_index.search(user_message, file_ids, top_k=5)
    
    # Build context from chunks
    context = ""
    sources = []
    for chunk in relevant_chunks:
        if len(context) + len(chunk.content) < request.context_limit:
            context += f"\n\n[From {chunk.filename}]:\n{chunk.content}"
            sources.append({
                "file_id": chunk.file_id,
                "filename": chunk.filename,
                "chunk_index": chunk.chunk_index
            })
    
    # Generate response (in production, send to LLM)
    # For now, return the relevant context
    if context:
        response = f"Based on your documents, here's what I found relevant to your question:\n{context}"
    else:
        response = "I couldn't find any relevant information in your documents. Try rephrasing your question or uploading more documents."
    
    return ChatResponse(
        response=response,
        sources=sources,
        context_used=len(context)
    )


# ============================================================================
# DOCUMENT INDEXING ENDPOINTS
# ============================================================================

@router.post("/index/{file_id}")
async def index_document(
    file_id: str,
    content: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Index a document for search and chat.
    
    This is called automatically when a document is uploaded.
    """
    file = db.query(File).filter(
        File.id == file_id,
        File.user_id == current_user.user_id
    ).first()
    
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    # Index the document
    document_index.add_document(
        file_id=file_id,
        filename=file.filename,
        content=content,
        metadata={
            "content_type": file.content_type,
            "size": file.size,
            "user_id": current_user.user_id
        }
    )
    
    return {"message": f"Document {file.filename} indexed successfully"}


@router.delete("/index/{file_id}")
async def remove_document_from_index(
    file_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Remove a document from the search index."""
    document_index.remove_document(file_id)
    return {"message": "Document removed from index"}


@router.get("/index/stats")
async def get_index_stats(
    current_user: AuthenticatedUser = Depends(get_current_user)
):
    """Get statistics about the document index."""
    total_docs = len(document_index.documents)
    total_chunks = sum(len(chunks) for chunks in document_index.documents.values())
    
    return {
        "total_documents": total_docs,
        "total_chunks": total_chunks,
        "chunk_size": document_index.chunk_size,
        "overlap": document_index.overlap
    }
