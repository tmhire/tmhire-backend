from datetime import datetime
from app.db.mongodb import team
from app.models.team import TeamMemberModel, TeamMemberCreate, TeamMemberUpdate
from app.models.user import UserModel
from bson import ObjectId
from typing import List, Optional, Dict, Literal
from pymongo import DESCENDING
from fastapi import HTTPException

groupSet = {
    "client": ["sales-engineer"],
    "pump": ["pump-operator", "pipeline-gang"],
    "schedule": ["site-supervisor"]
}

async def get_all_teams(current_user: UserModel) -> List[TeamMemberModel]:
    """Get all team members for the current user's company"""
    query = {}
    
    # Super admin can see all team members
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    team_list = []
    async for member in team.find(query).sort("created_at", DESCENDING):
        team_list.append(TeamMemberModel(**member))
    return team_list

async def get_team_member(id: str, current_user: UserModel) -> Optional[TeamMemberModel]:
    """Get a specific team member by ID"""
    if id is None:
        return None
    
    query = {"_id": ObjectId(id)}
    # Super admin can see all team members
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return None
        query["company_id"] = ObjectId(current_user.company_id)
    
    member = await team.find_one(query)
    if member:
        return TeamMemberModel(**member)
    return None

async def get_team_group(group: Literal["client", "pump", "schedule"], current_user: UserModel) -> List[TeamMemberModel]:
    "Get all team members in a specific group for the current user's company"
    query = {"designation": {"$in": groupSet[group]}}
    
    # Super admin can see all team members
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    team_list = []
    async for member in team.find(query):
        team_list.append(TeamMemberModel(**member))
    return team_list

async def create_team_member(member: TeamMemberCreate, current_user: UserModel) -> TeamMemberModel:
    """Create a new team member"""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    member_data = member.model_dump()
    member_data["company_id"] = ObjectId(current_user.company_id)
    member_data["created_by"] = ObjectId(current_user.id)
    member_data["user_id"] = ObjectId(current_user.id)  # Keep for compatibility
    member_data["created_at"] = datetime.utcnow()
    member_data["last_updated"] = datetime.utcnow()
    
    result = await team.insert_one(member_data)
    
    new_member = await team.find_one({"_id": result.inserted_id})
    return TeamMemberModel(**new_member)

async def update_team_member(id: str, member: TeamMemberUpdate, current_user: UserModel) -> Optional[TeamMemberModel]:
    """Update a team member"""
    member_data = {k: v for k, v in member.model_dump().items() if v is not None}
    
    if not member_data:
        return await get_team_member(id, current_user)
    
    query = {"_id": ObjectId(id)}
    # Super admin can update any team member
    if current_user.role != "super_admin":
        if not current_user.company_id:
            raise HTTPException(status_code=403, detail="User must belong to a company")
        query["company_id"] = ObjectId(current_user.company_id)
    
    await team.update_one(query, {"$set": member_data})

    return await get_team_member(id, current_user)

async def delete_team_member(id: str, current_user: UserModel) -> Dict[str, bool]:
    """Delete a team member"""
    # Verify team member exists and user has access
    member = await get_team_member(id, current_user)
    if not member:
        return {"success": False}
    
    query = {"_id": ObjectId(id)}
    if current_user.role != "super_admin":
        query["company_id"] = ObjectId(current_user.company_id)
    
    result = await team.delete_one(query)
    return {"success": result.deleted_count > 0}
