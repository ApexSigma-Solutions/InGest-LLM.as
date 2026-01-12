"""
Document Parser Module for CortexBridge InGest-LLMs Engine.

This module provides extractive NLP parsing capabilities using Spacy Transformers
and NLTK for sentence tokenization. It converts long-form text into structured
Knowledge Graphs (Nodes & Edges) with data provenance.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import spacy
from spacy.tokens import Doc
from spacy.language import Language

logger = logging.getLogger(__name__)


class DocumentParser:
    """
    Extractive NLP parser for converting text to Knowledge Graphs.

    Uses Spacy Transformers (en_core_web_trf) for high-fidelity
    Entity & Relationship extraction, and NLTK for sentence tokenization.

    Attributes:
        nlp: Spacy language model loaded at initialization
        model_name: Name of the loaded Spacy model
    """

    # Model priority list (in order of preference)
    MODEL_PRIORITY = [
        "en_core_web_trf",  # Transformer-based (best accuracy, largest)
        "en_core_web_md",  # Transformer-based (good accuracy, medium)
        "en_core_web_sm",  # CNN-based (fastest, smallest)
    ]

    def __init__(self, model_name: str | None = None) -> None:
        """
        Initialize DocumentParser with a Spacy Transformer model.

        Args:
            model_name: Name of Spacy model to load. If None, will try
                      models in priority order, falling back to lighter models.
                      Can also be set via SPACY_MODEL environment variable.

        Raises:
            ImportError: If Spacy is not installed or no model can be loaded
        """
        # Get model from environment variable or parameter
        if model_name is None:
            model_name = os.getenv("SPACY_MODEL", "")

        self.model_name = model_name
        self.nlp: Language | None = None

        # Try to load the specified model or fallback through priority list
        models_to_try = [model_name] if model_name else []
        models_to_try.extend([m for m in self.MODEL_PRIORITY if m not in models_to_try])

        for attempt_model in models_to_try:
            try:
                self.nlp = spacy.load(attempt_model)
                logger.info(f"Loaded Spacy model: {attempt_model}")
                return  # Success - exit early
            except OSError as e:
                logger.warning(f"Failed to load Spacy model '{attempt_model}': {e}")
                if attempt_model != models_to_try[-1]:
                    logger.info("Trying next model in priority list...")
                    continue
                else:
                    # Last attempt failed - provide helpful error
                    logger.error("All Spacy models failed to load.")
                    logger.error(
                        "Please install a model using one of:\n"
                        "  python -m spacy download en_core_web_trf  (best accuracy)\n"
                        "  python -m spacy download en_core_web_md   (good accuracy)\n"
                        "  python -m spacy download en_core_web_sm   (fastest)"
                    )
                    logger.error(
                        "Or set SPACY_MODEL environment variable to your preferred model."
                    )
                    raise ImportError(
                        f"No Spacy model could be loaded. Tried: {', '.join(models_to_try)}. "
                        "Install with: python -m spacy download <model_name>"
                    ) from e
            except Exception as e:
                logger.error(f"Unexpected error loading Spacy model: {e}")
                raise

    def preprocess(self, text: str) -> List[str]:
        """
        Preprocess text by cleaning and splitting into sentences.

        Uses NLTK's sent_tokenize for superior sentence splitting compared
        to Spacy's default sentence splitter.

        Args:
            text: Raw input text to preprocess

        Returns:
            List of cleaned sentences

        Raises:
            ImportError: If NLTK is not installed
        """
        try:
            import nltk
        except ImportError as e:
            logger.error(f"NLTK not installed: {e}")
            logger.error("Please install NLTK: pip install nltk")
            logger.error("Download NLTK data: python -m nltk.downloader punkt")
            raise ImportError(
                "NLTK not installed. Install with: pip install nltk"
            ) from e

        # Clean whitespace
        cleaned_text = " ".join(text.split())

        # Use NLTK for sentence tokenization (superior to Spacy's default)
        try:
            sentences: List[str] = nltk.sent_tokenize(cleaned_text)
        except LookupError as e:
            logger.error(f"NLTK punkt tokenizer not found: {e}")
            logger.error("Download NLTK data: python -m nltk.downloader punkt")
            raise ImportError(
                "NLTK punkt tokenizer not found. "
                "Download with: python -m nltk.downloader punkt"
            ) from e

        logger.debug(f"Preprocessed text into {len(sentences)} sentences")
        return sentences

    def _expand_compound_noun(self, token: Any) -> str:
        """
        Expand compound nouns to capture full entity phrases.

        For example, "ApexSigma Design System" should be captured as a single
        entity rather than just "ApexSigma" or "Design System".

        Args:
            token: Spacy token to expand

        Returns:
            Full compound noun phrase
        """
        # Collect all tokens that are part of the compound noun phrase
        compound_tokens = [token]
        to_process = list(token.children)

        while to_process:
            child = to_process.pop(0)
            if child.dep_ == "compound":
                compound_tokens.append(child)
                # Recursively check children of compound words
                to_process.extend(child.children)

        # Sort by position in text to maintain correct order
        compound_tokens.sort(key=lambda t: t.i)

        return " ".join([t.text for t in compound_tokens])

    def extract_relations(self, doc: Doc) -> Dict[str, Any]:
        """
        Extract entities and relationships from Spacy document using dependency parsing.

        Iterates through tokens to identify VERB tokens and their children
        (nsubj, dobj, pobj) to extract subject-verb-object triples.

        Args:
            doc: Spacy processed document

        Returns:
            Dictionary with 'nodes' and 'edges' keys representing the Knowledge Graph
        """
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        seen_entities: set[str] = set()

        for token in doc:
            # Focus on VERB tokens as relationship anchors
            if token.pos_ != "VERB":
                continue

            # Extract subject (nominal subject)
            subject = None
            for child in token.children:
                if child.dep_ in ("nsubj", "nsubjpass"):
                    subject_text = self._expand_compound_noun(child)
                    subject = {
                        "text": subject_text,
                        "pos": child.pos_,
                        "type": self._classify_entity_type(child),
                    }
                    break

            # Extract object (direct object)
            obj = None
            for child in token.children:
                if child.dep_ == "dobj":
                    obj_text = self._expand_compound_noun(child)
                    obj = {
                        "text": obj_text,
                        "pos": child.pos_,
                        "type": self._classify_entity_type(child),
                    }
                    break

            # Extract prepositional object (object of preposition)
            pobj = None
            for child in token.children:
                if child.dep_ == "pobj":
                    pobj_text = self._expand_compound_noun(child)
                    pobj = {
                        "text": pobj_text,
                        "pos": child.pos_,
                        "type": self._classify_entity_type(child),
                    }
                    break

            # Only create edge if we have at least subject and one object
            if subject and (obj or pobj):
                # Add subject node if not seen
                if subject["text"] not in seen_entities:
                    nodes.append(subject)
                    seen_entities.add(subject["text"])

                # Add object node if not seen
                if obj and obj["text"] not in seen_entities:
                    nodes.append(obj)
                    seen_entities.add(obj["text"])

                if pobj and pobj["text"] not in seen_entities:
                    nodes.append(pobj)
                    seen_entities.add(pobj["text"])

                # Create edge: subject --[verb]--> object
                edge = {
                    "source": subject["text"],
                    "target": (obj or pobj)["text"],
                    "relation": token.lemma_,
                    "source_pos": subject["pos"],
                    "target_pos": (obj or pobj)["pos"],
                }
                edges.append(edge)

        logger.debug(f"Extracted {len(nodes)} nodes and {len(edges)} edges")
        return {"nodes": nodes, "edges": edges}

    def _classify_entity_type(self, token: Any) -> str:
        """
        Classify entity type based on Spacy NER and POS tags.

        Args:
            token: Spacy token to classify

        Returns:
            Entity type string (PERSON, ORG, PRODUCT, GPE, etc.)
        """
        # Check for named entity recognition
        if token.ent_type_:
            return token.ent_type_

        # Fallback to POS-based classification
        pos_mapping = {
            "PROPN": "PERSON",  # Proper noun
            "ORG": "ORG",  # Organization
            "GPE": "GPE",  # Geopolitical entity
            "LOC": "GPE",  # Location
            "PRODUCT": "PRODUCT",  # Product
            "EVENT": "EVENT",  # Event
            "WORK_OF_ART": "WORK_OF_ART",  # Work of art
            "LAW": "LAW",  # Law
            "LANGUAGE": "LANGUAGE",  # Language
            "DATE": "DATE",  # Date
            "TIME": "TIME",  # Time
            "PERCENT": "PERCENT",  # Percent
            "MONEY": "MONEY",  # Money
            "QUANTITY": "QUANTITY",  # Quantity
            "ORDINAL": "ORDINAL",  # Ordinal
            "CARDINAL": "CARDINAL",  # Cardinal
        }

        return pos_mapping.get(token.pos_, "ENTITY")

    def parse(self, text: str) -> Dict[str, Any]:
        """
        Parse text into a Knowledge Graph structure.

        Orchestrates the full pipeline:
        1. Preprocess text (clean, sentence tokenize)
        2. Process each sentence with Spacy
        3. Extract entities and relationships
        4. Return structured graph

        Args:
            text: Raw input text to parse

        Returns:
            Dictionary with 'metadata', 'nodes', and 'edges' keys

        Raises:
            RuntimeError: If parser is not initialized
        """
        if self.nlp is None:
            raise RuntimeError("DocumentParser not initialized. Model not loaded.")

        logger.info(f"Parsing text ({len(text)} characters)")

        # Step 1: Preprocess text
        sentences = self.preprocess(text)

        # Step 2: Process each sentence with Spacy
        all_nodes: List[Dict[str, Any]] = []
        all_edges: List[Dict[str, Any]] = []
        seen_entities: set[str] = set()

        for sentence in sentences:
            doc = self.nlp(sentence)

            # Extract entities and relations from this sentence
            result = self.extract_relations(doc)

            # Merge nodes, avoiding duplicates
            for node in result["nodes"]:
                if node["text"] not in seen_entities:
                    all_nodes.append(node)
                    seen_entities.add(node["text"])

            # Merge edges
            all_edges.extend(result["edges"])

        # Remove duplicate edges
        unique_edges = []
        seen_edges = set()
        for edge in all_edges:
            edge_key = (edge["source"], edge["relation"], edge["target"])
            if edge_key not in seen_edges:
                unique_edges.append(edge)
                seen_edges.add(edge_key)

        logger.info(f"Parsed into {len(all_nodes)} nodes and {len(unique_edges)} edges")

        return {
            "metadata": {
                "model": self.model_name,
                "sentences_processed": len(sentences),
                "nodes_extracted": len(all_nodes),
                "edges_extracted": len(unique_edges),
            },
            "nodes": all_nodes,
            "edges": unique_edges,
        }
