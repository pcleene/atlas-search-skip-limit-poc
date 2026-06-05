"""
Atlas Search query builders and filter utilities
"""
from typing import Dict, Any, List, Optional
from bson import ObjectId
from datetime import datetime


class AtlasSearchQueryBuilder:
    """
    Build MongoDB Atlas Search queries with proper operators.
    """

    @staticmethod
    def build_text_search(
        search_text: str,
        user_location: Optional[str] = None,
        index_name: str = "parts_search_index"
    ) -> Dict[str, Any]:
        """
        Build compound text search query for Atlas Search.

        This searches across multiple fields with different boost scores:
        - partNo (exact phrase): 10x boost
        - partNo (autocomplete): 5x boost
        - name: 3x boost
        - description: 2x boost
        - serialNo: 4x boost
        - batchNo: 4x boost
        - companyName: 1.5x boost
        """
        should_clauses = [
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
        ]

        # Optionally boost results from user's location
        if user_location:
            should_clauses.append({
                "text": {
                    "query": user_location,
                    "path": "location",
                    "score": {"boost": {"value": 1.2}}
                }
            })

        return {
            "$search": {
                "index": index_name,
                "compound": {
                    "should": should_clauses
                }
            }
        }

    @staticmethod
    def build_initial_load_search(
        user_location: str,
        index_name: str = "parts_search_index"
    ) -> Dict[str, Any]:
        """
        Build search query for initial load (no search text).

        Prioritizes:
        1. Parts from user's location (2x boost)
        2. All other parts (1x score)
        """
        return {
            "$search": {
                "index": index_name,
                "compound": {
                    "should": [
                        # Prioritize parts from user's location
                        {
                            "text": {
                                "query": user_location,
                                "path": "location",
                                "score": {"boost": {"value": 2}}
                            }
                        },
                        # Match all documents
                        {
                            "exists": {
                                "path": "partNo"
                            }
                        }
                    ]
                }
            }
        }


class FilterBuilder:
    """
    Build MongoDB filter queries without regex.
    """

    @staticmethod
    def build_compound_filter(
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
        Build compound filter for use within Atlas Search $search stage.

        Returns filter clauses for use in compound.filter array.
        """
        filters = []

        # Status filter
        # Note: 'status' field is indexed as 'string' (lucene.keyword) in the Atlas Search index.
        # To filter on it efficiently using 'equals' or 'in', we must ensure we match the type.
        if status:
            filters.append({
                "in": {
                    "path": "status",
                    "value": status
                }
            })

        # Seller filter
        if seller:
            filters.append({
                "in": {
                    "path": "companyCode",
                    "value": seller
                }
            })

        # Condition filter
        if condition:
            filters.append({
                "in": {
                    "path": "condition",
                    "value": condition
                }
            })

        # Location filters
        if location:
            filters.append({
                "in": {
                    "path": "location",
                    "value": location
                }
            })

        if airport_location:
            filters.append({
                "in": {
                    "path": "airportLocation",
                    "value": airport_location
                }
            })

        # Category filter
        if category:
            filters.append({
                "in": {
                    "path": "chapter.category",
                    "value": category
                }
            })

        # Material class filter
        if material_class:
            filters.append({
                "in": {
                    "path": "materialClass",
                    "value": material_class
                }
            })

        # Real part filter
        if is_real_part is not None:
            filters.append({
                "equals": {
                    "path": "isRealPart",
                    "value": is_real_part
                }
            })

        # Price filtering (range)
        if min_price is not None or max_price is not None:
            price_range = {"path": "price"}
            if min_price is not None:
                price_range["gte"] = min_price
            if max_price is not None:
                price_range["lte"] = max_price

            filters.append({
                "range": price_range
            })

        return filters
