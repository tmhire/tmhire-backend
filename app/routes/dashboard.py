from fastapi import APIRouter, Depends, Query
from app.models.user import UserModel
from app.services.auth_service import get_current_user
from app.services.dashboard_service import get_dashboard_stats
from app.schemas.response import StandardResponse
from typing import Dict, Any
from datetime import date, datetime

router = APIRouter(tags=["Dashboard"])

@router.get("/", response_model=StandardResponse[Dict[str, Any]])
async def get_dashboard(
    date_val: date | str = Query(datetime.now().date(), description="Get dashboard stats for a specific date (YYYY-MM-DD)"),
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get dashboard statistics including counts, monthly trends, and recent orders.
    
    Returns:
    - counts: Current counts of plants, transit mixers, clients, pumps, and today's orders
    - monthly_stats: 12-month historical data for pumping quantity and TMs used
    - recent_orders: List of recent orders with client, quantity, and status
    """
    dashboard_data = await get_dashboard_stats(date_val, current_user)
    return StandardResponse(
        success=True,
        message="Dashboard statistics retrieved successfully",
        data=dashboard_data
    )
