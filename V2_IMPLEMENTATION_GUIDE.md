# V2 Implementation Guide - Offset Pagination with Runtime Pricing

## Overview

This folder contains **Version 2 (V2)** of the Automotive Parts Catalog Search application, which uses **offset-based pagination (skip/limit)** instead of cursor-based pagination.

## Why Skip/Limit Instead of searchSequenceToken?

**The fundamental reason:** The client needs to **calculate prices at runtime** (applying forex rates and markups) and **sort by these calculated prices**, not the database prices.

**Why searchSequenceToken doesn't work:**
1. `searchSequenceToken` generates cursor positions based on the **original sort order** from Atlas Search
2. When you calculate prices in the pipeline and then re-sort by `localMarkupPrice`, you've changed the document order
3. The cursor positions from the original sort are now **invalid** for the new sort order
4. Using `searchAfter` with a cursor from one sort order but applying a different sort causes incorrect pagination

**The solution:** Use **skip/limit** which works regardless of sort order changes, at the cost of slower performance for deep pages.

---

## Key Differences: V1 vs V2

| Feature | V1 (Cursor) | V2 (Skip/Limit - This Implementation) |
|---------|-------------|---------------------------------------|
| **Pagination** | Cursor-based (`searchSequenceToken`) | Offset-based (`skip` + `limit`) |
| **Price Calculation** | In Python after query | In MongoDB pipeline **before** sort |
| **Sort by Price** | Sorts by database price (inaccurate) | Sorts by displayed price (accurate) |
| **searchSequenceToken Compatible** | ✅ Yes (no re-sorting) | ❌ No (breaks after re-sort) |
| **Performance (Deep Pages)** | ✅ Constant time O(1) | ⚠️ Linear time O(n) |
| **Price Accuracy** | ❌ Wrong order | ✅ Correct order |
| **Use Case** | Relevance search, static sorting | Runtime pricing, dynamic sorting |
| **Backend Port** | 8000 | 8001 |
| **Frontend Port** | 8080 | 8081 |

---

## Architecture Changes

### Backend Changes

#### 1. **Runtime Price Calculation in Pipeline**

**Location:** `backend_v2/app/routers/parts_v2.py` (lines 325-341)

```python
# V2: Calculate custom pricing in the aggregation pipeline
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
            "$multiply": ["$price", {" $add": [1, markup]}]
        }
    }
})
```

**Why?** 
- Calculating prices **before** sorting ensures results are ordered by the actual prices users see
- Eliminates the discrepancy between sort order and displayed prices

#### 2. **Conditional Sorting Logic**

**Location:** `backend_v2/app/routers/parts_v2.py` (lines 343-358)

```python
# V2: Add $sort stage AFTER price calculation (for price sorting)
if sort_by == "price":
    pipeline.append({
        "$sort": {
            "localMarkupPrice": sort_direction,
            "_id": sort_direction  # Tiebreaker
        }
    })
elif sort_by != "relevance" and sort_in_search is None:
    pipeline.append({
        "$sort": {
            sort_by: sort_direction,
            "_id": sort_direction
        }
    })
```

**Logic:**
- **Price sorting:** Sort by `localMarkupPrice` (calculated field)
- **Relevance sorting:** No explicit sort (use natural Atlas Search score order)
- **Other fields:** Sort in $search stage or after

#### 3. **Offset Pagination**

**Location:** `backend_v2/app/routers/parts_v2.py` (lines 360-365)

```python
# V2: Offset pagination (skip + limit)
skip_count = (page - 1) * limit
pipeline.append({"$skip": skip_count})

pipeline.extend([
    {"$limit": limit + 1},  # Fetch one extra to detect has_more
])
```

**How it works:**
- `skip_count = (page - 1) * limit`
  - Page 1: skip 0
  - Page 2: skip 20
  - Page 3: skip 40
- Fetch `limit + 1` documents to detect if there are more pages

#### 4. **No Cursor Logic**

**Removed:**
- `searchAfter` / `searchBefore` parameters
- `paginationToken` extraction
- Cursor tracking and validation

**Added:**
- `page: int` parameter (default = 1)
- Simple `skip_count` calculation

---

### Frontend Changes

#### 1. **API Configuration**

**Location:** `frontend_v2/js/api.js` (line 6)

```javascript
const API_BASE_URL = 'http://localhost:8001';  // V2 uses port 8001
```

#### 2. **Page-Based Parameters**

**Location:** `frontend_v2/js/api.js` (lines 57-82)

```javascript
const {
    // ... other params
    page = 1,  // V2: page number instead of cursor
    // ... removed: cursor, direction
} = options;

const params = {
    // ... other params
    page,  // V2: page number
    // ... removed: cursor, direction
};
```

#### 3. **Simplified State Management**

**Location:** `frontend_v2/js/app.js` (lines 18-25)

```javascript
// V2: No cursor tracking, only page numbers
this.hasMore = false;
this.facets = [];
this.searchTimeout = null;

// V2: Track page number for offset pagination
this.currentPageNumber = 1;
```

**Removed:**
- `this.currentCursor`
- `this.nextCursor`
- `this.prevCursor`

#### 4. **Simple Page Navigation**

**Location:** `frontend_v2/js/app.js` (lines 442-459)

```javascript
goToNextPage() {
    if (this.hasMore) {
        this.currentPageNumber++;  // V2: Simple increment
        this.performSearch(false);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

goToPreviousPage() {
    if (this.currentPageNumber > 1) {
        this.currentPageNumber--;  // V2: Simple decrement
        this.performSearch(false);
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}
```

**Logic:**
- Next: Increment page number
- Previous: Decrement page number
- No cursor manipulation needed

---

## Running Both Versions Side-by-Side

You can run V1 and V2 simultaneously for comparison.

### Backend

**V2 (This Implementation):**
```bash
cd backend_v2
source venv/bin/activate
uvicorn app.main:app --reload --port 8001
# Or simply:
python app/main.py
```

### Frontend

**V2:**
```bash
cd frontend_v2
python3 -m http.server 8081
```

### Access URLs

- **Frontend:** http://localhost:8081
- **Backend API:** http://localhost:8001
- **API Docs:** http://localhost:8001/docs

---

## Performance Characteristics

### Offset Pagination Trade-offs

#### V1 (Cursor)

**Pros:**
- ✅ Constant time pagination (O(1) for any page)
- ✅ Consistent results even if data changes
- ✅ Efficient for deep pagination
- ✅ Works when sort order matches Atlas Search order

**Cons:**
- ❌ **Incompatible with runtime price calculation + sorting**
- ❌ searchSequenceToken breaks when documents are re-sorted after $search
- ❌ Cannot sort by calculated fields (localMarkupPrice)
- ❌ Price sorting shows wrong order (sorted by DB price, not displayed price)
- ❌ Cannot jump to arbitrary pages

#### V2 (Offset)

**Pros:**
- ✅ **Enables runtime price calculation + sorting** (the requirement)
- ✅ Sorts by actual displayed prices (localMarkupPrice)
- ✅ Price accuracy guaranteed
- ✅ Works with any sort order, including pipeline-calculated fields
- ✅ Can jump to any page (future enhancement)

**Cons:**
- ⚠️ Slower for deep pages (O(n) with skip count)
- ⚠️ Results may shift if data changes during pagination
- ⚠️ MongoDB must scan skipped documents
- ⚠️ Not suitable for very deep pagination (page 100+)

### Performance Expectations (150k documents)

| Page | Expected Load Time |
|------|-------------------|
| 1-10 | < 500ms |
| 11-50 | 500ms - 2s |
| 51-100 | 2s - 5s |
| 100+ | > 5s |

**Mitigation:**
- Set reasonable skip limits (e.g., max 1000 documents / 50 pages)
- Use facets to narrow results before deep pagination
- Consider caching for common queries

---

## Testing Checklist

### Functional Testing

- [ ] Page 1 loads correctly
- [ ] Next button navigates to page 2
- [ ] Previous button works on page 2+
- [ ] Previous button disabled on page 1
- [ ] Next button disabled on last page
- [ ] Sort by price shows results in correct order (lowest/highest)
- [ ] Sort by relevance works
- [ ] Filters reset pagination to page 1
- [ ] Search resets pagination to page 1
- [ ] Page indicator shows correct ranges

### Price Accuracy Testing

1. **Sort by Lowest Price (V1 vs V2)**
   - V1: May show higher prices first (sorted by database price)
   - V2: Should show lowest displayed prices first

2. **Change Forex Rate**
   - Results should re-sort correctly

3. **Change Markup**
   - Results should re-sort correctly

### Performance Testing

- [ ] Page 1: Load time < 500ms
- [ ] Page 10: Load time < 2s
- [ ] Page 50: Load time < 5s
- [ ] Facets still fast with filters applied

---

## When to Use V1 vs V2

### Use V1 (Cursor Pagination) When:

- Sorting by **database fields only** (no runtime calculations)
- Primary use case is relevance search
- Users rarely go beyond page 10
- Performance is critical for deep pagination
- Data consistency during pagination matters
- **You don't need to modify sort order after $search**

### Use V2 (Offset Pagination) When:

- **You MUST calculate fields at runtime and sort by them** (like runtime pricing)
- Price sorting accuracy is essential (client requirement)
- Users need to see results sorted by actual displayed prices, not DB prices
- Demonstrating dynamic pricing (forex, markups, customer-specific)
- Dataset size is reasonable (< 500k documents)
- Deep pagination is rare or limited
- **searchSequenceToken is incompatible with your sorting needs**

---

## Future Enhancements

### Hybrid Approach

Combine both pagination strategies:

```javascript
// Frontend decides which endpoint to use
const endpoint = (sortBy === 'price') 
  ? '/api/parts/search-v2'  // Offset for price sorting
  : '/api/parts/search';     // Cursor for everything else
```

### Skip Limit Guard

Prevent excessive skip counts:

```python
MAX_SKIP = 1000  # Limit to first 50 pages (20 per page)
skip_count = min((page - 1) * limit, MAX_SKIP)

if skip_count >= MAX_SKIP:
    return {"error": "Page limit reached. Please use filters to narrow results."}
```

### Caching Layer

Cache common queries in Redis:

```python
cache_key = f"search:{hash(search_params)}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)
```

---

## Conclusion

V2 demonstrates a production-ready approach to **sorting by calculated prices** at the cost of some pagination performance. For the PartsDistributor use case where price accuracy matters (forex conversion, markups, customer-specific pricing), V2 provides the correct user experience.

**Recommendation:**
- Use V2 for demos and POCs where price sorting accuracy is critical
- Use V1 for production if relevance search is the primary use case
- Consider hybrid approach for best of both worlds

---

## Documentation Links

- Main Architecture Doc
- [Atlas Search Documentation](https://www.mongodb.com/docs/atlas/atlas-search/)
- [Aggregation Pipeline Reference](https://www.mongodb.com/docs/manual/core/aggregation-pipeline/)
