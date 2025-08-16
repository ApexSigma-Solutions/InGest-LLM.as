"""
LM Studio embedding service for InGest-LLM.as.

This module encapsulates all interaction with the LM Studio SDK for generating
embeddings using local models (nomic-embed-text, nomic-embed-code).
"""

from typing import List, Optional, Dict, Any
from enum import Enum

import numpy as np
from openai import OpenAI
import httpx

from ..config import settings
from ..observability.logging import get_logger

logger = get_logger(__name__)


class EmbeddingModelType(str, Enum):
    """Available embedding models in LM Studio."""
    
    TEXT = "nomic-embed-text-v1.5"
    CODE = "nomic-embed-code-v1"
    GENERAL = "text-embedding-3-small"  # Fallback model


class VectorizerError(Exception):
    """Base exception for vectorizer errors."""
    pass


class VectorizerConnectionError(VectorizerError):
    """Raised when connection to LM Studio fails."""
    pass


class VectorizerAPIError(VectorizerError):
    """Raised when LM Studio returns an API error."""
    pass


class LMStudioVectorizer:
    """
    LM Studio vectorizer client for generating embeddings.
    
    Provides seamless integration with LM Studio's OpenAI-compatible API
    to generate embeddings using specialized local models.
    """
    
    def __init__(self):
        """Initialize the LM Studio vectorizer client."""
        self.base_url = settings.lm_studio_base_url
        self.timeout = settings.lm_studio_timeout
        self.api_key = settings.lm_studio_api_key or "not-needed"  # LM Studio doesn't require real API key
        
        # Initialize OpenAI client pointed to LM Studio
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
        )
        
        # Model availability cache
        self._available_models: Optional[List[str]] = None
        self._model_loaded: Optional[str] = None
    
    async def health_check(self) -> bool:
        """
        Check if LM Studio server is healthy and reachable.
        
        Returns:
            bool: True if LM Studio is healthy, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"LM Studio health check failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """
        Get list of available embedding models from LM Studio.
        
        Returns:
            List[str]: Available model names
            
        Raises:
            VectorizerConnectionError: If unable to connect to LM Studio
            VectorizerAPIError: If LM Studio returns an error
        """
        try:
            if self._available_models is None:
                models_response = self.client.models.list()
                self._available_models = [model.id for model in models_response.data]
                logger.info(f"Available LM Studio models: {self._available_models}")
            
            return self._available_models
        
        except Exception as e:
            logger.error(f"Failed to get available models from LM Studio: {e}")
            raise VectorizerConnectionError(f"Unable to connect to LM Studio: {e}")
    
    def select_model_for_content(self, content_type: str, detected_type: str = None) -> str:
        """
        Select the most appropriate embedding model based on content type.
        
        Implements TASK-IG-15: Logic to switch between specialized embedding models
        based on the type of content being processed.
        
        Args:
            content_type: The declared content type (text, code, etc.)
            detected_type: Auto-detected content type from processing
            
        Returns:
            str: Selected model name
        """
        available_models = self.get_available_models()
        
        # Priority selection based on content analysis
        if content_type.lower() in ["code", "python", "javascript", "json"] or \
           (detected_type and detected_type.lower() == "code"):
            
            # Prefer code-specialized model
            if EmbeddingModelType.CODE.value in available_models:
                logger.debug(f"Selected {EmbeddingModelType.CODE.value} for code content")
                return EmbeddingModelType.CODE.value
        
        # For text, documentation, markdown
        if EmbeddingModelType.TEXT.value in available_models:
            logger.debug(f"Selected {EmbeddingModelType.TEXT.value} for text content")
            return EmbeddingModelType.TEXT.value
        
        # Fallback to first available model
        if available_models:
            fallback_model = available_models[0]
            logger.warning(f"Using fallback model {fallback_model} for content type {content_type}")
            return fallback_model
        
        # Final fallback
        logger.warning("No specialized models available, using general model")
        return EmbeddingModelType.GENERAL.value
    
    def generate_embedding(
        self,
        text: str,
        model: Optional[str] = None,
        content_type: str = "text",
        detected_type: str = None
    ) -> List[float]:
        """
        Generate embedding for the given text using LM Studio.
        
        Args:
            text: Text content to embed
            model: Specific model to use (auto-selected if None)
            content_type: Content type hint for model selection
            detected_type: Auto-detected content type
            
        Returns:
            List[float]: Embedding vector
            
        Raises:
            VectorizerConnectionError: If unable to connect to LM Studio
            VectorizerAPIError: If embedding generation fails
        """
        try:
            # Auto-select model if not specified
            if model is None:
                model = self.select_model_for_content(content_type, detected_type)
            
            logger.debug(f"Generating embedding with model {model} for {len(text)} chars")
            
            # Generate embedding using OpenAI-compatible API
            response = self.client.embeddings.create(
                input=[text],
                model=model
            )
            
            embedding = response.data[0].embedding
            
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            
            return embedding
        
        except Exception as e:
            error_msg = f"Failed to generate embedding with LM Studio: {e}"
            logger.error(error_msg)
            
            if "connection" in str(e).lower():
                raise VectorizerConnectionError(error_msg)
            else:
                raise VectorizerAPIError(error_msg)
    
    def generate_embeddings_batch(
        self,
        texts: List[str],
        model: Optional[str] = None,
        content_type: str = "text",
        detected_type: str = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in a single batch.
        
        Args:
            texts: List of text content to embed
            model: Specific model to use (auto-selected if None)
            content_type: Content type hint for model selection
            detected_type: Auto-detected content type
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            VectorizerConnectionError: If unable to connect to LM Studio
            VectorizerAPIError: If embedding generation fails
        """
        try:
            # Auto-select model if not specified
            if model is None:
                model = self.select_model_for_content(content_type, detected_type)
            
            logger.debug(f"Generating {len(texts)} embeddings with model {model}")
            
            # Generate embeddings using batch API
            response = self.client.embeddings.create(
                input=texts,
                model=model
            )
            
            embeddings = [item.embedding for item in response.data]
            
            logger.debug(f"Generated {len(embeddings)} embeddings")
            
            return embeddings
        
        except Exception as e:
            error_msg = f"Failed to generate batch embeddings with LM Studio: {e}"
            logger.error(error_msg)
            
            if "connection" in str(e).lower():
                raise VectorizerConnectionError(error_msg)
            else:
                raise VectorizerAPIError(error_msg)
    
    def calculate_similarity(
        self,
        embedding1: List[float],
        embedding2: List[float]
    ) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector
            
        Returns:
            float: Cosine similarity score (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norms = np.linalg.norm(vec1) * np.linalg.norm(vec2)
            
            if norms == 0:
                return 0.0
            
            similarity = dot_product / norms
            
            # Ensure result is in [0, 1] range
            return max(0.0, min(1.0, (similarity + 1) / 2))
        
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def get_embedding_info(self, model: Optional[str] = None) -> Dict[str, Any]:
        """
        Get information about the embedding model.
        
        Args:
            model: Model name to get info for
            
        Returns:
            Dict[str, Any]: Model information
        """
        if model is None:
            model = self.select_model_for_content("text")
        
        return {
            "model": model,
            "provider": "lm-studio",
            "local": True,
            "available_models": self.get_available_models(),
            "base_url": self.base_url,
        }


# Global vectorizer instance
_vectorizer: Optional[LMStudioVectorizer] = None


def get_vectorizer() -> LMStudioVectorizer:
    """
    Get the global LM Studio vectorizer instance.
    
    Returns:
        LMStudioVectorizer: Configured vectorizer instance
    """
    global _vectorizer
    if _vectorizer is None:
        _vectorizer = LMStudioVectorizer()
    return _vectorizer


async def generate_content_embedding(
    content: str,
    content_type: str = "text",
    detected_type: str = None
) -> Optional[List[float]]:
    """
    Convenience function to generate embedding for content.
    
    Args:
        content: Text content to embed
        content_type: Content type hint
        detected_type: Auto-detected content type
        
    Returns:
        Optional[List[float]]: Embedding vector or None if generation fails
    """
    try:
        vectorizer = get_vectorizer()
        
        # Check if LM Studio is available
        if not await vectorizer.health_check():
            logger.warning("LM Studio not available, skipping embedding generation")
            return None
        
        return vectorizer.generate_embedding(
            text=content,
            content_type=content_type,
            detected_type=detected_type
        )
    
    except Exception as e:
        logger.error(f"Failed to generate content embedding: {e}")
        return None