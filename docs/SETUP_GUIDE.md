# Automotive Parts Catalog Search POC - Setup Guide

## 📋 Prerequisites

- Python 3.8+
- MongoDB Atlas account (free tier works)
- Node.js (optional, for running a local web server)
- Git

## 🚀 Quick Start (5 Minutes)

### Step 1: Clone and Navigate
```bash
cd /path/to/PartsDistributor
```

### Step 2: Setup Backend

#### 2.1 Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

#### 2.2 Configure Environment
```bash
cp .env.example .env
# Edit .env with your MongoDB connection string
```

Your `.env` should look like:
```env
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>
MONGODB_DB_NAME=PartsDistributor
ATLAS_SEARCH_INDEX_NAME=parts_search_index
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

### Step 3: Setup MongoDB

#### 3.1 Create Database
1. Log into MongoDB Atlas
2. Create a new database called `PartsDistributor`
3. Create a collection called `parts_search`

#### 3.2 Import Sample Data
```bash
cd ../data

# Run the python script to generate and insert data directly
# Ensure you have set up your python environment (see Step 2)
python generate_sample_data.py
```

#### 3.3 Create Atlas Search Index

1. Go to MongoDB Atlas UI
2. Navigate to your cluster
3. Click on "Search" tab
4. Click "Create Search Index"
5. Choose "JSON Editor"
6. Name it: `parts_search_index`
7. Collection: `parts_search`
8. Paste this configuration:

```json
{
  "mappings": {
    "dynamic": false,
    "fields": {
      "partNo": {
        "type": "string",
        "analyzer": "lucene.standard",
        "multi": {
          "autocomplete": {
            "type": "autocomplete",
            "tokenization": "edgeGram",
            "minGrams": 2,
            "maxGrams": 15
          }
        }
      },
      "name": {
        "type": "string",
        "analyzer": "lucene.standard",
        "multi": {
          "autocomplete": {
            "type": "autocomplete",
            "tokenization": "edgeGram",
            "minGrams": 2,
            "maxGrams": 15
          }
        }
      },
      "description": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "serialNo": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "batchNo": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "companyName": {
        "type": "string",
        "analyzer": "lucene.standard"
      },
      "companyCode": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "location": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "airportLocation": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "condition": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "materialClass": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "chapter": {
        "type": "document",
        "fields": {
          "category": {
            "type": "string",
            "analyzer": "lucene.keyword"
          }
        }
      },
      "status": {
        "type": "string",
        "analyzer": "lucene.keyword"
      },
      "isRealPart": {
        "type": "boolean"
      },
      "price": {
        "type": "number"
      },
      "updatedAt": {
        "type": "date"
      },
      "_id": {
        "type": "objectId"
      }
    }
  }
}
```

9. Click "Create Search Index"
10. Wait for index to build (5-15 minutes)

#### 3.4 Create Traditional Indexes

In MongoDB Shell or Compass, run:

```javascript
use PartsDistributor

// Compound indexes for cursor pagination
db.parts_search.createIndex({ "price": 1, "_id": 1 })
db.parts_search.createIndex({ "updatedAt": -1, "_id": -1 })

// Single field indexes
db.parts_search.createIndex({ "partNo": 1 })
db.parts_search.createIndex({ "companyCode": 1 })
db.parts_search.createIndex({ "condition": 1 })
db.parts_search.createIndex({ "location": 1 })
db.parts_search.createIndex({ "status": 1 })
```

### Step 4: Start Backend Server

```bash
cd ../backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Connected to MongoDB: aerotrade
```

Test the API:
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy"}
```

### Step 5: Open Frontend

#### Option 1: Using Python's HTTP Server
```bash
cd ../frontend
python -m http.server 8080
```

Then open: http://localhost:8080

#### Option 2: Using Node.js
```bash
cd ../frontend
npx http-server -p 8080
```

Then open: http://localhost:8080

#### Option 3: Direct File
Just open `frontend/index.html` in your browser.

**Note:** If you use the direct file method, you'll need to update the API URL in `frontend/js/api.js` to allow CORS.

---

## ✅ Verification

### 1. Check Backend Health
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy"}
```

### 2. Test Search Endpoint
```bash
curl "http://localhost:8000/api/parts/search?limit=5&search_text=MS24694"
```

You should get JSON response with parts, facets, and pagination.

### 3. Check Frontend
1. Open http://localhost:8080
2. You should see the AeroTrade interface
3. Type "ms" in the search bar
4. You should see autocomplete suggestions
5. Click on a suggestion or press Enter
6. Results should load

---

## 🎯 Quick Test Searches

Try these searches to test the system:

1. **Initial Load** (no search text):
   - Just open the page
   - Should show parts sorted by relevance to your location

2. **Part Number Search**:
   - Search: `MS24694`
   - Should show exact matches first

3. **Partial Search**:
   - Search: `rivet`
   - Should show all parts with "rivet" in name or description

4. **Filters**:
   - Click "Filter" button
   - Select "New" condition
   - Select "KULMS" location
   - Click "Apply Filters"
   - Should show filtered results

5. **Pagination**:
   - Scroll to bottom
   - Click "Next" button
   - Should load next page instantly

---

## 🔧 Troubleshooting

### Backend won't start

**Error: `ModuleNotFoundError: No module named 'fastapi'`**
```bash
pip install -r requirements.txt
```

**Error: `Connection refused` to MongoDB**
- Check your MongoDB URI in `.env`
- Make sure your IP is whitelisted in MongoDB Atlas
- Test connection with MongoDB Compass

**Error: `Atlas Search index not found`**
- Go to MongoDB Atlas UI
- Check Search tab
- Verify index named `parts_search_index` exists
- Wait for index to finish building (check status)

### Frontend issues

**No results showing**
- Open browser console (F12)
- Check for CORS errors
- Make sure backend is running on port 8000
- Check API_BASE_URL in `frontend/js/api.js`

**Autocomplete not working**
- Type at least 2 characters
- Wait 300ms for debounce
- Check browser console for errors

**Filters not working**
- Make sure facets are being returned from API
- Check browser console for errors
- Verify Atlas Search index includes facet fields

### Performance issues

**Search is slow (>1 second)**
- Check if Atlas Search index is built
- Verify traditional indexes are created
- Check MongoDB Atlas metrics
- Consider upgrading Atlas tier

**No search results**
- Verify data is imported: `db.parts.countDocuments()`
- Check search index status in Atlas UI
- Try initial load (no search text) first

---

## 📚 Next Steps

1. **Read the Documentation**:
   - [Problem Summary](./PROBLEM_SUMMARY.md) - Understand what we're solving
   - Implementation Guide - Deep dive into the code

2. **Customize**:
   - Modify search boost values in `backend/app/routers/parts_v2.py`
   - Adjust pricing markup in `.env`
   - Customize frontend styles in `frontend/css/styles.css`

3. **Deploy**:
   - Backend: Deploy to your preferred platform (AWS, Heroku, Railway)
   - Frontend: Deploy to Netlify, Vercel, or S3
   - Update CORS settings in `.env`

---

## 🆘 Getting Help

If you encounter issues:

1. Check the troubleshooting section above
2. Review the code comments
3. Check MongoDB Atlas logs
4. Check browser console for frontend errors
5. Check backend logs for API errors

---

## 🎉 Success!

If you can:
- ✅ See the frontend interface
- ✅ Type and see autocomplete
- ✅ Search and get results
- ✅ Apply filters
- ✅ Navigate pages

Then you're all set! The POC is working correctly.

---

**Time to complete setup: ~15-20 minutes** (mostly waiting for Atlas Search index)
