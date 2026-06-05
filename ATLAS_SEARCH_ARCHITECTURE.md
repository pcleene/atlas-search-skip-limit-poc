# Atlas Search Parts Search Application V2 - Architecture Documentation

## Overview

**This V2 implementation uses offset-based pagination (skip/limit) with runtime price calculation.**

This application demonstrates a production-ready parts search system using **MongoDB Atlas Search** with integrated faceting, **offset-based pagination**, and **runtime price calculation in the aggregation pipeline**. 

### Why Skip/Limit Instead of searchSequenceToken?

This implementation uses **skip/limit** instead of **searchSequenceToken** (cursor-based pagination) for a critical reason:

**The client requirement:** Calculate custom prices (forex conversion + markup) at runtime and **sort by these calculated prices**, not the database prices.

**Why searchSequenceToken fails here:**
- `searchSequenceToken` generates cursor positions based on the **initial sort order** from `$search`
- When prices are calculated in `$addFields` and documents are re-sorted by `$sort` on `localMarkupPrice`, the document order changes
- The cursor positions from the original sort are now **invalid** for the new sort order
- Attempting to use `searchAfter`/`searchBefore` with the old cursor on the new order causes incorrect pagination

**The solution:** Use **skip/limit** which works with any sort order, though it sacrifices deep pagination performance.

The system consists of a FastAPI backend (port 8001) and vanilla JavaScript frontend (port 8081).

**Note**: For implementation details, see [V2_IMPLEMENTATION_GUIDE.md](V2_IMPLEMENTATION_GUIDE.md).

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Atlas Search Implementation](#atlas-search-implementation)
3. [Backend Structure](#backend-structure)
4. [Frontend Structure](#frontend-structure)
5. [Data Flow](#data-flow)
6. [Key Features](#key-features)

---

## Architecture Overview

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │         │                 │
│    Frontend     │────────▶│    Backend      │────────▶│  MongoDB Atlas  │
│  (Vanilla JS)   │  HTTP   │   (FastAPI)     │  Motor  │  Search Index   │
│                 │◀────────│                 │◀────────│                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Technology Stack

- **Frontend**: Vanilla JavaScript, HTML5, CSS3
- **Backend**: Python 3.14, FastAPI, Motor (async MongoDB driver)
- **Database**: MongoDB Atlas with Atlas Search
- **Search Engine**: Atlas Search (Lucene-based)

---

## Atlas Search Implementation

### 1. Search Index Configuration

The application uses a MongoDB Atlas Search index named `parts_search_index` on the `PartsDistributor.parts_search` collection.

#### Index Definition (`data/atlas_index_final.json`)

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "partNo": [
        {"type": "string", "analyzer": "lucene.standard"},
        {"type": "autocomplete", "tokenization": "edgeGram", "minGrams": 2, "maxGrams": 15}
      ],
      "name": [
        {"type": "string", "analyzer": "lucene.standard"},
        {"type": "autocomplete", "tokenization": "edgeGram", "minGrams": 2, "maxGrams": 15}
      ],
      "description": {"type": "string", "analyzer": "lucene.standard"},
      "companyName": {"type": "string", "analyzer": "lucene.standard"},
      "serialNo": {"type": "string", "analyzer": "lucene.keyword"},
      "batchNo": {"type": "string", "analyzer": "lucene.keyword"},
      "status": {"type": "token"},
      "condition": {"type": "token"},
      "location": {"type": "token"},
      "airportLocation": {"type": "token"},
      "materialClass": {"type": "token"},
      "companyCode": {"type": "token"},
      "chapter.category": {"type": "token"},
      "price": {"type": "number"},
      "updatedAt": {"type": "date"},
      "isRealPart": {"type": "boolean"}
    }
  }
}
```

#### Field Type Explanations

| Field Type | Purpose | Example Use Case |
|------------|---------|------------------|
| **string (lucene.standard)** | Full-text search with tokenization | Searching part names, descriptions |
| **autocomplete** | Real-time search suggestions | Auto-completing part numbers as user types |
| **token** | Exact match filtering (facets) | Filtering by status, condition, location |
| **number** | Numeric range queries | Price range filtering |
| **date** | Date-based sorting/filtering | Sorting by update date |

**Key Points:**
- `partNo` and `name` have **dual types** (string + autocomplete) for both full search and autocomplete
- **token** type is used for fields that need exact matching in facets (not analyzed/tokenized)
- `dynamic: false` means only explicitly defined fields are indexed

---

### 2. The V2 Pipeline Pattern (Skip/Limit with Runtime Pricing)

V2 uses a modified pipeline that calculates prices **before sorting**, then uses **skip/limit** for pagination.

#### V2 Pipeline Structure

```javascript
// V2 Actual Pipeline (from parts_v2.py)
[
  {
    $search: {
      index: "parts_search_index",
      facet: {
        operator: { compound: { /* search query */ } },
        facets: { /* facet definitions */ }
      },
      // sort: omitted for price sorting (will sort after price calc)
      count: { type: "total" }
    }
  },
  { $limit: 1000 },  // V2: Performance - limit before price calculation
  
  // V2: Calculate custom prices in pipeline
  {
    $addFields: {
      localPrice: { $multiply: ["$price", forex_rate] },
      localMarkupPrice: {
        $multiply: [
          { $multiply: ["$price", forex_rate] },
          { $add: [1, markup] }
        ]
      },
      localCurrency: user_currency
    }
  },
  
  // V2: Sort by calculated price (if sorting by price)
  { $sort: { localMarkupPrice: 1, _id: 1 } },
  
  // V2: Offset pagination
  { $skip: (page - 1) * limit },
  { $limit: limit + 1 },  // Fetch one extra for "has_more" detection
  
  {
    $facet: {
      results: [ /* project fields including calculated prices */ ],
      metadata: [ { $replaceWith: "$$SEARCH_META" } ]
    }
  }
]
```

**Key differences from cursor-based:**
- Price calculation happens **before sorting** (lines 3-4)
- Sort uses **calculated field** `localMarkupPrice` (line 5)
- Uses **$skip** instead of searchAfter/searchBefore (line 6)
- No `paginationToken` in projection (searchSequenceToken not used)

---

### 3. Building the Compound Search Query

Location: `backend/app/routers/parts_v2.py` (lines 165-240)

#### Step 1: Initialize Compound Operator

```python
compound_operator = {
    "must": [],      # Required conditions (AND logic)
    "should": [],    # Optional conditions (OR logic, boost relevance)
    "filter": []     # Filter without affecting score
}
```

#### Step 2: Add Text Search (if provided)

```python
if search_text:
    compound_operator["should"].append({
        "text": {
            "query": search_text,
            "path": ["partNo", "name", "description", "companyName"],
            "fuzzy": {"maxEdits": 1}  # Allow typos (1 character difference)
        }
    })
```

**How it works:**
- Searches across multiple fields simultaneously
- Ranks results by relevance (more matches = higher score)
- `fuzzy` allows typo tolerance (e.g., "bering" matches "bearing")

#### Step 3: Add Filters (Facet Selections)

```python
# Example: Filter by status
if status:
    compound_operator["filter"].append({
        "in": {
            "path": "status",
            "value": status  # ["Active", "Pending Update"]
        }
    })

# Example: Filter by seller
if seller:
    compound_operator["filter"].append({
        "in": {
            "path": "companyCode",
            "value": seller
        }
    })
```

**Filter vs Must vs Should:**
- **filter**: Excludes documents but doesn't affect search score (faster)
- **must**: Required to match AND affects score
- **should**: Optional to match but boosts score if matched

#### Step 4: Add Price Range Filter

```python
if min_price is not None or max_price is not None:
    range_query = {"path": "price"}
    if min_price is not None:
        range_query["gte"] = min_price  # Greater than or equal
    if max_price is not None:
        range_query["lte"] = max_price  # Less than or equal
    
    compound_operator["filter"].append({"range": range_query})
```

---

### 4. Sorting Logic (V2 - Critical for Runtime Pricing)

Location: `backend_v2/app/routers/parts_v2.py` (lines 251-372)

```python
# V2: Build sort specification
sort_direction = 1 if sort_order == "asc" else -1

if sort_by == "relevance":
    # For relevance sorting, omit sort in $search
    sort_in_search = None
elif sort_by == "price":
    # V2 CRITICAL: Price sorting happens AFTER price calculation
    # Cannot sort in $search because prices don't exist yet
    sort_in_search = None
else:
    # Other fields: can sort in $search stage
    sort_in_search = {
        sort_by: sort_direction,
        "_id": sort_direction  # Tiebreaker
    }

# Later in pipeline (lines 358-364):
if sort_by == "price":
    pipeline.append({
        "$sort": {
            "localMarkupPrice": sort_direction,  # Sort by calculated price!
            "_id": sort_direction
        }
    })
```

**V2 Key Insight:**
- Price sorting MUST happen **after** `$addFields` calculates `localMarkupPrice`
- This is why searchSequenceToken breaks: cursors are from the $search order, but docs are now in $sort order
- `_id` tiebreaker ensures consistent ordering

---

### 5. Facet Definitions

Location: `backend_v2/app/routers/parts_v2.py` (lines 268-302)

```python
facets_def = {
    "sellerFacet": {
        "type": "string",
        "path": "companyCode",
        "numBuckets": 50  # Return top 50 sellers
    },
    "conditionFacet": {
        "type": "string",
        "path": "condition",
        "numBuckets": 20
    },
    # ... more facets
}
```

**How Facets Work:**
1. Atlas Search analyzes **all matching documents** (before pagination)
2. Groups documents by field values
3. Counts occurrences in each group ("bucket")
4. Returns top N buckets sorted by count

**Example Output:**
```json
{
  "sellerFacet": {
    "buckets": [
      {"_id": "PartsDistributor", "count": 202},
      {"_id": "Boeing", "count": 156},
      {"_id": "Airbus", "count": 89}
    ]
  }
}
```

---

### 6. The Complete V2 Pipeline with Runtime Pricing

Location: `backend_v2/app/routers/parts_v2.py` (lines 306-418)

**This is the actual V2 implementation:**

```python
pipeline = []

# Step 1: $search with integrated facets
if facets_def:
    search_cmd = {
        "index": settings.atlas_search_index_name,
        "facet": {
            "operator": {"compound": compound_operator},
            "facets": facets_def
        },
        "count": {"type": "total"}
    }
    if sort_in_search is not None:  # Skip sort for price (will sort after calc)
        search_cmd["sort"] = sort_in_search
else:
    search_cmd = {
        "index": settings.atlas_search_index_name,
        "compound": compound_operator,
        "count": {"type": "total"}
    }
    if sort_in_search is not None:
        search_cmd["sort"] = sort_in_search

pipeline.append({"$search": search_cmd})

# Step 2: V2 PERFORMANCE - Limit before price calculation
pipeline.append({"$limit": 1000})

# Step 3: V2 CRITICAL - Calculate prices in pipeline
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
        "markupPrice": {"$multiply": ["$price", {"$add": [1, markup]}]}
    }
})

# Step 4: V2 CRITICAL - Sort by calculated price
if sort_by == "price":
    pipeline.append({
        "$sort": {
            "localMarkupPrice": sort_direction,  # THIS invalidates cursors!
            "_id": sort_direction
        }
    })

# Step 5: V2 - Offset pagination (only option after re-sort)
skip_count = (page - 1) * limit
pipeline.append({"$skip": skip_count})

pipeline.extend([
    {"$limit": limit + 1},
    {
        "$facet": {
            "results": [
                {
                    "$project": {
                        "_id": 1,
                        "partNo": 1,
                        # ... all fields
                        # V2: Include calculated prices
                        "localPrice": 1,
                        "localMarkupPrice": 1,
                        "localCurrency": 1,
                        # NO paginationToken - searchSequenceToken is invalid
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
```

**V2 Pipeline Flow:**
1. **$search**: Atlas Search with facets
2. **$limit 1000**: Performance - don't calc prices for all docs
3. **$addFields**: Calculate `localMarkupPrice` (runtime pricing)
4. **$sort**: Re-sort by calculated price ← **This breaks searchSequenceToken!**
5. **$skip**: Offset pagination (only option now)
6. **$limit**: Fetch extras for has_more detection
7. **$facet**: Split results and metadata

---

### 7. Cursor-Based Pagination

**Why Cursor-Based?**
- Traditional offset pagination (`skip(20)`) is **slow** for large datasets
- Cursor pagination uses the last document's position as a "bookmark"
- Much faster and more reliable for deep pagination

#### How It Works

```python
# First page: No cursor
GET /api/parts/search?limit=20

# Next page: Use searchAfter with last doc's token
GET /api/parts/search?limit=20&cursor=CAIiDloMaR58r4tJnMk...&direction=next

# Previous page: Use searchBefore
GET /api/parts/search?cursor=CAIiDloMaR58r4tJnMk...&direction=prev
```

#### Pagination Token

```python
"paginationToken": {"$meta": "searchSequenceToken"}
```

- Each document gets a unique `searchSequenceToken` from Atlas Search
- This token encodes the document's position in the sorted result set
- Tokens are opaque (encrypted) and only valid for the same search query

#### Has More Detection

```python
# Fetch limit + 1 documents
has_more = len(parts_list) > limit

if has_more:
    parts_list = parts_list[:limit]  # Trim extra doc
```

If we got 21 docs when asking for 20, there are more pages available.

---

### 8. Processing Search Results

Location: `backend/app/routers/parts_v2.py` (lines 378-487)

```python
# Execute aggregation
result = await collection.aggregate(pipeline).to_list(length=1)

parts_list = result[0].get("results", [])
metadata = result[0].get("metadata", [{}])[0]

# Detect has_more
has_more = len(parts_list) > limit
if has_more:
    parts_list = parts_list[:limit]

# Extract cursors from first and last documents
first_cursor = parts_list[0].get("paginationToken") if parts_list else None
last_cursor = parts_list[-1].get("paginationToken") if parts_list else None

# Determine navigation cursors based on direction
if direction == "next":
    next_cursor = last_cursor if has_more else None
    prev_cursor = first_cursor  # Can always go back
else:  # direction == "prev"
    next_cursor = last_cursor  # Can go forward
    prev_cursor = first_cursor if cursor else None
```

#### Cursor Logic Explanation

| Scenario | next_cursor | prev_cursor |
|----------|-------------|-------------|
| First page, has more | Last doc's token | None |
| Middle page | Last doc's token | First doc's token |
| Last page | None | First doc's token |
| Going backward | Last doc's token | First doc's token (if not first page) |

---

### 9. Custom Pricing Application

Location: `backend/app/utils/pricing.py`

After fetching search results, each part gets custom pricing applied:

```python
parts_with_pricing = PricingCalculator.apply_pricing_to_parts(
    parts=parts_list,
    forex_rate=forex_rate,      # e.g., 4.5 (USD to MYR)
    markup=markup,              # e.g., 0.15 (15% markup)
    local_currency=user_currency # e.g., "MYR"
)
```

**Pricing Logic:**
```python
# Convert to local currency
local_price = price * forex_rate

# Apply markup
local_markup_price = local_price * (1 + markup)
```

This allows demonstrating **dynamic pricing** per customer without modifying the database.

---

### 10. Facet Response Structure

Location: `backend/app/routers/parts_v2.py` (lines 432-456)

```python
# Extract facet data from $$SEARCH_META
facet_data = metadata.get("facet", {})

# Map internal facet names to user-facing names
facet_mapping = {
    "sellerFacet": "seller",
    "conditionFacet": "condition",
    "locationFacet": "location",
    "airportLocationFacet": "airportLocation",
    "categoryFacet": "category",
    "materialClassFacet": "materialClass"
}

facets = []
for facet_key, field_name in facet_mapping.items():
    if facet_key in facet_data and "buckets" in facet_data[facet_key]:
        buckets = [
            FacetBucket(value=bucket["_id"], count=bucket["count"])
            for bucket in facet_data[facet_key]["buckets"]
        ]
        facets.append(FacetResponse(field=field_name, buckets=buckets))
```

**Output Example:**
```json
{
  "facets": [
    {
      "field": "seller",
      "buckets": [
        {"value": "PartsDistributor", "count": 202},
        {"value": "Boeing", "count": 156}
      ]
    },
    {
      "field": "condition",
      "buckets": [
        {"value": "New", "count": 450},
        {"value": "Overhauled", "count": 320}
      ]
    }
  ]
}
```

---

### 11. Autocomplete Implementation

Location: `backend/app/routers/parts_v2.py` (autocomplete endpoint)

```python
@router.get("/autocomplete")
async def autocomplete_parts(
    q: str = Query(..., min_length=2),
    limit: int = Query(10, ge=1, le=20)
):
    pipeline = [
        {
            "$search": {
                "index": "parts_search_index",
                "autocomplete": {
                    "query": q,
                    "path": "partNo",  # Search in part number field
                    "tokenOrder": "sequential"  # Match character order
                }
            }
        },
        {"$limit": limit},
        {"$project": {"_id": 0, "partNo": 1, "name": 1}}
    ]
    
    results = await collection.aggregate(pipeline).to_list(length=limit)
    return results
```

**How Autocomplete Works:**
1. User types "AB" → Query `partNo` autocomplete index
2. Atlas Search uses **edgeGram** tokenization (2-15 character prefixes)
3. Returns parts with numbers starting with "AB" (e.g., "AB123", "AB456")
4. Frontend displays suggestions in real-time

**edgeGram Tokenization Example:**
- Input: "ABC123"
- Tokens generated: "AB", "ABC", "ABC1", "ABC12", "ABC123"
- Query "AB" matches because "AB" token exists

---

## Backend Structure

### Directory Layout

```
backend/
├── app/
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration (MongoDB URI, etc.)
│   ├── routers/
│   │   └── parts_v2.py         # Main search endpoint
│   ├── models/
│   │   └── parts.py            # Pydantic response models
│   ├── utils/
│   │   └── pricing.py          # Dynamic pricing calculator
│   └── db.py                   # MongoDB connection
├── requirements.txt            # Python dependencies
└── .env                        # Environment variables
```

### Key Files

#### 1. `main.py` - Application Entry

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import parts_v2

app = FastAPI(title="Automotive Parts Catalog Search API")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(parts_v2.router, prefix="/api", tags=["parts"])
```

#### 2. `config.py` - Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    mongodb_uri: str
    database_name: str = "PartsDistributor"
    collection_name: str = "parts_search"
    atlas_search_index_name: str = "parts_search_index"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

#### 3. `db.py` - Database Connection

```python
from motor.motor_asyncio import AsyncIOMotorClient
from app.config import settings

client: AsyncIOMotorClient = None

async def get_database():
    return client[settings.database_name]

async def get_collection():
    db = await get_database()
    return db[settings.collection_name]
```

---

## Frontend Structure

### Directory Layout

```
frontend/
├── index.html              # Main HTML structure
├── css/
│   └── styles.css          # All styles
└── js/
    ├── api.js              # API communication layer
    └── app.js              # Main application logic
```

### Key Components

#### 1. `api.js` - API Layer

```javascript
class PartsAPI {
    constructor() {
        this.baseURL = 'http://localhost:8000/api';
        this.abortController = null;
    }
    
    async searchParts(params) {
        // Cancel previous request
        if (this.abortController) {
            this.abortController.abort();
        }
        
        this.abortController = new AbortController();
        
        // Build query string
        const queryParams = new URLSearchParams({
            search_text: params.searchText || '',
            sort_by: params.sortBy || 'price',
            sort_order: params.sortOrder || 'asc',
            limit: params.limit || 20,
            // ... more params
        });
        
        const response = await fetch(
            `${this.baseURL}/parts/search?${queryParams}`,
            { signal: this.abortController.signal }
        );
        
        return await response.json();
    }
}
```

**Features:**
- Request cancellation (prevents race conditions)
- Query string building
- Error handling

#### 2. `app.js` - Application Logic

**State Management:**
```javascript
class PartsSearchApp {
    constructor() {
        this.currentSearchParams = { /* search state */ };
        this.currentCursor = null;
        this.nextCursor = null;
        this.prevCursor = null;
        this.currentPageNumber = 1;  // Track current page
        this.facets = [];
    }
}
```

**Search Flow:**
```javascript
async performSearch(resetPagination = false) {
    if (resetPagination) {
        this.currentCursor = null;
        this.currentPageNumber = 1;  // Reset to page 1
    }
    
    const response = await partsAPI.searchParts({...});
    
    this.renderResults(response);
    this.updatePagination(response.pagination);
    this.updateFacets(response.facets);
}
```

**Pagination:**
```javascript
updatePagination(pagination) {
    // Calculate page range
    const start = ((this.currentPageNumber - 1) * limit) + 1;
    const end = this.currentPageNumber * limit;
    
    // Display: "Showing 1-20", "Showing 21-40", etc.
    pageInfo.textContent = `Showing ${start}-${end}`;
}

goToNextPage() {
    this.currentCursor = this.nextCursor;
    this.currentPageNumber++;
    this.performSearch(false);
}
```

---

## Data Flow

### Complete Search Request Flow

```
1. USER TYPES IN SEARCH BOX
   ↓
2. FRONTEND: Debounce (300ms wait)
   ↓
3. FRONTEND: Build search params
   {
     searchText: "bearing",
     sortBy: "relevance",
     limit: 20,
     filters: { condition: ["New"] }
   }
   ↓
4. FRONTEND: Make API call
   GET /api/parts/search?search_text=bearing&sort_by=relevance&...
   ↓
5. BACKEND: Build compound query
   {
     compound: {
       should: [text search],
       filter: [status, condition filters]
     }
   }
   ↓
6. BACKEND: Build facet definitions
   ↓
7. BACKEND: Construct aggregation pipeline
   [$search with facet, $limit, $facet]
   ↓
8. MONGODB ATLAS SEARCH:
   - Execute full-text search across indexed fields
   - Apply filters
   - Generate facet counts
   - Sort results by relevance or field
   - Return paginated results with metadata
   ↓
9. BACKEND: Process results
   - Extract parts list
   - Extract facet data
   - Extract pagination tokens
   - Apply custom pricing
   ↓
10. BACKEND: Build response
    {
      parts: [...],
      facets: [...],
      pagination: {...}
    }
    ↓
11. FRONTEND: Render results
    - Display part cards
    - Update facet checkboxes
    - Update pagination controls
    - Show page indicator
```

---

## Key Features

### 1. **Full-Text Search**
- Multi-field search (part number, name, description, seller)
- Fuzzy matching (typo tolerance)
- Relevance-based ranking

### 2. **Autocomplete**
- Real-time suggestions as user types
- Edge n-gram tokenization
- Fast prefix matching

### 3. **Faceted Search**
- Dynamic filter options based on search results
- Count of matching items per facet value
- Multi-select filtering

### 4. **Cursor-Based Pagination**
- Fast pagination regardless of page depth
- Bidirectional navigation (next/previous)
- No "page jump" feature (by design for cursor pagination)

### 5. **Flexible Sorting**
- Relevance (search score)
- Price (ascending/descending)
- Date updated
- Part number (alphabetical)

### 6. **Dynamic Pricing**
- Per-customer pricing without database changes
- Forex conversion
- Markup calculation

### 7. **Real-Time Interactivity**
- Debounced search input
- Request cancellation (prevents race conditions)
- Smooth page transitions

---

## Performance Considerations

### 1. **Index Optimization**
- `dynamic: false` - Only index defined fields (faster indexing)
- Appropriate analyzers per field type
- Token type for exact-match filters

### 2. **Query Optimization**
- Use `filter` for non-scoring conditions (faster than `must`)
- Limit facet bucket counts (`numBuckets`)
- Project only needed fields in results

### 3. **Pagination Strategy**
- Cursor-based pagination (no skip() overhead)
- Fetch `limit + 1` to detect has_more efficiently

### 4. **Frontend Optimization**
- Request cancellation (abort previous searches)
- Debouncing (reduce API calls)
- Efficient DOM updates

---

## Common Pitfalls & Solutions

### 1. **Facet Fields Must Be "token" Type**
❌ **Problem**: Using `"type": "string"` for facet fields
```json
{"path": "status", "type": "string"}  // WRONG
```

✅ **Solution**: Use `"type": "token"` for exact matching
```json
{"path": "status", "type": "token"}  // CORRECT
```

### 2. **Autocomplete Requires Array Syntax**
❌ **Problem**: Using `multi` syntax
```json
{"name": {"type": "string", "multi": {"autocomplete": {...}}}}
```

✅ **Solution**: Use array syntax
```json
{"name": [
  {"type": "string"},
  {"type": "autocomplete", "tokenization": "edgeGram"}
]}
```

### 3. **Search Score Capture in $facet**
❌ **Problem**: Using `$meta` inside `$facet` doesn't work well

✅ **Solution**: We don't need explicit search scores for this demo; sorting by relevance (omitting sort spec) is sufficient

### 4. **Cursor Invalidation**
❌ **Problem**: Cursor becomes invalid when search parameters change

✅ **Solution**: Always call `performSearch(true)` when filters/sort changes to reset cursor

---

## Future Enhancements

### Possible Extensions

1. **Advanced Search**
   - Boolean operators (AND, OR, NOT)
   - Phrase search ("exact phrase")
   - Wildcard search

2. **Search Analytics**
   - Track popular searches
   - Log search performance
   - A/B test ranking algorithms

3. **Personalization**
   - User search history
   - Recommended parts
   - Saved searches

4. **Geospatial Search**
   - "Parts near me" functionality
   - Distance-based sorting

5. **Synonyms & Stopwords**
   - Configure Atlas Search analyzers
   - Custom synonym mappings

---

## Conclusion

This application demonstrates production-ready patterns for:
- ✅ MongoDB Atlas Search integration
- ✅ Integrated faceting with search
- ✅ Cursor-based pagination
- ✅ Relevance-based ranking
- ✅ Real-time autocomplete
- ✅ Dynamic filtering
- ✅ Custom business logic (pricing)

The architecture is scalable, maintainable, and demonstrates best practices for building search-driven applications with MongoDB Atlas Search.
