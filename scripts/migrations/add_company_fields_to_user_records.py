"""
Migration script to add company_id, created_by, created_at, and last_updated fields
to all records belonging to a specific user.

This script:
1. Finds all records in specified collections that belong to user 6819c935f7cf16f14379614a
2. Adds company_id, created_by, created_at, and last_updated fields
3. Updates records in: transit_mixers, clients, plants, projects, pumps, schedules, team

Run this script to populate metadata fields for existing user records.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.mongodb import (
    transit_mixers, clients, plants, projects, pumps, schedules, team
)
from bson import ObjectId


# Configuration
USER_ID = "68df653d9e2835024a1f94a3"
COMPANY_ID = "692936b87bd3888e945c38a6"
CREATED_BY = "6929379e7bd3888e945c38a8"
CREATED_AT = "2025-11-28T05:49:56.283+00:00"
LAST_UPDATED = "2025-11-28T05:49:56.283+00:00"


async def migrate_collection(collection_name, collection):
    """Migrate a single collection by adding fields to user's records"""
    print(f"\n{'='*60}")
    print(f"Migrating {collection_name}...")
    print(f"{'='*60}")
    
    updated_count = 0
    skipped_count = 0
    error_count = 0
    
    # Convert user_id to ObjectId
    user_object_id = ObjectId(USER_ID)
    
    # Parse datetime strings - handle timezone format
    def parse_datetime(dt_str: str) -> datetime:
        """Parse datetime string with timezone support"""
        try:
            # Try fromisoformat first (works with +00:00 format in Python 3.7+)
            return datetime.fromisoformat(dt_str)
        except ValueError:
            try:
                # If format has Z instead of +00:00, replace it
                dt_str_normalized = dt_str.replace('Z', '+00:00')
                return datetime.fromisoformat(dt_str_normalized)
            except ValueError:
                try:
                    # Fallback to strptime with timezone
                    return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S.%f%z")
                except ValueError:
                    try:
                        # Try without microseconds
                        return datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S%z")
                    except ValueError:
                        # Last resort: parse without timezone
                        return datetime.strptime(dt_str.split('+')[0].split('Z')[0], "%Y-%m-%dT%H:%M:%S.%f")
    
    created_at_dt = parse_datetime(CREATED_AT)
    last_updated_dt = parse_datetime(LAST_UPDATED)
    
    # Convert IDs to ObjectId
    company_object_id = ObjectId(COMPANY_ID)
    created_by_object_id = ObjectId(CREATED_BY)
    
    # Find all records for this user
    # Query by user_id (all models have this field for backward compatibility)
    query = {
        "$or": [
            {"user_id": user_object_id},
            {"user_id": USER_ID},  # Also try string format
        ]
    }
    
    async for doc in collection.find(query):
        try:
            # Check if fields already exist and match (skip if already set correctly)
            doc_company_id = doc.get("company_id")
            doc_created_by = doc.get("created_by")
            
            # Convert to ObjectId for comparison if they exist
            if doc_company_id:
                if isinstance(doc_company_id, str):
                    doc_company_id = ObjectId(doc_company_id)
            if doc_created_by:
                if isinstance(doc_created_by, str):
                    doc_created_by = ObjectId(doc_created_by)
            
            # Skip if already has the correct values
            if (doc_company_id == company_object_id and 
                doc_created_by == created_by_object_id):
                skipped_count += 1
                continue
            
            # Prepare update data
            update_data = {
                "company_id": company_object_id,
                "created_by": created_by_object_id,
                "created_at": created_at_dt,
                "last_updated": last_updated_dt
            }
            
            # Update the document
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": update_data}
            )
            
            updated_count += 1
            if updated_count % 100 == 0:
                print(f"  ✅ Updated {updated_count} records...")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error updating {doc.get('_id')}: {str(e)}")
    
    print(f"\n📊 {collection_name} Migration Summary:")
    print(f"   ✅ Updated: {updated_count}")
    print(f"   ⚠️  Skipped: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    
    return updated_count, skipped_count, error_count


async def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("ADD COMPANY FIELDS TO USER RECORDS MIGRATION")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    print(f"\nTarget User ID: {USER_ID}")
    print(f"Company ID: {COMPANY_ID}")
    print(f"Created By: {CREATED_BY}")
    print(f"Created At: {CREATED_AT}")
    print(f"Last Updated: {LAST_UPDATED}")
    print("\nThis script will:")
    print("1. Find all records belonging to the specified user")
    print("2. Add company_id, created_by, created_at, and last_updated fields")
    print("3. Update records in: transit_mixers, clients, plants, projects, pumps, schedules, team")
    print("\n" + "="*60)
    
    # Collections to migrate
    collections = [
        ("transit_mixers", transit_mixers),
        ("clients", clients),
        ("plants", plants),
        ("projects", projects),
        ("pumps", pumps),
        ("schedules", schedules),
        ("team", team),
    ]
    
    total_updated = 0
    total_skipped = 0
    total_errors = 0
    
    for collection_name, collection in collections:
        updated, skipped, errors = await migrate_collection(collection_name, collection)
        total_updated += updated
        total_skipped += skipped
        total_errors += errors
    
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    print(f"Finished at: {datetime.now()}")
    print(f"\n📊 Overall Summary:")
    print(f"   ✅ Total Updated: {total_updated}")
    print(f"   ⚠️  Total Skipped: {total_skipped}")
    print(f"   ❌ Total Errors: {total_errors}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

