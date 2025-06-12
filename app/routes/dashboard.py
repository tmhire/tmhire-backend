from fastapi import APIRouter, Depends
from app.models.user import UserModel
from app.services.auth_service import get_current_user
from app.services.dashboard_service import get_dashboard_stats
from app.schemas.response import StandardResponse
from typing import Dict, Any

router = APIRouter(tags=["Dashboard"])

@router.get("/", response_model=StandardResponse[Dict[str, Any]])
async def get_dashboard(current_user: UserModel = Depends(get_current_user)):
    """
    Get dashboard statistics including counts, monthly trends, and recent orders.
    
    Returns:
    - counts: Current counts of plants, transit mixers, clients, pumps, and today's orders
    - monthly_stats: 12-month historical data for pumping quantity and TMs used
    - recent_orders: List of recent orders with client, quantity, and status
    """
    dashboard_data = await get_dashboard_stats(str(current_user.id))
    return StandardResponse(
        success=True,
        message="Dashboard statistics retrieved successfully",
        data=dashboard_data
    )
