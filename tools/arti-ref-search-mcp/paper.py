"""Shared, source-agnostic paper record.

Adapted from openags/paper-search-mcp (MIT, Copyright 2025 OPENAGS), `paper_search_mcp/paper.py`.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Paper:
    """Standardized paper format shared across all sources."""

    paper_id: str
    title: str
    authors: List[str]
    abstract: str
    doi: str
    published_date: Optional[datetime]
    pdf_url: str
    url: str
    source: str

    categories: List[str] = field(default_factory=list)
    citations: int = 0
    extra: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to a JSON-safe dict. Lists/dicts are kept as-is (no lossy flattening)."""
        return {
            "paper_id": self.paper_id,
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "doi": self.doi,
            "published_date": self.published_date.isoformat() if self.published_date else "",
            "pdf_url": self.pdf_url,
            "url": self.url,
            "source": self.source,
            "categories": self.categories,
            "citations": self.citations,
            "extra": self.extra,
        }
