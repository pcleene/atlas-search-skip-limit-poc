"""
Pydantic models for Parts API responses
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class PaginationMeta(BaseModel):
    """Pagination metadata for response"""
    limit: int
    has_more: bool
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    total_count: Optional[int] = None
    current_page_start: int
    current_page_end: int


class FacetBucket(BaseModel):
    """Individual facet bucket"""
    value: str
    count: int


class FacetResponse(BaseModel):
    """Facet data for a specific field"""
    field: str
    buckets: List[FacetBucket]


class PartResponse(BaseModel):
    """Individual part in search results"""
    part_id: str = Field(alias="_id")
    part_no: str = Field(alias="partNo")
    name: str
    description: Optional[str] = None
    material_class: str = Field(alias="materialClass")
    condition: str
    location: str
    serial_no: Optional[str] = Field(None, alias="serialNo")
    batch_no: Optional[str] = Field(None, alias="batchNo")
    manufacturer: Optional[str] = None

    # Stock and pricing
    stock: int
    price: float
    local_price: float = Field(alias="localPrice")
    markup_price: float = Field(alias="markupPrice")
    local_markup_price: float = Field(alias="localMarkupPrice")
    currency: str
    local_currency: str = Field(alias="localCurrency")

    # Seller info
    seller_company: str = Field(alias="companyName")
    seller_code: str = Field(alias="companyCode")

    # Metadata
    status: str
    updated_at: datetime = Field(alias="updatedAt")
    is_real_part: bool = Field(alias="isRealPart")

    # Atlas Search score
    search_score: Optional[float] = None

    # Pagination token (hidden from user, used internally)
    pagination_token: Optional[str] = Field(None, exclude=True)

    class Config:
        populate_by_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class PartsSearchResponse(BaseModel):
    """Complete search response with results, facets, and pagination"""
    parts: List[PartResponse]
    facets: List[FacetResponse]
    pagination: PaginationMeta
    search_metadata: Dict[str, Any]
