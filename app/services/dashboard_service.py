from app.db.mongodb import plants, transit_mixers, schedules, pumps, clients, PyObjectId
from bson import ObjectId
from typing import List, Dict, Any
from datetime import datetime, date, timedelta
from calendar import monthrange

async def get_dashboard_stats(user_id: str) -> Dict[str, Any]:
    """Get all dashboard statistics for a user."""
    # Convert string user_id to ObjectId
    user_id_obj = ObjectId(user_id)
    
    # Get counts
    plant_count = await plants.count_documents({"user_id": user_id_obj})
    tm_count = await transit_mixers.count_documents({"user_id": user_id_obj})
    client_count = await clients.count_documents({"user_id": user_id_obj})
    pump_count = await pumps.count_documents({"user_id": user_id_obj})
    
    # Get orders for today
    today = datetime.now().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_end = datetime.combine(today, datetime.max.time())
    
    today_orders = await schedules.count_documents({
        "user_id": user_id_obj,
        "created_at": {
            "$gte": today_start,
            "$lte": today_end
        }
    })
    
    # Calculate monthly statistics for the past 12 months
    monthly_stats = await get_monthly_stats(user_id_obj)

    # Get recent orders
    recent_orders = await get_recent_orders(user_id_obj)
    
    # Format the response according to the required structure
    return {
        "counts": {
            "plants": plant_count,
            "transit_mixers": tm_count,
            "clients": client_count,
            "pumps": pump_count,
            "orders_today": today_orders
        },
        "series": [
            {
                "name": "Pumping quantity",
                "data": monthly_stats["pumping_quantity"]
            },
            {
                "name": "TMs used",
                "data": monthly_stats["tms_used"]
            }
        ],
        "recent_orders": recent_orders
    }

async def get_monthly_stats(user_id: ObjectId) -> Dict[str, List[float]]:
    """Get pumping quantity and TMs used for the last 12 months."""
    current_date = datetime.now()
    series = {
        "pumping_quantity": [],
        "tms_used": []
    }
    
    for i in range(11, -1, -1):  # Last 12 months
        # Calculate start and end of month
        target_month = current_date - timedelta(days=current_date.day) - timedelta(days=30*i)
        days_in_month = monthrange(target_month.year, target_month.month)[1]
        month_start = datetime(target_month.year, target_month.month, 1)
        month_end = datetime(target_month.year, target_month.month, days_in_month, 23, 59, 59)
        
        # Get all schedules for this month
        month_schedules = schedules.find({
            "user_id": user_id,
            "created_at": {
                "$gte": month_start,
                "$lt": month_end
            }
        })
        
        monthly_quantity = 0
        monthly_tms = set()
        
        async for schedule in month_schedules:
            # Sum up quantities
            input_params = schedule.get("input_params", {})
            monthly_quantity += input_params.get("quantity", 0)
            
            # Count unique TMs used
            output_table = schedule.get("output_table", [])
            for trip in output_table:
                if trip.get("tm_id"):
                    monthly_tms.add(trip["tm_id"])
        
        series["pumping_quantity"].append(monthly_quantity)
        series["tms_used"].append(len(monthly_tms))
    
    return series

async def get_recent_orders(user_id: ObjectId, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent orders with client, quantity, and status information."""
    recent_orders = []
    cursor = schedules.find({"user_id": user_id}).sort("created_at", -1).limit(limit)
    
    async for order in cursor:
        quantity = order.get("input_params", {}).get("quantity", 0)
        recent_orders.append({
            "client": order.get("client_name", "Unknown Client"),
            "quantity": f"{quantity} m³",
            "order_date": order.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            "status": order.get("status", "draft")
        })
    
    return recent_orders
