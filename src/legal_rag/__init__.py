"""Offline retrieval-augmented generation for Vietnamese legal QA."""

from .config import RAGConfig
from .pipeline import LegalRAGPipeline

__all__ = ["LegalRAGPipeline", "RAGConfig"]
