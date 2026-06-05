
# MongoDB Setup Commands for Automotive Parts Catalog Search V2

## 1. Create Database and Collection
```javascript
use PartsDistributor
db.createCollection("parts_search")
```

## 2. Generate and Import Sample Data

This project uses `generate_sample_data.py` which **directly inserts** data into MongoDB (no intermediate JSON file needed).

```bash
cd data

# Edit the script to set your MongoDB URI
# MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>"

# Run the generator (creates 150k documents)
python generate_sample_data.py
```

The script will:
- Generate 150,000 realistic sample parts
- Connect directly to MongoDB
- Insert in batches of 10,000 documents
- Show progress during insertion
- Target: `PartsDistributor.parts_search` collection

## 3. Create Atlas Search Index
```javascript
// In MongoDB Atlas UI:
// 1. Go to Search tab
// 2. Click "Create Search Index"
// 3. Use JSON Editor and paste:

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
        "analyzer": "lucene.standard"
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

## 4. Create Traditional Indexes (Optional - for performance)
```javascript
// Compound indexes for sorting (V2 primarily uses Atlas Search)
db.parts_search.createIndex({ "price": 1, "_id": 1 })
db.parts_search.createIndex({ "updatedAt": -1, "_id": -1 })

// Single field indexes
db.parts_search.createIndex({ "partNo": 1 })
db.parts_search.createIndex({ "companyCode": 1 })
db.parts_search.createIndex({ "condition": 1 })
db.parts_search.createIndex({ "location": 1 })
db.parts_search.createIndex({ "status": 1 })
```

**Note**: For V2, the Atlas Search index handles most queries. Traditional indexes are optional and mainly useful for non-search queries.

## 5. Verify Data
```javascript
// Check total count
db.parts_search.countDocuments()

// Sample query
db.parts_search.find().limit(5)

// Check a specific part
db.parts_search.findOne({ "partNo": "MS24694" })
```
