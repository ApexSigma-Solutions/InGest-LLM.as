"""
Langfuse LLM observability client for InGest-LLM.as.

Provides LLM-specific observability including tracing, metrics, and
quality evaluation for agent interactions in the ApexSigma ecosystem.
"""

import os
from typing import Optional, Dict, Any, List

from langfuse import Langfuse


class LangfuseClient:
    """Langfuse client for LLM observability."""

    def __init__(self):
        """Initialize Langfuse client with environment configuration."""
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Langfuse client."""
        try:
            public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
            secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
            host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

            if public_key and secret_key:
                self.client = Langfuse(
                    public_key=public_key, secret_key=secret_key, host=host
                )
                print("Langfuse client initialized successfully")
            else:
                print("Langfuse API keys not found in environment")
        except Exception as e:
            print(f"Failed to initialize Langfuse client: {e}")
            self.client = None

    def is_available(self) -> bool:
        """Check if Langfuse client is available."""
        return self.client is not None

    @property
    def enabled(self) -> bool:
        """Check if Langfuse client is enabled (alias for is_available)."""
        return self.is_available()

    def create_trace(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Create a new trace."""
        if not self.client:
            return None

        try:
            # Merge input_data into metadata if provided
            if input_data:
                metadata = metadata or {}
                metadata.update(input_data)

            with self.client.start_as_current_span(name=name, metadata=metadata) as trace:
                # Set tags on the trace
                if tags:
                    trace.update_trace(tags=tags)
                return getattr(trace, "id", None)
        except Exception as e:
            print(f"Failed to create trace: {e}")
            return None

    def create_generation(
        self,
        name: str,
        model: str,
        input_text: str,
        output_text: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Create a generation record."""
        if not self.client:
            return

        try:
            with self.client.start_as_current_generation(
                name=name,
                model=model,
                input=input_text,
                output=output_text,
                metadata=metadata,
            ) as generation:
                return getattr(generation, "id", None)
        except Exception as e:
            print(f"Failed to create generation: {e}")
            return None

    def create_score(self, name: str, value: float, comment: Optional[str] = None):
        """Create a score for evaluation."""
        if not self.client:
            return

        try:
            self.client.score_current_trace(name=name, value=value, comment=comment)
        except Exception as e:
            print(f"Failed to create score: {e}")

    def flush(self):
        """Flush pending events."""
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                print(f"Failed to flush Langfuse events: {e}")


# Global client instance
_langfuse_client = None


def get_langfuse_client() -> LangfuseClient:
    """Get the global Langfuse client instance."""
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = LangfuseClient()
    return _langfuse_client
