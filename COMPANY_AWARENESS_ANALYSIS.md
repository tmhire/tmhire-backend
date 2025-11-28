# Company Awareness Analysis & Migration Plan

## Current System Understanding

### Role Hierarchy

1. **Super Admin** (`role: "super_admin"`)
   - Manages company admins and companies
   - Can view all users across all companies
   - Does NOT directly manage company data
   - Access: `/company/all_users` returns all users with company info
   - Access: `/company/change_status` to approve/revoke companies

2. **Company Admin** (`role: "company_admin"`)
   - Manages their own company and its users
   - Automatically gets `sub_role: "editor"` and `account_status: "pen
   ding"` on onboarding
   - Can update company details via `/company/update`
   - Can view/manage users in their company via `/company/all_users`

3. **User** (`role: "user"`)
   - Belongs to a company via `company_id`
   - Has `sub_role: "viewer"` or `sub_role: "editor"`
   - `sub_role` access control is handled in frontend (backend doesn't enforce it)
   - `account_status: "pending"` initially, needs approval

### Authentication Flow (`app/routes/auth.py`)

1. **Signup**: Creates user with default `role: "user"`, `sub_role: "viewer"`, `account_status: "pending"`
2. **Onboarding** (`/auth/onboard`):
   - If `role: "company_admin"`: Creates new company, sets `sub_role: "editor"`, `account_status: "approved"`
   - If `role: "user"`: Joins existing company via `company_code`, sets `sub_role: "viewer"`, `account_status: "pending"`
3. **JWT Tokens**: Include `company_code` and `company_name` in token payload for company admins

### Company Management (`app/routes/company.py`)

- **Super Admin** can:
  - View all companies: `GET /company/`
  - Change company status: `PUT /company/change_status`
  - View all users across companies: `GET /company/all_users`

- **Company Admin** can:
  - Update their company: `PUT /company/update`
  - View users in their company: `GET /company/all_users` (filtered by company)

## Current Problem

### All Services Filter by `user_id` Instead of `company_id`

Currently, all services (plants, tms, pumps, team, projects, clients, schedules, calendar) filter data by `user_id`:

```python
# Current pattern (WRONG for company-aware system)
async def get_all_plants(user_id: str) -> List[PlantModel]:
    async for plant in plants.find({"user_id": ObjectId(user_id)}):
        ...
```

This means:
- Each user only sees their own data
- Company admins can't see data created by their company's users
- No company-wide visibility
- No tracking of who created what

## Required Changes

### 1. Change Filtering from `user_id` to `company_id`

**Services that need updating:**
- `app/services/plant_service.py`
- `app/services/tm_service.py`
- `app/services/pump_service.py`
- `app/services/team_service.py`
- `app/services/project_service.py`
- `app/services/client_service.py`
- `app/services/schedule_service.py`
- `app/services/schedule_calendar_service.py`
- `app/services/dashboard_service.py`

**Pattern Change:**
```python
# OLD (user-based)
async def get_all_plants(user_id: str) -> List[PlantModel]:
    async for plant in plants.find({"user_id": ObjectId(user_id)}):
        ...

# NEW (company-based)
async def get_all_plants(company_id: str, current_user: UserModel) -> List[PlantModel]:
    # Super admin can see all, company admin/users see their company
    query = {}
    if current_user.role != "super_admin":
        query["company_id"] = ObjectId(company_id)
    
    async for plant in plants.find(query):
        ...
```

### 2. Add `company_id` and `created_by` Fields to Models

**Current State:**
All models currently have `user_id: PyObjectId` as a required field:
- `PlantModel` - has `user_id: PyObjectId`
- `TransitMixerModel` - has `user_id: PyObjectId`
- `PumpModel` - has `user_id: PyObjectId`
- `TeamMemberModel` - has `user_id: PyObjectId`
- `ProjectModel` - has `user_id: PyObjectId`
- `ClientModel` - has `user_id: PyObjectId`
- `ScheduleModel` - has `user_id: PyObjectId`
- `DailySchedule` (schedule_calendar) - has `user_id: PyObjectId`

**Required Changes:**
1. Add `company_id: Optional[PyObjectId]` to all models (make it required for non-super-admin users)
2. Add `created_by: Optional[PyObjectId]` to track who created the record
3. Keep `user_id` for backward compatibility (or mark as deprecated)

**Model Updates Needed:**
```python
# Example: PlantModel
class PlantModel(BaseModel):
    id: Optional[PyObjectId] = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId  # Keep for backward compatibility
    company_id: Optional[PyObjectId] = None  # NEW - required for company users
    created_by: Optional[PyObjectId] = None  # NEW - track creator
    name: str
    # ... rest of fields
```

**Update Create Functions:**
```python
async def create_plant(plant: PlantCreate, current_user: UserModel) -> PlantModel:
    plant_data = plant.model_dump()
    plant_data["company_id"] = ObjectId(current_user.company_id)  # NEW
    plant_data["created_by"] = ObjectId(current_user.id)  # NEW
    plant_data["user_id"] = ObjectId(current_user.id)  # Keep for backward compatibility?
    ...
```

### 3. Update Service Function Signatures

**Change from:**
```python
async def get_all_plants(user_id: str) -> List[PlantModel]:
```

**To:**
```python
async def get_all_plants(company_id: str, current_user: UserModel) -> List[PlantModel]:
```

**Or better, just pass `current_user` and derive `company_id`:**
```python
async def get_all_plants(current_user: UserModel) -> List[PlantModel]:
    company_id = current_user.company_id
    if not company_id:
        return []  # User not part of a company
    
    query = {"company_id": ObjectId(company_id)}
    # Super admin can see all
    if current_user.role == "super_admin":
        query = {}
    
    async for plant in plants.find(query):
        ...
```

### 4. Update Route Handlers

**Change from:**
```python
@router.get("/")
async def read_plants(current_user: UserModel = Depends(get_current_user)):
    plants = await get_all_plants(str(current_user.id))
    ...
```

**To:**
```python
@router.get("/")
async def read_plants(current_user: UserModel = Depends(get_current_user)):
    plants = await get_all_plants(current_user)
    ...
```

### 5. Database Migration Considerations

#### Migration Strategy

**Step 1: Add New Fields (Non-Breaking)**
- Add `company_id` and `created_by` as optional fields to all models
- Deploy code that writes both `user_id` and `company_id` on create
- Keep reading by `user_id` for now (backward compatible)

**Step 2: Data Migration Script**
```python
# Migration script to populate company_id from user's company_id
async def migrate_data_to_company_aware():
    from app.db.mongodb import users, plants, transit_mixers, pumps, team, projects, clients, schedules
    
    collections = [plants, transit_mixers, pumps, team, projects, clients, schedules]
    
    for collection in collections:
        async for doc in collection.find({"company_id": {"$exists": False}}):
            user_id = doc.get("user_id")
            if user_id:
                user = await users.find_one({"_id": user_id})
                if user and user.get("company_id"):
                    await collection.update_one(
                        {"_id": doc["_id"]},
                        {"$set": {"company_id": user["company_id"]}}
                    )
```

**Step 3: Switch Filtering to `company_id`**
- Update all service functions to filter by `company_id` instead of `user_id`
- Keep `user_id` field for audit trail but don't use for filtering
- Super admin queries don't filter by company

**Step 4: Make `company_id` Required (Optional)**
- After migration, make `company_id` required for new records
- Or keep it optional to support super admin creating records without company

## Implementation Priority

### Phase 1: Models & Database Schema
1. Add `company_id` and `created_by` to all models
2. Create migration script to update existing records

### Phase 2: Service Layer
1. Update all service functions to use `company_id` filtering
2. Add `created_by` tracking in create operations
3. Handle super admin access (can see all companies)

### Phase 3: Route Layer
1. Update route handlers to pass `current_user` instead of `user_id`
2. Ensure proper authorization checks

### Phase 4: Testing & Validation
1. Test super admin can see all data
2. Test company admin can see company data
3. Test users can see company data
4. Verify `created_by` tracking works

## Key Considerations

1. **Super Admin Access**: Should super admins see all data across all companies? (Probably yes for management)
2. **Backward Compatibility**: Keep `user_id` field for now or remove immediately?
3. **Authorization**: Add middleware to ensure users can only access their company's data (unless super admin)
4. **Performance**: Index `company_id` in MongoDB for efficient queries
5. **Audit Trail**: `created_by` enables tracking who created/modified what

## Example: Complete Service Function Update

```python
# app/services/plant_service.py

async def get_all_plants(current_user: UserModel) -> List[PlantModel]:
    """Get all plants for the current user's company"""
    query = {}
    
    # Super admin can see all plants
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []  # User not part of a company
        query["company_id"] = ObjectId(current_user.company_id)
    
    plant_list = []
    async for plant in plants.find(query).sort("created_at", DESCENDING):
        plant_list.append(PlantModel(**plant))
    return plant_list

async def create_plant(plant: PlantCreate, current_user: UserModel) -> PlantModel:
    """Create a new plant"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    plant_data = plant.model_dump()
    plant_data["company_id"] = ObjectId(current_user.company_id)
    plant_data["created_by"] = ObjectId(current_user.id)
    plant_data["user_id"] = ObjectId(current_user.id)  # Keep for compatibility
    plant_data["created_at"] = datetime.utcnow()
    plant_data["last_updated"] = datetime.utcnow()
    
    result = await plants.insert_one(plant_data)
    new_plant = await plants.find_one({"_id": result.inserted_id})
    return PlantModel(**new_plant)
```

## Quick Reference: What Needs to Change

### Files to Modify

**Models (Add `company_id` and `created_by`):**
- `app/models/plant.py`
- `app/models/transit_mixer.py`
- `app/models/pump.py`
- `app/models/team.py`
- `app/models/project.py`
- `app/models/client.py`
- `app/models/schedule.py`
- `app/models/schedule_calendar.py`

**Services (Change filtering from `user_id` to `company_id`):**
- `app/services/plant_service.py`
- `app/services/tm_service.py`
- `app/services/pump_service.py`
- `app/services/team_service.py`
- `app/services/project_service.py`
- `app/services/client_service.py`
- `app/services/schedule_service.py`
- `app/services/schedule_calendar_service.py`
- `app/services/dashboard_service.py`

**Routes (Update to pass `current_user` instead of `user_id`):**
- `app/routes/plants.py`
- `app/routes/tms.py`
- `app/routes/pumps.py`
- `app/routes/team_members.py`
- `app/routes/projects.py`
- `app/routes/clients.py`
- `app/routes/schedules.py`
- `app/routes/schedule_calendar.py`
- `app/routes/dashboard.py`

### Key Patterns

**OLD Pattern:**
```python
# Service
async def get_all_plants(user_id: str) -> List[PlantModel]:
    async for plant in plants.find({"user_id": ObjectId(user_id)}):
        ...

# Route
@router.get("/")
async def read_plants(current_user: UserModel = Depends(get_current_user)):
    plants = await get_all_plants(str(current_user.id))
```

**NEW Pattern:**
```python
# Service
async def get_all_plants(current_user: UserModel) -> List[PlantModel]:
    query = {}
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    async for plant in plants.find(query):
        ...

# Route
@router.get("/")
async def read_plants(current_user: UserModel = Depends(get_current_user)):
    plants = await get_all_plants(current_user)
```

### Authorization Rules

1. **Super Admin**: Can see all data across all companies (no `company_id` filter)
2. **Company Admin**: Can see all data in their company (`company_id` = their company)
3. **User (Editor/Viewer)**: Can see all data in their company (`company_id` = their company)
4. **User without company**: Cannot see any data (return empty list)

### Database Indexes to Add

```javascript
// MongoDB indexes for performance
db.plants.createIndex({ "company_id": 1 })
db.transit_mixers.createIndex({ "company_id": 1 })
db.pumps.createIndex({ "company_id": 1 })
db.team.createIndex({ "company_id": 1 })
db.projects.createIndex({ "company_id": 1 })
db.clients.createIndex({ "company_id": 1 })
db.schedules.createIndex({ "company_id": 1 })
db.schedule_calendar.createIndex({ "company_id": 1 })
```

