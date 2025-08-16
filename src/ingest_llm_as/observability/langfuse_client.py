"""
Langfuse LLM observability client for InGest-LLM.as.

Provides LLM-specific observability including tracing, metrics, and
quality evaluation for agent interactions in the ApexSigma ecosystem.
"""

import os
from typing import Optional, Dict, Any
from contextlib import contextmanager

from langfuse import Langfuse
from langfuse.decorators import observe

from ..config import settings


class LangfuseClient:
    """Langfuse client for LLM observability."""
    
    def __init__(self):
        """Initialize Langfuse client with environment configuration."""
        self._client: Optional[Langfuse] = None
        self._enabled = self._check_langfuse_config()
    
    def _check_langfuse_config(self) -> bool:
        """Check if Langfuse is properly configured."""
        required_vars = ["LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY"]
        return all(os.getenv(var) for var in required_vars)
    
    @property
    def client(self) -> Optional[Langfuse]:
        """Get Langfuse client instance."""
        if not self._enabled:
            return None
            
        if self._client is None:
            self._client = Langfuse(
                public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
                secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
                host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
                environment=os.getenv("ENVIRONMENT", "development"),
                release=settings.app_version,
            )
        
        return self._client
    
    @property
    def enabled(self) -> bool:
        """Check if Langfuse is enabled and configured."""
        return self._enabled
    
    def create_trace(
        self,
        name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
    ) -> Optional[str]:
        """Create a new trace in Langfuse."""
        if not self.client:
            return None
        
        trace = self.client.trace(
            name=name,
            session_id=session_id,
            user_id=user_id,
            metadata=metadata or {},
            tags=tags or [],
            input=input_data,
            output=output_data,
        )
        
        return trace.id if trace else None
    
    def create_span(
        self,
        trace_id: str,
        name: str,
        span_type: str = "span",
        metadata: Optional[Dict[str, Any]] = None,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
    ) -> Optional[str]:
        """Create a span within an existing trace."""
        if not self.client:
            return None
        
        span = self.client.span(
            trace_id=trace_id,
            name=name,
            type=span_type,
            metadata=metadata or {},
            input=input_data,
            output=output_data,
            start_time=start_time,
            end_time=end_time,
        )
        
        return span.id if span else None
    
    def score_trace(
        self,
        trace_id: str,
        name: str,
        value: float,
        comment: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Add a score to a trace for quality evaluation."""
        if not self.client:
            return
        
        self.client.score(
            trace_id=trace_id,
            name=name,
            value=value,
            comment=comment,
            metadata=metadata or {},
        )
    
    def flush(self):
        """Flush any pending events to Langfuse."""
        if self.client:
            self.client.flush()
    
    @contextmanager
    def trace_context(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[list] = None,
        input_data: Optional[Any] = None,
    ):
        """Context manager for creating and managing a trace."""
        trace_id = None
        try:
            if self.enabled:
                trace_id = self.create_trace(
                    name=name,
                    metadata=metadata,
                    tags=tags,
                    input_data=input_data,
                )
            
            yield trace_id
            
        finally:
            if self.enabled and trace_id:
                self.flush()


# Global Langfuse client instance
langfuse_client = LangfuseClient()


def get_langfuse_client() -> LangfuseClient:
    """Get the global Langfuse client instance."""
    return langfuse_client


def trace_ingestion(
    content_type: str,
    content_size: int,
    chunk_count: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
):
    """Decorator for tracing ingestion operations."""
    def decorator(func):
        if not langfuse_client.enabled:
            return func
        
        @observe(name=f"ingestion_{content_type}")
        def wrapper(*args, **kwargs):
            # Execute the function with Langfuse observation
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_content_processing(operation_type: str):
    """Decorator for tracing content processing operations."""
    def decorator(func):
        if not langfuse_client.enabled:
            return func
        
        @observe(name=f"content_processing_{operation_type}")
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def trace_memos_interaction(endpoint: str, method: str):
    """Decorator for tracing memOS.as service interactions."""
    def decorator(func):
        if not langfuse_client.enabled:
            return func
        
        @observe(name=f"memos_interaction_{endpoint.replace('/', '_')}")
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        return wrapper
    return decorator