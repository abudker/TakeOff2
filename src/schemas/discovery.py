"""Pydantic models for document structure mapping during discovery phase."""
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict
from enum import Enum


# Cache version for migration - increment when schema changes require cache invalidation
CACHE_VERSION = 2


class PageType(str, Enum):
    """Types of pages found in Title 24 documents."""
    SCHEDULE = "schedule"
    CBECC = "cbecc"
    DRAWING = "drawing"
    OTHER = "other"


# Valid subtypes for richer classification
DRAWING_SUBTYPES = [
    "site_plan",        # Property layout, north arrow
    "floor_plan",       # Room layout, dimensions
    "elevation",        # Exterior views (N/S/E/W)
    "section",          # Cross-sections
    "detail",           # Construction details
    "mechanical_plan",  # HVAC ductwork layout
    "plumbing_plan",    # Pipe layout, WH location
]

SCHEDULE_SUBTYPES = [
    "window_schedule",      # Window specs, U/SHGC
    "equipment_schedule",   # HVAC, WH equipment
    "room_schedule",        # Room areas
    "wall_schedule",        # Wall assemblies
    "door_schedule",        # Door specs
    "energy_summary",       # Title-24 summary (Wade format)
]

# Content tags for semantic relevance markers
CONTENT_TAGS = [
    "north_arrow",          # orientation
    "room_labels",          # zones
    "area_callouts",        # zones, project
    "ceiling_heights",      # zones
    "window_callouts",      # windows
    "glazing_performance",  # windows (U-factor, SHGC)
    "hvac_equipment",       # hvac
    "hvac_specs",           # hvac (SEER, HSPF)
    "water_heater",         # dhw
    "dhw_specs",            # dhw (UEF)
    "wall_assembly",        # zones
    "insulation_values",    # zones
]


class PageInfo(BaseModel):
    """Information about a single page in the document."""
    page_number: int = Field(ge=1, description="Global 1-indexed page number (unique across all PDFs)")
    page_type: PageType = Field(description="Classified page type")
    confidence: Literal["high", "medium", "low"] = Field(description="Classification confidence level")
    description: Optional[str] = Field(default=None, description="Brief description of page content")

    # PDF source tracking (added in v2.0 for native PDF mode)
    pdf_name: str = Field(default="plans", description="Name of source PDF (without .pdf extension)")
    pdf_page_number: int = Field(default=1, ge=1, description="1-indexed page number within the source PDF")

    # Optional fields for intelligent routing (added in v2.0)
    subtype: Optional[str] = Field(
        default=None,
        description="Specific subtype (e.g., 'site_plan', 'window_schedule')"
    )
    content_tags: List[str] = Field(
        default_factory=list,
        description="Semantic tags indicating content relevance (e.g., 'north_arrow', 'hvac_specs')"
    )


class PDFSource(BaseModel):
    """Metadata about a source PDF file."""
    filename: str = Field(description="PDF filename (e.g., 'plans.pdf')")
    total_pages: int = Field(ge=1, description="Total number of pages in this PDF")


class DocumentMap(BaseModel):
    """Map of document structure with classified pages."""
    cache_version: int = Field(default=CACHE_VERSION, description="Schema version for cache migration")
    total_pages: int = Field(ge=1, description="Total number of pages in document")
    pages: List[PageInfo] = Field(description="List of classified pages")
    source_pdfs: Dict[str, PDFSource] = Field(
        default_factory=dict,
        description="Metadata about source PDFs keyed by name (e.g., {'plans': PDFSource(...)})"
    )

    # ========================================================================
    # Core type properties (existing)
    # ========================================================================

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

    # ========================================================================
    # Subtype and tag query methods (new)
    # ========================================================================

    def pages_by_subtype(self, subtype: str) -> List[int]:
        """Return page numbers matching a specific subtype."""
        return [p.page_number for p in self.pages if p.subtype == subtype]

    def pages_with_tag(self, tag: str) -> List[int]:
        """Return page numbers containing a specific content tag."""
        return [p.page_number for p in self.pages if tag in p.content_tags]

    def pages_with_any_tag(self, tags: List[str]) -> List[int]:
        """Return page numbers containing any of the specified tags."""
        tag_set = set(tags)
        return [p.page_number for p in self.pages if tag_set & set(p.content_tags)]

    # ========================================================================
    # Drawing subtype shortcuts
    # ========================================================================

    @property
    def site_plan_pages(self) -> List[int]:
        """Return pages classified as site plans."""
        return self.pages_by_subtype("site_plan")

    @property
    def floor_plan_pages(self) -> List[int]:
        """Return pages classified as floor plans."""
        return self.pages_by_subtype("floor_plan")

    @property
    def elevation_pages(self) -> List[int]:
        """Return pages classified as elevations."""
        return self.pages_by_subtype("elevation")

    @property
    def section_pages(self) -> List[int]:
        """Return pages classified as sections."""
        return self.pages_by_subtype("section")

    @property
    def detail_pages(self) -> List[int]:
        """Return pages classified as details."""
        return self.pages_by_subtype("detail")

    @property
    def mechanical_plan_pages(self) -> List[int]:
        """Return pages classified as mechanical plans."""
        return self.pages_by_subtype("mechanical_plan")

    @property
    def plumbing_plan_pages(self) -> List[int]:
        """Return pages classified as plumbing plans."""
        return self.pages_by_subtype("plumbing_plan")

    # ========================================================================
    # Schedule subtype shortcuts
    # ========================================================================

    @property
    def window_schedule_pages(self) -> List[int]:
        """Return pages classified as window schedules."""
        return self.pages_by_subtype("window_schedule")

    @property
    def equipment_schedule_pages(self) -> List[int]:
        """Return pages classified as equipment schedules."""
        return self.pages_by_subtype("equipment_schedule")

    @property
    def room_schedule_pages(self) -> List[int]:
        """Return pages classified as room schedules."""
        return self.pages_by_subtype("room_schedule")

    @property
    def wall_schedule_pages(self) -> List[int]:
        """Return pages classified as wall schedules."""
        return self.pages_by_subtype("wall_schedule")

    @property
    def energy_summary_pages(self) -> List[int]:
        """Return pages classified as energy summary (Title-24 summary)."""
        return self.pages_by_subtype("energy_summary")
