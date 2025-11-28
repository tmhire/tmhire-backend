"""
Migration script to populate company_id and created_by fields from existing user_id data.

This script:
1. Reads all existing records that don't have company_id
2. Looks up the user's company_id from the users collection
3. Populates company_id and created_by fields
4. Keeps user_id for backward compatibility

Run this script after deploying the new code that supports company_id.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.db.mongodb import (
    users, plants, transit_mixers, pumps, team, projects, clients, schedules, schedule_calendar
)
from bson import ObjectId
from datetime import datetime


async def migrate_collection(collection_name, collection):
    """Migrate a single collection to be company-aware"""
    print(f"\n{'='*60}")
    print(f"Migrating {collection_name}...")
    print(f"{'='*60}")
    
    migrated_count = 0
    skipped_count = 0
    error_count = 0
    
    async for doc in collection.find({"company_id": {"$exists": False}}):
        try:
            user_id = doc.get("user_id")
            if not user_id:
                skipped_count += 1
                print(f"  ⚠️  Skipping {doc.get('_id')} - no user_id")
                continue
            
            # Convert to ObjectId if it's a string
            if isinstance(user_id, str):
                user_id = ObjectId(user_id)
            
            # Look up the user
            user = await users.find_one({"_id": user_id})
            if not user:
                skipped_count += 1
                print(f"  ⚠️  Skipping {doc.get('_id')} - user not found: {user_id}")
                continue
            
            # Get company_id from user
            user_company_id = user.get("company_id")
            if not user_company_id:
                skipped_count += 1
                print(f"  ⚠️  Skipping {doc.get('_id')} - user has no company_id")
                continue
            
            # Convert to ObjectId if needed
            if isinstance(user_company_id, str):
                user_company_id = ObjectId(user_company_id)
            
            # Update the document
            update_data = {
                "company_id": user_company_id,
                "created_by": user_id  # Set created_by to the user_id
            }
            
            await collection.update_one(
                {"_id": doc["_id"]},
                {"$set": update_data}
            )
            
            migrated_count += 1
            if migrated_count % 100 == 0:
                print(f"  ✅ Migrated {migrated_count} records...")
                
        except Exception as e:
            error_count += 1
            print(f"  ❌ Error migrating {doc.get('_id')}: {str(e)}")
    
    print(f"\n📊 {collection_name} Migration Summary:")
    print(f"   ✅ Migrated: {migrated_count}")
    print(f"   ⚠️  Skipped: {skipped_count}")
    print(f"   ❌ Errors: {error_count}")
    
    return migrated_count, skipped_count, error_count


async def main():
    """Main migration function"""
    print("\n" + "="*60)
    print("COMPANY AWARENESS MIGRATION")
    print("="*60)
    print(f"Started at: {datetime.now()}")
    print("\nThis script will:")
    print("1. Find all records without company_id")
    print("2. Look up the user's company_id")
    print("3. Populate company_id and created_by fields")
    print("4. Keep user_id for backward compatibility")
    print("\n" + "="*60)
    
    # Collections to migrate
    collections = [
        ("plants", plants),
        ("transit_mixers", transit_mixers),
        ("pumps", pumps),
        ("team", team),
        ("projects", projects),
        ("clients", clients),
        ("schedules", schedules),
        ("schedule_calendar", schedule_calendar),
    ]
    
    total_migrated = 0
    total_skipped = 0
    total_errors = 0
    
    for collection_name, collection in collections:
        migrated, skipped, errors = await migrate_collection(collection_name, collection)
        total_migrated += migrated
        total_skipped += skipped
        total_errors += errors
    
    print("\n" + "="*60)
    print("MIGRATION COMPLETE")
    print("="*60)
    print(f"Finished at: {datetime.now()}")
    print(f"\n📊 Overall Summary:")
    print(f"   ✅ Total Migrated: {total_migrated}")
    print(f"   ⚠️  Total Skipped: {total_skipped}")
    print(f"   ❌ Total Errors: {total_errors}")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())


