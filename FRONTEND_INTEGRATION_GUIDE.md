# Frontend Integration Guide: Company Awareness Migration

## Overview
The backend has been migrated from **user-based** to **company-based** data access. All APIs now filter data by `company_id` instead of `user_id`, enabling company-wide data sharing while maintaining proper access control.

---

## 🔄 Backend Changes Summary

### 1. **Data Model Changes**
All models now include:
- `company_id`: Links records to a company
- `created_by`: Tracks which user created the record
- `user_id`: Kept for backward compatibility (deprecated)

**Affected Models:**
- Plants, Transit Mixers, Pumps, Team Members, Projects, Clients, Schedules, Schedule Calendar

### 2. **API Behavior Changes**

#### **Before (User-Based):**
- Each user only saw their own data
- Company admins couldn't see data created by their users
- No company-wide visibility

#### **After (Company-Based):**
- **Company Admin**: Sees ALL data in their company
- **Users (Editor/Viewer)**: See ALL data in their company
- **Super Admin**: Sees ALL data across ALL companies
- All users in a company share the same data pool

### 3. **Access Control Rules**

| Role | Access Level |
|------|-------------|
| **Super Admin** | Can see/manage all data across all companies |
| **Company Admin** | Can see/manage all data in their company |
| **User (Editor)** | Can see all data in their company, can create/edit (frontend controlled) |
| **User (Viewer)** | Can see all data in their company, read-only (frontend controlled) |

---

## 📋 Frontend Changes Required

### **Critical Changes (Must Implement)**

#### 1. **User Context & Company Information**

**What to Add:**
- Display user's company name/ID in user profile/settings
- Show company membership status
- Display user's role (super_admin, company_admin, user) and sub_role (editor, viewer)

**API Endpoints to Use:**
- `GET /auth/me` - Returns current user with `company_id`, `company_name`, `role`, `sub_role`
- `GET /company/all_users` - For company admins to see company users

**Frontend Implementation:**
```typescript
// User context should include:
interface UserContext {
  id: string;
  email: string;
  role: 'super_admin' | 'company_admin' | 'user';
  sub_role?: 'editor' | 'viewer';
  company_id?: string;
  company_name?: string;
  account_status: 'pending' | 'approved';
}
```

---

#### 2. **Data Visibility Changes**

**Before:**
- Each user saw only their own plants, TMs, pumps, etc.

**After:**
- All users in a company see ALL company data
- Super admin sees ALL data from ALL companies

**Frontend Impact:**
- ✅ **No API changes needed** - Same endpoints, different data returned
- ✅ Lists will automatically show company-wide data
- ⚠️ **UI Changes Needed:**
  - Update labels: "My Plants" → "Company Plants"
  - Update empty states: "Create your first plant" → "No plants in your company yet"
  - Show creator info: Display `created_by` user name in lists/details

**Example UI Updates:**
```typescript
// Before
<h1>My Plants</h1>
<p>You haven't created any plants yet</p>

// After
<h1>Company Plants</h1>
<p>No plants in your company yet</p>
// Show creator badge
{plant.created_by_name && (
  <Badge>Created by {plant.created_by_name}</Badge>
)}
```

---

#### 3. **Create/Edit Permissions**

**Backend Behavior:**
- All users in a company can create/edit (backend doesn't enforce sub_role)
- Frontend must enforce `sub_role: "viewer"` restrictions

**Frontend Implementation:**
```typescript
// Check permissions before showing create/edit buttons
const canEdit = currentUser.role === 'super_admin' || 
                currentUser.role === 'company_admin' ||
                (currentUser.role === 'user' && currentUser.sub_role === 'editor');

// Hide create/edit buttons for viewers
{canEdit && (
  <Button onClick={handleCreate}>Create Plant</Button>
)}
```

**Pages to Update:**
- Plants list/create/edit
- Transit Mixers list/create/edit
- Pumps list/create/edit
- Team Members list/create/edit
- Projects list/create/edit
- Clients list/create/edit
- Schedules create/edit

---

#### 4. **Creator Tracking Display**

**What to Add:**
- Show who created each record
- Display `created_by` user name in:
  - List views (optional column)
  - Detail views
  - Cards/tiles

**Implementation:**
```typescript
// Fetch creator info (you may need to add a lookup endpoint)
interface RecordWithCreator {
  id: string;
  name: string;
  created_by?: string;
  created_by_name?: string; // Populated from user lookup
  created_at: string;
}

// Display in UI
<div className="record-card">
  <h3>{plant.name}</h3>
  <div className="meta">
    <span>Created by {plant.created_by_name || 'Unknown'}</span>
    <span>{formatDate(plant.created_at)}</span>
  </div>
</div>
```

**Note:** You may need to:
- Add a user lookup endpoint: `GET /users/{user_id}` (if not exists)
- Or batch fetch creator names when loading lists
- Or add `created_by_name` to API responses (backend enhancement)

---

#### 5. **Company Admin Features**

**What to Add:**
- Company admin dashboard showing company-wide stats
- User management interface (already exists via `/company/all_users`)
- Company settings page

**New Features:**
```typescript
// Company Admin Dashboard
if (currentUser.role === 'company_admin') {
  // Show:
  // - Total company users
  // - Total company resources (plants, TMs, etc.)
  // - Company activity feed
  // - User management link
}
```

---

#### 6. **Super Admin Features**

**What to Add:**
- Company selector/filter
- Cross-company analytics
- Company management interface

**Implementation:**
```typescript
// Super Admin View
if (currentUser.role === 'super_admin') {
  // Show company filter dropdown
  <Select
    value={selectedCompanyId}
    onChange={setSelectedCompanyId}
  >
    <Option value="all">All Companies</Option>
    {companies.map(c => (
      <Option value={c.id}>{c.name}</Option>
    ))}
  </Select>
  
  // Show company badge on all records
  <Badge>{record.company_name}</Badge>
}
```

---

### **UI/UX Changes**

#### 7. **Empty States**

**Update all empty states:**
```typescript
// Before
"No plants found. Create your first plant!"

// After
{currentUser.role === 'company_admin' && (
  "No plants in your company yet. Create the first plant!"
)}
{currentUser.role === 'user' && (
  "No plants in your company yet. Contact your company admin."
)}
```

---

#### 8. **Breadcrumbs & Navigation**

**Add company context:**
```typescript
<Breadcrumb>
  <Breadcrumb.Item>Company: {companyName}</Breadcrumb.Item>
  <Breadcrumb.Item>Plants</Breadcrumb.Item>
</Breadcrumb>
```

---

#### 9. **Filtering & Search**

**Add creator filter:**
```typescript
<Filter>
  <Select placeholder="Filter by creator">
    <Option value="me">Created by me</Option>
    <Option value="all">All creators</Option>
    {companyUsers.map(u => (
      <Option value={u.id}>{u.name}</Option>
    ))}
  </Select>
</Filter>
```

---

#### 10. **Activity Feed / Audit Trail**

**New Feature to Add:**
- Show recent company activity
- Track who created/updated what
- Useful for company admins

**Implementation:**
```typescript
// Activity feed component
interface Activity {
  type: 'created' | 'updated' | 'deleted';
  resource_type: 'plant' | 'tm' | 'pump' | etc.;
  resource_name: string;
  user_name: string;
  timestamp: string;
}
```

---

### **API Response Changes**

#### 11. **Response Data Structure**

**All API responses now include:**
```typescript
// Example: GET /plants
{
  success: true,
  data: [
    {
      id: "...",
      name: "Plant A",
      company_id: "...",      // NEW
      created_by: "...",      // NEW
      user_id: "...",         // Still present (deprecated)
      // ... other fields
    }
  ]
}
```

**Frontend should:**
- Use `company_id` for filtering (if needed)
- Display `created_by` information
- Ignore `user_id` (deprecated)

---

### **Error Handling**

#### 12. **New Error Scenarios**

**Handle these cases:**
```typescript
// User not in a company
if (error.message === "User must belong to a company") {
  showError("You must be part of a company to access this feature");
  redirectTo('/onboard');
}

// Permission denied
if (error.status === 403) {
  showError("You don't have permission to perform this action");
}
```

---

## 📝 Detailed Checklist

### **Immediate Changes (High Priority)**

- [ ] Update user context to include `company_id`, `company_name`, `role`, `sub_role`
- [ ] Add permission checks for create/edit actions based on `sub_role`
- [ ] Update all "My X" labels to "Company X" or "X"
- [ ] Update empty states to reflect company-wide data
- [ ] Add creator name display in lists/details
- [ ] Test that company users see each other's data
- [ ] Test that company admin sees all company data
- [ ] Test that super admin sees all data

### **UI Enhancements (Medium Priority)**

- [ ] Add company name/logo in header/navigation
- [ ] Add creator filter in list views
- [ ] Add "Created by" badges/cards
- [ ] Update breadcrumbs to show company context
- [ ] Add company admin dashboard
- [ ] Add super admin company selector
- [ ] Add activity feed/audit trail

### **New Features (Low Priority)**

- [ ] User lookup endpoint integration (to show creator names)
- [ ] Company statistics dashboard
- [ ] Cross-company analytics (super admin)
- [ ] Export company data feature
- [ ] Company-level reports

---

## 🔍 Testing Checklist

### **Test Scenarios**

1. **Company Admin:**
   - [ ] Can see all plants created by any company user
   - [ ] Can edit any company resource
   - [ ] Can see company users list
   - [ ] Can manage company settings

2. **User (Editor):**
   - [ ] Can see all company data
   - [ ] Can create new resources
   - [ ] Can edit resources
   - [ ] Cannot see other companies' data

3. **User (Viewer):**
   - [ ] Can see all company data
   - [ ] Cannot see create/edit buttons
   - [ ] Cannot access create/edit endpoints (frontend blocked)
   - [ ] Cannot see other companies' data

4. **Super Admin:**
   - [ ] Can see all data from all companies
   - [ ] Can filter by company
   - [ ] Can manage companies
   - [ ] Can see all users across companies

---

## 🚀 Migration Steps for Frontend

### **Step 1: Update User Context**
```typescript
// Update your auth context/store
const user = await fetch('/auth/me');
// Ensure it includes: company_id, company_name, role, sub_role
```

### **Step 2: Add Permission Utilities**
```typescript
// utils/permissions.ts
export const canEdit = (user: User) => {
  return user.role === 'super_admin' || 
         user.role === 'company_admin' ||
         (user.role === 'user' && user.sub_role === 'editor');
};

export const canView = (user: User) => {
  return user.role === 'super_admin' || 
         user.role === 'company_admin' ||
         user.role === 'user';
};
```

### **Step 3: Update Components**
- Replace "My X" with "Company X"
- Add permission checks to buttons
- Add creator display
- Update empty states

### **Step 4: Test Thoroughly**
- Test with different user roles
- Test company isolation
- Test super admin access

---

## 📚 API Endpoints Reference

### **No Changes (Same Endpoints, Different Data)**
- `GET /plants` - Now returns all company plants
- `GET /tms` - Now returns all company TMs
- `GET /pumps` - Now returns all company pumps
- `GET /team` - Now returns all company team members
- `GET /projects` - Now returns all company projects
- `GET /clients` - Now returns all company clients
- `GET /schedules` - Now returns all company schedules
- All create/update/delete endpoints work the same

### **New Fields in Responses**
All responses now include:
- `company_id`: Company identifier
- `created_by`: User ID who created the record
- `user_id`: Still present (deprecated, ignore in frontend)

---

## ⚠️ Breaking Changes

### **None!**
- All API endpoints remain the same
- Request/response structure is the same
- Only the **data returned** is different (company-wide instead of user-specific)

### **What Frontend Must Handle:**
1. More data in lists (company-wide)
2. Need to show creator information
3. Need to enforce viewer permissions
4. Need to handle company context in UI

---

## 🎯 Summary

**Backend Changes:**
- ✅ All data is now company-scoped
- ✅ All APIs filter by `company_id`
- ✅ Super admin can see all companies
- ✅ `created_by` tracks who created what

**Frontend Changes Needed:**
1. Update labels and empty states
2. Add permission checks (viewer vs editor)
3. Display creator information
4. Add company context in UI
5. Handle super admin company selector
6. Test company isolation

**No API Changes Required:**
- Same endpoints
- Same request format
- Same response structure (just more data)

---

## 📞 Support

If you encounter issues:
1. Check user's `company_id` is set
2. Verify `role` and `sub_role` are correct
3. Ensure frontend is passing `current_user` correctly
4. Check backend logs for company filtering

---

**Last Updated:** After Company Awareness Migration
**Version:** 1.0

