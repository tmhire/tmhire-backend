from fastapi import APIRouter, Depends, HTTPException, status
from app.models.project import ProjectModel, ProjectCreate, ProjectUpdate
from app.models.user import UserModel
from app.services.project_service import (
    get_all_projects, get_project, create_project, update_project, delete_project, 
    get_project_schedules, get_project_stats, get_all_projects_for_mother_plant,
    migrate_projects_with_mother_plant, get_projects_without_mother_plant
)
from app.services.auth_service import get_current_user
from typing import List, Dict, Any
from app.schemas.response import StandardResponse

router = APIRouter(tags=["Projects"])

@router.get("/", response_model=StandardResponse[List[ProjectModel]])
async def read_projects(current_user: UserModel = Depends(get_current_user)):
    """
    Retrieve all projects for the current user.
    
    Returns a list of all projects belonging to the authenticated user.
    """
    projects = await get_all_projects(current_user)
    return StandardResponse(
        success=True,
        message="Projects retrieved successfully",
        data=projects
    )

@router.post("/", response_model=StandardResponse[ProjectModel], status_code=status.HTTP_201_CREATED)
async def create_new_project(
    project: ProjectCreate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Create a new project.
    
    Requires project details in the request body.
    Returns the newly created project with its ID.
    """
    new_project = await create_project(project, current_user)
    return StandardResponse(
        success=True,
        message="Project created successfully",
        data=new_project
    )

@router.get("/{project_id}", response_model=StandardResponse[ProjectModel])
async def read_project(
    project_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve a specific project by ID.
    
    Path parameter:
    - project_id: The ID of the project to retrieve
    
    Returns the project details if found.
    """
    project = await get_project(project_id, current_user)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return StandardResponse(
        success=True,
        message="Project retrieved successfully",
        data=project
    )

@router.put("/{project_id}", response_model=StandardResponse[ProjectModel])
async def update_project_details(
    project_id: str,
    project: ProjectUpdate,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Update a project's details.
    
    Path parameter:
    - project_id: The ID of the project to update
    
    Request body:
    - Updated project fields (only fields to be updated need to be included)
    
    Returns the updated project details.
    """
    updated_project = await update_project(project_id, project, current_user)
    if not updated_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return StandardResponse(
        success=True,
        message="Project updated successfully",
        data=updated_project
    )

@router.delete("/{project_id}", response_model=StandardResponse)
async def delete_project_record(
    project_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Delete a project.
    
    Path parameter:
    - project_id: The ID of the project to delete
    
    Returns a success status and message. Will not delete projects that have associated schedules.
    """
    result = await delete_project(project_id, current_user)
    if not result["success"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["message"]
        )
    return StandardResponse(
        success=True,
        message=result["message"],
        data=None
    )

@router.get("/{project_id}/schedules", response_model=StandardResponse[Dict])
async def read_project_schedules(
    project_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve all schedules for a specific project.
    
    Path parameter:
    - project_id: The ID of the project
    
    Returns the project details along with all their associated schedules.
    """
    result = await get_project_schedules(project_id, current_user)
    if not result["project"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return StandardResponse(
        success=True,
        message="Project schedules retrieved successfully",
        data=result
    )

@router.get("/{project_id}/stats", response_model=StandardResponse[Dict[str, Any]])
async def read_project_stats(
    project_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve statistics for a specific project.
    
    Path parameter:
    - project_id: The ID of the project
    
    Returns statistics including:
    - Total scheduled volume
    - Total delivered volume
    - Pending delivery volume
    - Recent trip summaries
    """    
    stats = await get_project_stats(project_id, current_user)
    return StandardResponse(
        success=True,
        message="Project statistics retrieved successfully",
        data=stats
    ) 

@router.get("/mother-plant/{mother_plant_id}", response_model=StandardResponse[List[ProjectModel]])
async def read_projects_by_mother_plant(
    mother_plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve all projects for a specific mother plant.
    
    Path parameter:
    - mother_plant_id: The ID of the mother plant
    
    Returns a list of all projects associated with the specified mother plant.
    """
    projects = await get_all_projects_for_mother_plant(current_user, mother_plant_id)
    return StandardResponse(
        success=True,
        message="Projects for mother plant retrieved successfully",
        data=projects
    )

@router.get("/without-mother-plant", response_model=StandardResponse[List[ProjectModel]])
async def read_projects_without_mother_plant(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Retrieve all projects that don't have a mother plant assigned.
    
    Returns a list of all projects without a mother plant.
    """
    projects = await get_projects_without_mother_plant(current_user)
    return StandardResponse(
        success=True,
        message="Projects without mother plant retrieved successfully",
        data=projects
    )

@router.post("/migrate/{mother_plant_id}", response_model=StandardResponse[Dict[str, Any]])
async def migrate_projects_to_mother_plant(
    mother_plant_id: str,
    current_user: UserModel = Depends(get_current_user)
):
    """
    Migrate all projects without a mother plant to assign the specified mother plant.
    
    Path parameter:
    - mother_plant_id: The ID of the mother plant to assign
    
    Returns migration results.
    """
    result = await migrate_projects_with_mother_plant(current_user, mother_plant_id)
    return StandardResponse(
        success=True,
        message=result["message"],
        data=result
    ) 