# Automotive Parts Catalog Search - Backend

FastAPI backend with MongoDB Atlas Search integration.

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your settings
```

### 3. Run the Server
```bash
python -m uvicorn app.main:app --reload
```

Or:
```bash
python app/main.py
```

The API will be available at http://localhost:8001

## 📚 API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc

## 🔧 Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── database.py          # MongoDB connection
│   ├── models/              # Pydantic models
│   │   ├── __init__.py
│   │   └── parts.py         # Parts response models
│   ├── routers/             # API endpoints
│   │   ├── __init__.py
│   │   └── parts_v2.py      # Parts search endpoint (V2)
│   └── utils/               # Helper utilities
│       ├── __init__.py
│       ├── cursor.py        # Cursor encoding/decoding
│       ├── pricing.py       # Pricing calculations
│       └── search.py        # Search query builders
├── requirements.txt
├── .env.example
└── README.md
```

## 📍 API Endpoints

### GET /api/parts/search

Search for parts with filtering, faceting, and pagination.

**Query Parameters:**
- `search_text` (optional): Search query
- `seller` (optional, multi): Filter by seller codes
- `condition` (optional, multi): Filter by condition
- `location` (optional, multi): Filter by location
- `status` (default: ["Active", "Pending Update"]): Filter by status
- `min_price` (optional): Minimum price filter
- `max_price` (optional): Maximum price filter
- `sort_by` (default: "price"): Sort field
- `sort_order` (default: "asc"): Sort direction
- `limit` (default: 20, max: 100): Results per page
- `cursor` (optional): Pagination cursor
- `direction` (default: "next"): Pagination direction (next/prev)
- `forex_rate` (default: 4.2432): Currency conversion rate
- `markup` (default: 0.2): Markup percentage
- `user_currency` (default: "MYR"): User's currency
- `user_location` (default: "MY"): User's location
- `use_facets` (default: true): Include facets in response

**Example Request:**
```bash
curl "http://localhost:8001/api/parts/search?search_text=MS24694&limit=20"
```

**Example Response:**
```json
{
  "parts": [
    {
      "part_id": "...",
      "part_no": "MS24694s",
      "name": "RIVET",
      "price": 5.0,
      "local_price": 21.22,
      "markup_price": 6.0,
      "local_markup_price": 25.46,
      "currency": "USD",
      "local_currency": "MYR",
      "seller_company": "Parts Distributor Engineering",
      "location": "KULMS",
      "stock": 425,
      ...
    }
  ],
  "facets": [
    {
      "field": "seller",
      "buckets": [
        {"value": "PartsDistributor", "count": 150},
        {"value": "FCPL", "count": 89}
      ]
    }
  ],
  "pagination": {
    "limit": 20,
    "has_more": true,
    "next_cursor": "eyJz...",
    "prev_cursor": null,
    "total_count": 250,
    "current_page_start": 1,
    "current_page_end": 20
  },
  "search_metadata": {
    "search_text": "MS24694",
    "sort_by": "price",
    "sort_order": "asc"
  }
}
```

## ⚙️ Configuration

Edit `.env` file:

```env
# MongoDB
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>
MONGODB_DB_NAME=aerotrade
ATLAS_SEARCH_INDEX_NAME=parts_search_index

# API
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# Pricing
DEFAULT_FOREX_RATE=4.2432
DEFAULT_MARKUP=0.2
DEFAULT_USER_CURRENCY=MYR
DEFAULT_USER_LOCATION=MY
```

## 🧪 Testing

### Health Check
```bash
curl http://localhost:8001/health
```

### Simple Search
```bash
curl "http://localhost:8001/api/parts/search?limit=5"
```

### Search with Filters
```bash
curl "http://localhost:8001/api/parts/search?search_text=rivet&condition=New&limit=10"
```

### Pagination (V2 - Page-based)
```bash
# Get first page
curl "http://localhost:8001/api/parts/search?limit=20&page=1"

# Get second page
curl "http://localhost:8001/api/parts/search?limit=20&page=2"

# Get fifth page
curl "http://localhost:8001/api/parts/search?limit=20&page=5"
```

## 🔑 Key Features

- ✅ **MongoDB Atlas Search** - Full-text search with relevance scoring
- ✅ **No Regex Queries** - All filters use indexed lookups (compound.filter)
- ✅ **Offset Pagination** - Page-based navigation (skip/limit)
- ✅ **Runtime Price Calculation** - Prices calculated in aggregation pipeline
- ✅ **Accurate Price Sorting** - Sort by displayed prices (forex + markup)
- ✅ **Integrated Faceting** - Facets calculated in same query
- ✅ **Async/Await** - Non-blocking I/O with Motor
- ✅ **Type Safety** - Pydantic models for validation

## 📊 Performance (V2)

Expected response times:
- Page 1-10: 200-500ms (includes runtime price calculation)
- Page 11-50: 500ms-2s
- Page 51+: 2s-5s+ (skip overhead increases with page depth)
- Search with filters: 200-400ms

## 🐛 Troubleshooting

### MongoDB Connection Issues
```python
# Test connection
from motor.motor_asyncio import AsyncIOMotorClient

client = AsyncIOMotorClient("YOUR_MONGODB_URI")
db = client.aerotrade
print(await db.parts.count_documents({}))
```

### Atlas Search Index Missing
Check in MongoDB Atlas UI under Search tab that index `parts_search_index` exists and is active.

### CORS Errors
Add your frontend URL to `CORS_ORIGINS` in `.env`

## 📚 Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [MongoDB Motor Documentation](https://motor.readthedocs.io/)
- [MongoDB Atlas Search](https://www.mongodb.com/docs/atlas/atlas-search/)
