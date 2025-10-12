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
        """
        Create a LangfuseClient and configure its underlying Langfuse client from environment variables.
        
        If API keys are not present or initialization fails, the client attribute will remain `None`.
        """
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """
        Configure and assign the Langfuse client on the instance using environment variables.
        
        Reads LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, and optional LANGFUSE_HOST; if both keys are present, instantiates a Langfuse client and assigns it to self.client, otherwise leaves self.client as None. On error during initialization, sets self.client to None and prints an error message.
        """
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
        """
        Indicates whether a Langfuse client has been successfully initialized.
        
        Returns:
            bool: `True` if the Langfuse client is initialized and available, `False` otherwise.
        """
        return self.client is not None

    @property
    def enabled(self) -> bool:
        """
        Indicates whether the Langfuse client is available.
        
        Returns:
            True if the underlying Langfuse client is initialized and usable, False otherwise.
        """
        return self.is_available()

    def create_trace(
        self,
        name: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        input_data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Start a new Langfuse trace and return its identifier.
        
        Parameters:
            name (str): Human-readable name for the trace.
            metadata (Optional[dict]): Arbitrary metadata to attach to the trace.
            tags (Optional[list]): Tags to associate with the trace (may be ignored by the client).
            input_data (Optional[dict]): Additional data that will be merged into `metadata` before creating the trace.
        
        Returns:
            Optional[str]: The trace id if the trace was created, `None` otherwise.
        """
        if not self.client:
            return None

        try:
            # Merge input_data into metadata if provided
            if input_data:
                metadata = metadata or {}
                metadata.update(input_data)

            trace = self.client.start_as_current_span(name=name, metadata=metadata)
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
        """
        Create a generation record in Langfuse for a model input and optional output.
        
        Parameters:
            name (str): Human-readable name for the generation.
            model (str): Identifier of the model that produced the generation.
            input_text (str): Text provided to the model.
            output_text (str, optional): Text produced by the model, if available.
            metadata (dict[str, Any], optional): Additional metadata to attach to the generation.
        
        Returns:
            str or None: The created generation's id if available, `None` on failure or if the client is unavailable.
        """
        if not self.client:
            return

        try:
            generation = self.client.start_as_current_generation(
                name=name,
                model=model,
                input=input_text,
                output=output_text,
                metadata=metadata,
            )
            return getattr(generation, "id", None)
        except Exception as e:
            print(f"Failed to create generation: {e}")
            return None

    def create_score(self, name: str, value: float, comment: Optional[str] = None):
        """
        Record a numeric score for the currently active trace.
        
        Parameters:
            name (str): Identifier for the score (for example, a metric name).
            value (float): Numeric score value.
            comment (Optional[str]): Optional human-readable note or context for the score.
        """
        if not self.client:
            return

        try:
            self.client.score_current_trace(name=name, value=value, comment=comment)
        except Exception as e:
            print(f"Failed to create score: {e}")

    def flush(self):
        """
        Flushes any queued Langfuse events to the backend.
        
        If the Langfuse client is not initialized this is a no-op. Exceptions raised while flushing are caught and printed.
        """
        if self.client:
            try:
                self.client.flush()
            except Exception as e:
                print(f"Failed to flush Langfuse events: {e}")


# Global client instance
_langfuse_client = None


def get_langfuse_client() -> LangfuseClient:
    """
    Get the module-level singleton LangfuseClient instance, creating it on first access.
    
    Returns:
        langfuse_client (LangfuseClient): The singleton LangfuseClient used for Langfuse observability.
    """
    global _langfuse_client
    if _langfuse_client is None:
        _langfuse_client = LangfuseClient()
    return _langfuse_client