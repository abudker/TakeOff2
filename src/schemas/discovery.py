"""Pydantic models for document structure mapping during discovery phase."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from enum import Enum


class PageType(str, Enum):
    """Types of pages found in Title 24 documents."""
    SCHEDULE = "schedule"
    CBECC = "cbecc"
    DRAWING = "drawing"
    OTHER = "other"


class PageInfo(BaseModel):
    """Information about a single page in the document."""
    page_number: int = Field(ge=1, description="1-indexed page number")
    page_type: PageType = Field(description="Classified page type")
    confidence: Literal["high", "medium", "low"] = Field(description="Classification confidence level")
    description: Optional[str] = Field(default=None, description="Brief description of page content")


class DocumentMap(BaseModel):
    """Map of document structure with classified pages."""
    total_pages: int = Field(ge=1, description="Total number of pages in document")
    pages: List[PageInfo] = Field(description="List of classified pages")

    @property
    def schedule_pages(self) -> List[int]:
        """Return list of page numbers classified as schedules."""
        return [p.page_number for p in self.pages if p.page_type == PageType.SCHEDULE]

    @property
    def cbecc_pages(self) -> List[int]:
        """Return list of page numbers classified as CBECC compliance forms."""
        return [p.page_number for p in self.pages if p.page_type == PageType.CBECC]

    @property
    def drawing_pages(self) -> List[int]:
        """Return list of page numbers classified as architectural drawings."""
        return [p.page_number for p in self.pages if p.page_type == PageType.DRAWING]
