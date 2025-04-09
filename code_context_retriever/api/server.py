import os
import json
import time
import logging
from typing import Dict, Any, Optional, List

from fastapi import FastAPI, HTTPException, Depends, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import uvicorn

from ..config import Config
from ..retrieval.retriever import CodeContextRetriever
from ..utils.logging import get_logger

logger = get_logger(__name__)

app = FastAPI(title="Code Context Retriever API", 
              description="API for retrieving code context from indexed codebases")

# Global retriever instance
retriever: Optional[CodeContextRetriever] = None
config: Dict[str, Any] = {}

# Request/response models
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = None
    raw: bool = False

class QueryResponse(BaseModel):
    context: List[str]
    query_time: float
    
class RawQueryResponse(BaseModel):
    results: List[Dict[str, Any]]
    query_time: float

class IndexStatusResponse(BaseModel):
    status: str
    index_name: str
    chunks_count: int

# Security and rate limiting
async def verify_api_key(api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """Verify API key if authentication is enabled."""
    if config.get('api', {}).get('enable_authentication', False):
        expected_key = config.get('api', {}).get('api_key', '')
        if not expected_key or api_key != expected_key:
            raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# Rate limiting middleware
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Implement rate limiting based on client IP."""
    rate_limit = config.get('api', {}).get('rate_limit', 60)  # Requests per minute
    client_ip = request.client.host
    
    # Simple in-memory rate limiting
    # In production, use Redis or another distributed cache
    rate_limit_key = f"rate_limit:{client_ip}"
    
    # Check if rate limit exceeded
    # This is a simplistic implementation - production would use a proper rate limiter
    if hasattr(app.state, 'rate_limits') and rate_limit_key in app.state.rate_limits:
        timestamp, count = app.state.rate_limits[rate_limit_key]
        if time.time() - timestamp < 60 and count >= rate_limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again later."}
            )
    
    response = await call_next(request)
    
    # Update rate limit counter
    if not hasattr(app.state, 'rate_limits'):
        app.state.rate_limits = {}
    
    if rate_limit_key in app.state.rate_limits:
        timestamp, count = app.state.rate_limits[rate_limit_key]
        if time.time() - timestamp < 60:
            app.state.rate_limits[rate_limit_key] = (timestamp, count + 1)
        else:
            app.state.rate_limits[rate_limit_key] = (time.time(), 1)
    else:
        app.state.rate_limits[rate_limit_key] = (time.time(), 1)
    
    return response

@app.on_event("startup")
def startup_event():
    """Initialize the retriever on startup."""
    global retriever, config
    
    try:
        # Initialize retriever
        retriever = CodeContextRetriever()
        config = retriever.config
        
        # Set up CORS
        cors_origins = config.get('api', {}).get('cors_origins', ["*"])
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        logger.info("API server initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing API server: {e}", exc_info=True)

@app.get("/", tags=["Status"])
async def root():
    """Get API status."""
    return {"status": "ok", "service": "Code Context Retriever API"}

@app.get("/api/status", tags=["Status"])
async def status(api_key_valid: bool = Depends(verify_api_key)):
    """Get API and index status."""
    global retriever
    
    if not retriever:
        raise HTTPException(status_code=500, detail="Retriever not initialized")
    
    index_name = config.get('index_name', 'default')
    chunks_count = len(retriever.vector_index.metadata) if retriever.vector_index.metadata else 0
    
    return IndexStatusResponse(
        status="ok" if retriever.retriever else "no_index",
        index_name=index_name,
        chunks_count=chunks_count
    )

@app.post("/api/query", response_model=QueryResponse, tags=["Query"])
async def query(request: QueryRequest, api_key_valid: bool = Depends(verify_api_key)):
    """Query the indexed codebase."""
    global retriever
    
    if not retriever:
        raise HTTPException(status_code=500, detail="Retriever not initialized")
    
    if not retriever.retriever:
        raise HTTPException(status_code=404, detail="No index loaded. Index a codebase first.")
    
    try:
        start_time = time.time()
        
        if request.raw:
            # Return raw results
            results = retriever.raw_query(request.query, request.top_k)
            return RawQueryResponse(
                results=results,
                query_time=time.time() - start_time
            )
        else:
            # Return formatted context
            context = retriever.query(request.query)
            return QueryResponse(
                context=context,
                query_time=time.time() - start_time
            )
    except Exception as e:
        logger.error(f"Error processing query: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

def start_server(host: str = "0.0.0.0", port: int = 8000, config_path: Optional[str] = None):
    """Start the API server."""
    # Initialize global retriever with config
    global retriever, config
    retriever = CodeContextRetriever(config_path)
    config = retriever.config
    
    # Start server
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    start_server()