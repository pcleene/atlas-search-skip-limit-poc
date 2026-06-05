<!-- Portfolio repository -->

> **Atlas Search Skip/Limit + Runtime Pricing** — portfolio demonstration.
> Offset pagination with dynamic price sorting on search results
>
> This is a sanitized public version of a real-world prototype. Client names,
> credentials, internal endpoints, and proprietary assets have been removed; all
> configuration is environment-driven (`.env.example`). Authored by
> [Paul Cleenewerck](https://github.com/pcleene).

---

# Automotive Parts Catalog Search V2 - Offset Pagination

A proof-of-concept implementation demonstrating MongoDB Atlas Search with **offset-based pagination (skip/limit)** and **runtime price calculation**. 

## Why Skip/Limit Instead of Cursor Pagination?

This implementation uses offset-based pagination (skip/limit) instead of cursor-based pagination (searchSequenceToken) because:

**The client requires runtime price calculation** (forex conversion + markup) to be performed **before sorting**. This allows sorting by the actual displayed prices, not database prices.

**searchSequenceToken is incompatible with this approach** because:
- It generates cursors based on the **original sort order** from Atlas Search
- Once prices are calculated and re-sorted in the pipeline, the original cursor positions become invalid
- You cannot use searchAfter/searchBefore with a sort order that differs from the Atlas Search sort

Therefore, **skip/limit is the only viable solution** for accurate price-based sorting with runtime calculations.

## 🎯 What This Is

This V2 implementation demonstrates MongoDB Atlas Search with offset pagination and runtime pricing:

- **Key Feature**: Sorts by **actual displayed prices** (after forex conversion & markup)
- **Approach**: Calculates prices in aggregation pipeline before sorting
- **Pagination**: Traditional page-based (skip/limit) instead of cursor-based
- **Performance**: 200-400ms search times (slightly slower than cursor-based for deep pages)

## 📁 Project Structure

```
PartsDistributor_v2_skip_limit/
├── README.md                           # This file
├── ATLAS_SEARCH_ARCHITECTURE.md        # Architecture documentation
├── mongodb_setup.md                    # MongoDB setup instructions
├── V2_IMPLEMENTATION_GUIDE.md          # V2-specific implementation details
├── backend_v2/                         # FastAPI backend (port 8001)
│   ├── app/
│   │   ├── main.py                     # Main FastAPI application
│   │   ├── config.py                   # Configuration management
│   │   ├── database.py                 # MongoDB connection
│   │   ├── models/                     # Pydantic models
│   │   ├── routers/
│   │   │   └── parts_v2.py             # V2 offset pagination implementation
│   │   └── utils/                      # Helper utilities
│   ├── requirements.txt                 # Python dependencies
│   ├── .env                            # Environment variables
│   └── README.md                       # Backend-specific docs
├── frontend_v2/                        # Frontend UI
│   ├── index.html                      # Main HTML page
│   ├── css/
│   │   └── styles.css                  # Styling (matches PartsDistributor design)
│   ├── js/
│   │   ├── api.js                      # API client (port 8001)
│   │   └── app.js                      # Main application logic
│   └── README.md                       # Frontend-specific docs
└── data/                               # Sample data and MongoDB scripts
```

## 🚀 Quick Start

### 1. Setup (5 minutes)
```bash
# Install backend dependencies
cd backend_v2
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your MongoDB Atlas URI
```

### 2. Generate and Import Data
```bash
# The generate_sample_data.py script generates 150k sample parts
# and directly inserts them into MongoDB
cd data
python generate_sample_data.py

# The script will:
# - Generate 150,000 realistic parts
# - Connect to MongoDB using the URI in the script
# - Insert data in batches of 10,000
# - Target database: Parts Distributor
# - Target collection: parts_search
```

**Note**: Edit `generate_sample_data.py` to update the MongoDB URI before running.

### 3. Create Atlas Search Index
Follow instructions in [mongodb_setup.md](mongodb_setup.md)

### 4. Start Backend (Port 8001)
```bash
cd backend_v2
python -m uvicorn app.main:app --reload --port 8001
# Or simply:
python app/main.py
```

### 5. Open Frontend (Port 8081)
```bash
cd frontend_v2
python -m http.server 8081
# Open http://localhost:8081
```

## 📊 Performance Characteristics

| Metric | V2 (Offset) | Notes |
|--------|-------------|-------|
| Page 1-10 | 200-500ms | Fast, includes price calculation in pipeline |
| Page 11-50 | 500ms-2s | Acceptable performance |
| Page 51+ | 2s-5s+ | Slower due to skip overhead |
| Price Sort Accuracy | ✅ 100% | Sorts by actual displayed prices |
| Runtime Price Calc | ✅ In Pipeline | Calculated before sorting |

## ✨ Key Features

### Backend (FastAPI + MongoDB Atlas Search)

- ✅ **Single Unified API** - One endpoint for search, filters, facets, pagination
- ✅ **Atlas Search** - Full-text search with relevance scoring
- ✅ **No Regex Queries** - All filters use indexed lookups (compound.filter)
- ✅ **Offset Pagination** - Traditional page-based navigation (skip/limit)
- ✅ **Runtime Price Calculation** - Prices calculated in aggregation pipeline
- ✅ **Accurate Price Sorting** - Sorts by displayed prices (forex + markup)
- ✅ **Integrated Faceting** - Facets calculated in same query
- ✅ **Page-Based Navigation** - Simple next/previous with page numbers

### Frontend (Vanilla JS)

- ✅ **Clean UI** - Matches PartsDistributor's design language
- ✅ **Autocomplete** - Real-time search suggestions
- ✅ **Live Search** - Debounced search as you type
- ✅ **Dynamic Filters** - Facet-based filtering
- ✅ **Instant Pagination** - Smooth page transitions
- ✅ **Responsive Design** - Works on all screen sizes

## 🎓 How It Works

### V2 Pipeline Flow
```
User Search → Atlas Search with compound.filter (100-150ms) ✅
→ Limit to 1000 docs (performance optimization) ✅
→ Calculate prices in pipeline ($addFields) (20-30ms) ✅
→ Sort by calculated price ($sort) (15-25ms) ✅
→ Skip to page position ($skip) (5-50ms depending on page) ✅
→ Limit results (10-15ms) ✅ → Response
TOTAL: 200-400ms for early pages ⚡
```

### Key Differences from Cursor Pagination
- **Price Calculation**: Done in MongoDB before sorting (not in Python)
- **Sorting**: By actual displayed prices, not database prices
- **Pagination**: Skip-based (slower for deep pages) vs cursor-based (constant time)

## 📖 Documentation

- **[ATLAS_SEARCH_ARCHITECTURE.md](ATLAS_SEARCH_ARCHITECTURE.md)** - Complete architecture documentation
- **[V2_IMPLEMENTATION_GUIDE.md](V2_IMPLEMENTATION_GUIDE.md)** - V2-specific implementation details
- **[mongodb_setup.md](mongodb_setup.md)** - MongoDB Atlas Search index setup

## 🔧 Technology Stack

**Backend:** FastAPI, Motor (async MongoDB), Pydantic, MongoDB Atlas Search
**Frontend:** Vanilla JavaScript, Modern CSS, Fetch API

## 🧪 Sample Data

Includes 1000 realistic sample parts with various part numbers (MS, NAS, AN, CSK, HI series), multiple sellers, conditions, locations, and pricing ($0.50 - $500).

## 🎯 Key Takeaways

1. **Runtime Pricing Enables Accurate Sorting** - Calculate prices before sorting in pipeline
2. **Offset Pagination Trade-offs** - Simpler but slower for deep pages than cursors
3. **Limit Early** - Process only top 1000 docs before expensive operations
4. **One Query is Better** - Combine search, filters, facets, and pricing
5. **compound.filter Beats $match** - Use it within $search stage for performance

---

**Price Accuracy**: 100% | **Page Navigation**: Simple | **Performance**: 200-500ms (early pages)
