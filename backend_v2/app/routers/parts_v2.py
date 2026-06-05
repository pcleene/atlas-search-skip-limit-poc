"""
Parts Search API V2 - Using Native MongoDB Atlas Search Pagination

This version uses:
- searchSequenceToken for cursor generation
- searchAfter/searchBefore for pagination
- compound.filter for efficient filtering
- Built-in faceting
"""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime

from ..models import PartsSearchResponse, PartResponse, FacetResponse, FacetBucket, PaginationMeta
from ..database import get_database
from ..utils import PricingCalculator, FilterBuilder
from ..config import settings

router = APIRouter(prefix="/api/parts", tags=["parts"])


async def build_compound_search_operator(
    search_text: Optional[str],
    user_location: str,
    # Filters
    status: Optional[List[str]] = None,
    seller: Optional[List[str]] = None,
    excluded_companies: Optional[List[str]] = None,
    condition: Optional[List[str]] = None,
    location: Optional[List[str]] = None,
    airport_location: Optional[List[str]] = None,
    category: Optional[List[str]] = None,
    material_class: Optional[List[str]] = None,
    is_real_part: Optional[bool] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Build compound operator with both text search AND filters.

    Uses compound.filter which is more efficient than $match stage.
    """
    compound = {
        "must": [],
        "should": [],
        "filter": [],
        "mustNot": []
    }

    # TEXT SEARCH
    if search_text:
        # Add MUST clause to require at least one field to match
        # This ensures we only get matching documents, not all documents
        compound["must"].append({
            "text": {
                "query": search_text,
                "path": ["partNo", "name", "description", "serialNo", "batchNo", "companyName"]
            }
        })
        
        # Keep all SHOULD clauses for detailed relevance scoring
        compound["should"].extend([
            # Exact phrase match on part number (highest priority)
            {
                "phrase": {
                    "query": search_text,
                    "path": "partNo",
                    "score": {"boost": {"value": 10}}
                }
            },
            # Autocomplete on part number
            {
                "autocomplete": {
                    "query": search_text,
                    "path": "partNo",
                    "tokenOrder": "sequential",
                    "score": {"boost": {"value": 5}}
                }
            },
            # Autocomplete on name
            {
                "autocomplete": {
                    "query": search_text,
                    "path": "name",
                    "tokenOrder": "sequential",
                    "score": {"boost": {"value": 4}}
                }
            },
            # Text search on name
            {
                "text": {
                    "query": search_text,
                    "path": "name",
                    "score": {"boost": {"value": 3}}
                }
            },
            # Text search on description
            {
                "text": {
                    "query": search_text,
                    "path": "description",
                    "score": {"boost": {"value": 2}}
                }
            },
            # Text search on serial number
            {
                "text": {
                    "query": search_text,
                    "path": "serialNo",
                    "score": {"boost": {"value": 4}}
                }
            },
            # Text search on batch number
            {
                "text": {
                    "query": search_text,
                    "path": "batchNo",
                    "score": {"boost": {"value": 4}}
                }
            },
            # Text search on company name
            {
                "text": {
                    "query": search_text,
                    "path": "companyName",
                    "score": {"boost": {"value": 1.5}}
                }
            }
        ])
    else:
        # Initial load - prioritize by location
        compound["should"].append({
            "text": {
                "query": user_location,
                "path": "location",
                "score": {"boost": {"value": 2}}
            }
        })

        # Also match all documents
        compound["should"].append({
            "exists": {
                "path": "partNo"
            }
        })

    # FILTERS (using compound.filter - more efficient!)
    filter_clauses = FilterBuilder.build_compound_filter(
        status=status,
        seller=seller,
        excluded_companies=excluded_companies,
        condition=condition,
        location=location,
        airport_location=airport_location,
        category=category,
        material_class=material_class,
        is_real_part=is_real_part,
        min_price=min_price,
        max_price=max_price
    )

    if filter_clauses:
        compound["filter"] = filter_clauses

    # Excluded companies (use mustNot)
    if excluded_companies:
        compound["mustNot"].append({
            "in": {
                "path": "companyCode",
                "value": excluded_companies
            }
        })

    # Clean up empty arrays
    compound = {k: v for k, v in compound.items() if v}

    return compound


@router.get("/search", response_model=PartsSearchResponse)
async def search_parts(
    # Search parameters
    search_text: Optional[str] = Query(None, description="Search text for part number, name, description, etc."),

    # Filter parameters
    seller: Optional[List[str]] = Query(None, description="Filter by seller company codes"),
    condition: Optional[List[str]] = Query(None, description="Filter by condition (New, Used, etc.)"),
    location: Optional[List[str]] = Query(None, description="Filter by location"),
    airport_location: Optional[List[str]] = Query(None, description="Filter by airport location"),
    category: Optional[List[str]] = Query(None, description="Filter by ATA chapter/category"),
    status: Optional[List[str]] = Query(["Active", "Pending Update"], description="Filter by status"),
    material_class: Optional[List[str]] = Query(None, description="Filter by material class"),

    # Price filtering
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price filter"),

    # Special filters
    is_real_part: Optional[bool] = Query(None, description="Filter for real parts only"),

    # Excluded companies
    excluded_companies: Optional[List[str]] = Query(None, description="Company codes to exclude"),

    # Sorting
    sort_by: str = Query("price", description="Field to sort by (price, updatedAt, etc.)"),
    sort_order: str = Query("asc", regex="^(asc|desc)$", description="Sort order"),

    # Pagination
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),

    # Pricing parameters
    forex_rate: float = Query(settings.default_forex_rate, description="Forex rate for currency conversion"),
    markup: float = Query(settings.default_markup, description="Markup percentage (0.2 = 20%)"),
    user_currency: str = Query(settings.default_user_currency, description="User's local currency"),
    user_location: str = Query(settings.default_user_location, description="User's country code"),

    # Faceting
    use_facets: bool = Query(True, description="Include facets in response"),
):
    """
    Parts search endpoint using MongoDB Atlas Search with offset pagination.

    V2 Features (Offset Pagination Version):
    - Runtime price calculation in aggregation pipeline
    - Sort by calculated custom prices (forex + markup)
    - Traditional page-based pagination (skip/limit)
    - Allows accurate sorting by displayed prices
    - compound.filter for efficient filtering
    """
    db = await get_database()
    collection = db["parts_search"]

    # Build compound operator
    compound_operator = await build_compound_search_operator(
        search_text=search_text,
        user_location=user_location,
        status=status,
        seller=seller,
        excluded_companies=excluded_companies,
        condition=condition,
        location=location,
        airport_location=airport_location,
        category=category,
        material_class=material_class,
        is_real_part=is_real_part,
        min_price=min_price,
        max_price=max_price
    )

    # Build sort (with deterministic tiebreaker)
    sort_direction = 1 if sort_order == "asc" else -1
    
    # For V2: We calculate price in pipeline, so don't sort in $search for price
    if sort_by == "relevance":
        # Relevance: Let Atlas Search handle natural relevance scoring
        sort_in_search = None
    elif sort_by == "price":
        # Price: Will sort AFTER calculating custom price in pipeline
        sort_in_search = None
    else:
        # Other fields: Sort in $search (e.g., updatedAt, partNo)
        sort_in_search = {
            sort_by: sort_direction,
            "_id": sort_direction  # Tiebreaker
        }

    # Build facet definitions
    facets_def = {}
    if use_facets:
        facets_def = {
            "sellerFacet": {
                "type": "string",
                "path": "companyCode",
                "numBuckets": 50
            },
            "conditionFacet": {
                "type": "string",
                "path": "condition",
                "numBuckets": 20
            },
            "locationFacet": {
                "type": "string",
                "path": "location",
                "numBuckets": 50
            },
            "airportLocationFacet": {
                "type": "string",
                "path": "airportLocation",
                "numBuckets": 50
            },
            "categoryFacet": {
                "type": "string",
                "path": "chapter.category",
                "numBuckets": 50
            },
            "materialClassFacet": {
                "type": "string",
                "path": "materialClass",
                "numBuckets": 20
            }
        }

    # Add facets if requested
    # Build pipeline
    pipeline = []

    # Construct $search stage based on the "Integrated Facet" pattern
    if facets_def:
        search_cmd = {
            "index": settings.atlas_search_index_name,
            "facet": {
                "operator": {
                    "compound": compound_operator,
                },
                "facets": facets_def
            },
            "count": {"type": "total"}
        }
        # Only add sort if sort_in_search is not None
        if sort_in_search is not None:
            search_cmd["sort"] = sort_in_search
    else:
        search_cmd = {
            "index": settings.atlas_search_index_name,
            "compound": compound_operator,
            "count": {"type": "total"}
        }
        # Only add sort if sort_in_search is not None
        if sort_in_search is not None:
            search_cmd["sort"] = sort_in_search

    pipeline.append({"$search": search_cmd})

    # V2: PERFORMANCE: Limit to 1000 docs before expensive operations
    # This prevents calculating prices on 100k+ documents
    pipeline.append({"$limit": 1000})

    # V2: Calculate custom pricing in the aggregation pipeline
    # This allows us to sort by the actual displayed prices
    pipeline.append({
        "$addFields": {
            "localPrice": {"$multiply": ["$price", forex_rate]},
            "localMarkupPrice": {
                "$multiply": [
                    {"$multiply": ["$price", forex_rate]},
                    {"$add": [1, markup]}
                ]
            },
            "localCurrency": user_currency,
            "markupPrice": {
                "$multiply": ["$price", {"$add": [1, markup]}]
            }
        }
    })

    # V2: Add $sort stage AFTER price calculation (for price sorting)
    if sort_by == "price":
        pipeline.append({
            "$sort": {
                "localMarkupPrice": sort_direction,
                "_id": sort_direction  # Tiebreaker
            }
        })
    elif sort_by != "relevance" and sort_in_search is None:
        # For fields not sorted in $search, sort here
        pipeline.append({
            "$sort": {
                sort_by: sort_direction,
                "_id": sort_direction
            }
        })

    # V2: Offset pagination (skip + limit)
    skip_count = (page - 1) * limit
    pipeline.append({"$skip": skip_count})
    
    pipeline.extend([
        {"$limit": limit + 1},  # Fetch one extra to detect has_more
        {
            "$facet": {
                "results": [
                    {
                        "$project": {
                            "_id": 1,
                            "partId": 1,
                            "partNo": 1,
                            "name": 1,
                            "description": 1,
                            "materialClass": 1,
                            "condition": 1,
                            "location": 1,
                            "serialNo": 1,
                            "batchNo": 1,
                            "manufacturer": 1,
                            "stock": 1,
                            "price": 1,
                            "currency": 1,
                            "companyName": 1,
                            "companyCode": 1,
                            "status": 1,
                            "updatedAt": 1,
                            "isRealPart": 1,
                            # V2: Include calculated prices
                            "localPrice": 1,
                            "localMarkupPrice": 1,
                            "localCurrency": 1,
                            "markupPrice": 1
                        }
                    }
                ],
                "metadata": [
                    {"$replaceWith": "$$SEARCH_META"},
                    {"$limit": 1}
                ]
            }
        }
    ])

    # Execute query
    cursor_obj = collection.aggregate(pipeline)
    result = await cursor_obj.to_list(length=1)

    if not result or not result[0]:
         return PartsSearchResponse(
            parts=[],
            facets=[],
            pagination=PaginationMeta(
                limit=limit,
                has_more=False,
                current_page_start=0,
                current_page_end=0,
                total_count=0
            ),
            search_metadata={
                "search_text": search_text,
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        )

    parts_list = result[0].get("results", [])
    meta_list = result[0].get("metadata", [])
    metadata = meta_list[0] if meta_list else {}
    metadata = result[0].get("metadata", [{}])[0]

    # V2: Determine has_more (we fetched limit + 1)
    has_more = len(parts_list) > limit

    # Remove extra document if we fetched limit + 1
    if has_more:
        parts_list = parts_list[:limit]

    # V2: Pricing already calculated in pipeline, just convert ObjectId to string
    for part in parts_list:
        if "_id" in part and hasattr(part["_id"], "__str__"):
            part["_id"] = str(part["_id"])

    # Parse facets
    facets = []
    if use_facets and "facet" in metadata:
        facet_data = metadata["facet"]

        facet_mapping = {
            "sellerFacet": "seller",
            "conditionFacet": "condition",
            "locationFacet": "location",
            "airportLocationFacet": "airportLocation",
            "categoryFacet": "category",
            "materialClassFacet": "materialClass"
        }

        for facet_key, field_name in facet_mapping.items():
            if facet_key in facet_data and "buckets" in facet_data[facet_key]:
                buckets = [
                    FacetBucket(value=bucket["_id"], count=bucket["count"])
                    for bucket in facet_data[facet_key]["buckets"]
                ]

                facets.append(FacetResponse(
                    field=field_name,
                    buckets=buckets
                ))

    # Get total count
    total_count = metadata.get("count", {}).get("lowerBound", None)

    # Build response
    return PartsSearchResponse(
        parts=parts_list,  # V2: Already has pricing from pipeline
        facets=facets,
        pagination=PaginationMeta(
            limit=limit,
            has_more=has_more,
            next_cursor=None,  # V2: No cursors in offset pagination
            prev_cursor=None,  # V2: No cursors in offset pagination
            total_count=total_count,
            current_page_start=skip_count + 1,
            current_page_end=skip_count + len(parts_list)
        ),
        search_metadata={
            "search_text": search_text,
            "sort_by": sort_by,
            "sort_order": sort_order,
            "page": page,  # V2: Include page number
            "filters_applied": {
                "status": status,
                "seller": seller,
                "condition": condition,
                "location": location
            },
            "forex_rate": forex_rate,
            "markup": markup
        }
    )
