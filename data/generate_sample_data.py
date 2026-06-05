"""
Generate sample parts data for testing the Automotive Parts Catalog Search POC

This script generates realistic sample data matching the Automotive Parts Catalog schema
and inserts it directly into MongoDB.
"""
import json
import random
import os
from datetime import datetime, timedelta
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# Configuration
MONGODB_URI = "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/<db>"
DB_NAME = "PartsDistributor"
COLLECTION_NAME = "parts_search"

def generate_objectid():
    """Generate a fake ObjectId string"""
    import secrets
    return secrets.token_hex(12)


# Sample data pools - Expanded for 150k documents
PART_PREFIXES = [
    "MS", "NAS", "AN", "CSK", "HI", "AS", "BS", "DIN", "EN", "ISO",
    "SAE", "AMS", "BAC", "BMS", "NASM", "NAS", "VSM", "LHL", "CHR", "BRS"
]

PART_NUMBERS = [
    "MS24694s", "MS20470AD4-10", "MS20426AD3-5-5", "MS20470AD4-3.5",
    "NAS1149F0363P", "AN960-416", "MS21042-3", "NAS1351-3-16",
    "CSK100-8-10", "HI-LOK1234", "AS3582-6", "BS4620-12", "DIN933-M8",
    "EN2267-6H", "ISO7380-M6", "BAC15AB8", "BMS7-348", "NASM21251",
    "LHL-3456", "CHR-9821"
]

NAMES = [
    "Rivet", "CSK Solid Rivet", "Solid Rivet", "Universal Head Rivet",
    "Lock Nut", "Self-Locking Nut", "Hexagon Nut", "Castellated Nut",
    "Washer", "Flat Washer", "Spring Washer", "Lock Washer",
    "Screw", "Socket Head Screw", "Pan Head Screw", "Countersunk Screw",
    "Bolt", "Hex Head Bolt", "Close Tolerance Bolt", "Shear Bolt",
    "Pin", "Clevis Pin", "Cotter Pin", "Roll Pin",
    "Clamp", "Loop Clamp", "Cable Clamp", "Cushioned Clamp",
    "Fitting", "Tube Fitting", "Elbow Fitting", "Straight Fitting",
    "Bearing", "Ball Bearing", "Roller Bearing", "Thrust Bearing",
    "Seal", "O-Ring", "Oil Seal", "Gasket",
    "Bushing", "Plain Bushing", "Flanged Bushing", "Sleeve Bushing",
    "Spacer", "Standoff", "Shim", "Clip"
]

DESCRIPTIONS = [
    "High quality aerospace grade component",
    "Precision manufactured to aerospace standards",
    "Certified for aviation use",
    "Meets FAA requirements",
    "OEM specification",
    "EASA approved component",
    "Manufactured under AS9100 standards",
    "Traceable to original manufacturer",
    "Heat-treated for enhanced durability",
    "Corrosion-resistant coating applied",
    "Made from aircraft-grade aluminum",
    "Titanium alloy construction",
    "Stainless steel material",
    "Cadmium plated for protection",
    "Anodized finish for longevity",
    "Meets military specifications",
    "Compatible with Boeing aircraft",
    "Compatible with Airbus aircraft",
    "Designed for high-stress applications",
    "Tested for extreme temperatures",
    "Vibration-resistant design",
    "Low-maintenance component",
    "Long service life guaranteed",
    "Lightweight yet durable",
    "Precision-engineered tolerance"
]

CONDITIONS = ["New", "Used", "Overhauled", "Serviceable", "Repaired", "As Removed", "Inspected"]

LOCATIONS = [
    "KULMS", "BOMBAY", "SINGAPORE", "DUBAI", "TOKYO", "HONGKONG", "BANGKOK",
    "SYDNEY", "MELBOURNE", "AUCKLAND", "JAKARTA", "MANILA", "TAIPEI", "SEOUL",
    "BEIJING", "SHANGHAI", "DOHA", "ABU DHABI", "ISTANBUL", "LONDON"
]

AIRPORT_LOCATIONS = [
    "Kuala Lumpur International Airport (KUL) - Malaysia",
    "Chhatrapati Shivaji International Airport (BOM) - India",
    "Singapore Changi Airport (SIN) - Singapore",
    "Dubai International Airport (DXB) - UAE",
    "Hong Kong International Airport (HKG) - Hong Kong",
    "Suvarnabhumi Airport (BKK) - Thailand",
    "Sydney Airport (SYD) - Australia",
    "Narita International Airport (NRT) - Japan",
    "Incheon International Airport (ICN) - South Korea",
    "Beijing Capital International Airport (PEK) - China",
    "Shanghai Pudong International Airport (PVG) - China",
    "Hamad International Airport (DOH) - Qatar",
    "Abu Dhabi International Airport (AUH) - UAE",
    "Istanbul Airport (IST) - Turkey",
    "Heathrow Airport (LHR) - United Kingdom"
]

COMPANIES = [
    {"name": "Parts Distributor Engineering", "code": "PartsDistributor"},
    {"name": "Fastener Components Pvt. Ltd.", "code": "FCPL"},
    {"name": "Lion City Aero Engineering", "code": "LCAE"},
    {"name": "Gulf Aero Engineering", "code": "GAE-ENG"},
    {"name": "Skyline Aero Engineering", "code": "SKY-ENG"},
    {"name": "Cathay Pacific Engineering", "code": "CPAC"},
    {"name": "Thai Airways Engineering", "code": "THAI-ENG"},
    {"name": "Qantas Engineering", "code": "QF-ENG"},
    {"name": "Air New Zealand Engineering", "code": "ANZ-ENG"},
    {"name": "Garuda Maintenance Facility", "code": "GMF"},
    {"name": "Korean Air Engineering", "code": "KE-ENG"},
    {"name": "ANA Engineering", "code": "NH-ENG"},
    {"name": "China Eastern Engineering", "code": "MU-ENG"},
    {"name": "Qatar Airways Engineering", "code": "QR-ENG"},
    {"name": "Etihad Engineering", "code": "EY-ENG"}
]

MATERIAL_CLASSES = ["Consumable", "Rotable", "Expendable", "Repairable", "Serviceable"]

CATEGORIES = [
    "ATA 21 - Air Conditioning",
    "ATA 25 - Equipment/Furnishings",
    "ATA 27 - Flight Controls",
    "ATA 29 - Hydraulic Power",
    "ATA 32 - Landing Gear",
    "ATA 36 - Pneumatic",
    "ATA 49 - Auxiliary Power Unit",
    "ATA 52 - Doors",
    "ATA 53 - Fuselage",
    "ATA 54 - Nacelles/Pylons",
    "ATA 55 - Stabilizers",
    "ATA 56 - Windows",
    "ATA 57 - Wings",
    "ATA 71 - Power Plant",
    "ATA 79 - Oil System"
]

MANUFACTURERS = [
    "Boeing", "Airbus", "Spirit Aerosystems", "Collins Aerospace",
    "Honeywell", "Safran", "GE Aviation", "Rolls-Royce",
    "Pratt & Whitney", "Liebherr", "Goodrich", "Parker Aerospace",
    "Meggitt", "Eaton", "Zodiac Aerospace", "Thales",
    "Rockwell Collins", "UTC Aerospace", "Triumph Group", "AAR Corp"
]


def generate_part_number():
    """Generate realistic part number"""
    if random.random() < 0.3:
        # Use predefined part number
        return random.choice(PART_NUMBERS)
    else:
        # Generate random part number
        prefix = random.choice(PART_PREFIXES)
        numbers = ''.join([str(random.randint(0, 9)) for _ in range(5)])
        suffix = random.choice(['', 's', 'L', 'H', '-10', '-5'])
        return f"{prefix}{numbers}{suffix}"


def generate_batch_serial():
    """Generate batch or serial number"""
    if random.random() < 0.5:
        return None
    return ''.join([random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for _ in range(8)])


def generate_part():
    """Generate a single part document"""
    company = random.choice(COMPANIES)
    base_price = round(random.uniform(0.5, 500), 2)

    part = {
        # "_id" will be auto-generated by MongoDB if not provided, 
        # but keeping it here as string for JSON compatibility if needed.
        # For MongoDB insert, better to let it handle it or convert to ObjectId.
        # Since we are inserting, we can skip _id or ensure it's unique.
        # "partId" is custom.
        "partId": generate_objectid(),
        "partNo": generate_part_number(),
        "name": random.choice(NAMES),
        "description": random.choice(DESCRIPTIONS),
        "materialClass": random.choice(MATERIAL_CLASSES),
        "condition": random.choice(CONDITIONS),
        "location": random.choice(LOCATIONS),
        "airportLocation": random.choice(AIRPORT_LOCATIONS),
        "serialNo": generate_batch_serial(),
        "batchNo": generate_batch_serial(),
        "manufacturer": random.choice(MANUFACTURERS) if random.random() < 0.7 else None,

        # Stock and pricing
        "stock": random.randint(1, 10000),
        "price": base_price,
        "currency": "USD",

        # Seller info
        "companyName": company["name"],
        "companyCode": company["code"],

        # Metadata
        "status": random.choice(["Active", "Pending Update", "Active"]),  # More Active
        "updatedAt": datetime.now() - timedelta(days=random.randint(0, 365)),
        "isRealPart": random.choice([True, True, True, False]),  # More real parts

        # Additional fields
        "chapter": {
            "category": random.choice(CATEGORIES)
        }
    }

    return part


def generate_dataset(num_parts=1000):
    """Generate a dataset of parts"""
    parts = []

    # Generate some popular part numbers multiple times (for testing search relevance)
    popular_parts = ["MS24694s", "MS20470AD4-10", "MS20426AD3-5-5", "NAS1149F0363P", "AN960-416"]
    popular_count = min(200, num_parts // 100)  # Scale with dataset size
    
    for part_no in popular_parts:
        for _ in range(popular_count):  # Multiple variations of each popular part
            part = generate_part()
            part["partNo"] = part_no
            parts.append(part)

    # Generate remaining random parts
    remaining = num_parts - len(parts)
    print(f"Generating {remaining} random parts...")
    
    for i in range(remaining):
        if i > 0 and i % 10000 == 0:
            print(f"  Generated {i}/{remaining} parts...")
        parts.append(generate_part())

    return parts


def insert_into_mongodb(parts, batch_size=10000):
    """Insert parts into MongoDB using batched inserts"""
    print(f"Connecting to MongoDB...")
    print(f"URI: {MONGODB_URI.split('@')[1]}") # Print only the host part for security
    
    try:
        client = MongoClient(MONGODB_URI)
        # Force a connection check
        client.admin.command('ping')
        print("Connected to MongoDB successfully!")
        
        db = client[DB_NAME]
        collection = db[COLLECTION_NAME]
        
        print(f"Target Database: {DB_NAME}")
        print(f"Target Collection: {COLLECTION_NAME}")
        
        # Clear existing data (optional, commented out for safety)
        # print("⚠️  Clearing existing data...")
        # deleted = collection.delete_many({})
        # print(f"Deleted {deleted.deleted_count} existing documents.")
        
        total_parts = len(parts)
        print(f"Inserting {total_parts} documents in batches of {batch_size}...")
        
        total_inserted = 0
        # Insert in batches to avoid memory issues
        for i in range(0, total_parts, batch_size):
            batch = parts[i:i + batch_size]
            result = collection.insert_many(batch, ordered=False)
            total_inserted += len(result.inserted_ids)
            print(f"  Inserted batch {i//batch_size + 1}: {total_inserted}/{total_parts} documents")
        
        print(f"✅ Successfully inserted {total_inserted} documents.")
        
        # Verify count
        count = collection.count_documents({})
        print(f"Total documents in {COLLECTION_NAME}: {count}")
        
    except ConnectionFailure:
        print("❌ Could not connect to MongoDB. Check your internet connection and URI.")
    except OperationFailure as e:
        print(f"❌ Authentication failed or other operation error: {e}")
    except Exception as e:
        print(f"❌ An error occurred: {e}")
    finally:
        if 'client' in locals():
            client.close()


if __name__ == "__main__":
    print("="*60)
    print("Automotive Parts Catalog Search - Sample Data Generator")
    print("="*60)
    print("\nGenerating 150,000 sample parts data...")
    print("This may take a few minutes...\n")

    # Generate 150k parts
    parts = generate_dataset(150000)

    print(f"\nGenerated {len(parts)} parts successfully!")
    print("\nStarting MongoDB insertion...")
    
    # Insert into MongoDB
    insert_into_mongodb(parts, batch_size=10000)
    
    print("\n" + "="*60)
    print("Done! 150k documents generated and inserted.")
    print("="*60)
