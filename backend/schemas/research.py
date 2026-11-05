from typing import List, Optional
from pydantic import BaseModel, Field


class Author(BaseModel):
    name: str
    affiliation: Optional[str] = None


class ScientificPaper(BaseModel):
    doi: Optional[str] = None
    title: str
    authors: List[str] = Field(default_factory=list)
    publication_year: Optional[int] = None
    journal: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[str] = None
    is_peer_reviewed: bool = True
    source_database: str = "Crossref"
    citation_count: Optional[int] = None


class ResearchSearchResult(BaseModel):
    query: str
    total_found: int
    papers: List[ScientificPaper] = Field(default_factory=list)
    search_timestamp: str
    provider: str
    message: Optional[str] = None

