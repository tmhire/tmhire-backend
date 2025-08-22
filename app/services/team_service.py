from datetime import datetime
from app.db.mongodb import team
from app.models.team import TeamMemberModel, TeamMemberCreate, TeamMemberUpdate
from bson import ObjectId
from typing import List, Optional, Dict, Literal
from pymongo import DESCENDING

groupSet = {
    "client": ["sales-engineer"],
    "pump": ["pump-operator", "pipeline-gang"],
    "schedule": ["site-supervisor"]
}

async def get_all_teams(user_id: str) -> List[TeamMemberModel]:
    """Get all team members for a user"""
    team_list = []
    async for member in team.find({"user_id": ObjectId(user_id)}).sort("created_at", DESCENDING):
        team_list.append(TeamMemberModel(**member))
    return team_list

async def get_team_member(id: str, user_id: str) -> Optional[TeamMemberModel]:
    """Get a specific team member by ID"""
    if id is None:
        return None
    member = await team.find_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    if member:
        return TeamMemberModel(**member)
    return None

async def get_team_group(group: Literal["client", "pump", "schedule"], user_id: str) -> List[TeamMemberModel]:
    "Get all team members in a specific group for a user"
    team_list = []
    async for member in team.find({
        "user_id": ObjectId(user_id),
        "designation": {"$in": groupSet[group]}
    }):
        team_list.append(TeamMemberModel(**member))
    return team_list

async def create_team_member(member: TeamMemberCreate, user_id: str) -> TeamMemberModel:
    """Create a new team member"""
    member_data = member.model_dump()
    member_data["user_id"] = ObjectId(user_id)
    member_data["created_at"] = datetime.utcnow()
    member_data["last_updated"] = datetime.utcnow()
    
    result = await team.insert_one(member_data)
    
    new_member = await team.find_one({"_id": result.inserted_id})
    return TeamMemberModel(**new_member)

async def update_team_member(id: str, member: TeamMemberUpdate, user_id: str) -> Optional[TeamMemberModel]:
    """Update a team member"""
    member_data = {k: v for k, v in member.model_dump().items() if v is not None}
    
    if not member_data:
        return await get_team_member(id, user_id)
    
    await team.update_one(
        {"_id": ObjectId(id), "user_id": ObjectId(user_id)},
        {"$set": member_data}
    )

    return await get_team_member(id, user_id)

async def delete_team_member(id: str, user_id: str) -> Dict[str, bool]:
    """Delete a team member"""
    result = await team.delete_one({"_id": ObjectId(id), "user_id": ObjectId(user_id)})
    return {"success": result.deleted_count > 0}
