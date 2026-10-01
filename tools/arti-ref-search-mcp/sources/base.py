"""Base class for all paper-search sources.

Adapted from openags/paper-search-mcp (MIT, Copyright 2025 OPENAGS), `academic_platforms/base.py`.
`download_pdf`/`read_paper` are dropped -- no source in this build implements them, and a future
source that can should add its own methods instead of every source carrying unused stubs.
"""
from abc import ABC, abstractmethod
from typing import Any

from paper import Paper


class PaperSource(ABC):
    """Abstract base class for a single literature-search source."""

    @abstractmethod
    def search(self, query: str, **kwargs) -> Any:
        """Search papers matching the query.

        Args:
            query: Search query string.
            **kwargs: Source-specific parameters (e.g., max_results, year_from).

        Returns:
            Source-defined result built from Paper objects (OpenAlex returns a
            {"meta", "results"} envelope so paging/cost info travels with the papers).
        """
