import asyncio
from app.db.mongodb import plants, transit_mixers, schedules, pumps, clients
from app.models.user import UserModel
from bson import ObjectId
from typing import List, Dict, Any, Union
from datetime import datetime, timedelta, date
from calendar import monthrange
from pymongo import DESCENDING
from app.services.plant_service import get_all_plants
from app.services.pump_service import get_all_pumps
from app.services.schedule_calendar_service import _ensure_dateobj, _parse_datetime_with_timezone
from app.services.tm_service import get_all_tms
from fastapi import HTTPException

async def get_dashboard_stats(date_val: Union[date, str], current_user: UserModel) -> Dict[str, Any]:
    """Get all dashboard statistics for the current user's company."""
    if not current_user.company_id:
        raise HTTPException(status_code=400, detail="User must belong to a company")
    
    date_val = _ensure_dateobj(date_val)
    day_start = datetime.combine(date_val, datetime.min.time())
    day_end = datetime.combine(date_val, datetime.max.time())

    # Get counts
    schedule_query = {
        "status": "generated",
            "$or": [
            {
                "output_table.plant_start": {
                    "$gte": day_start.isoformat(),
                    "$lt": day_end.isoformat()
                }
            },
            {
                "output_table.return": {
                    "$gte": day_start.isoformat(),
                    "$lt": day_end.isoformat()
                }
            },
            {
                "burst_table.plant_start": {
                    "$gte": day_start.isoformat(),
                    "$lt": day_end.isoformat()
                }
            },
            {
                "burst_table.return": {
                    "$gte": day_start.isoformat(),
                    "$lt": day_end.isoformat()
                }
            }
        ]
    }
    
    # Filter by company_id if not super admin
    if current_user.role != "super_admin":
        schedule_query["company_id"] = ObjectId(current_user.company_id)
    
    all_plants, all_tms, all_pumps, schedules_in_date = await asyncio.gather(
        get_all_plants(current_user),
        get_all_tms(current_user),
        get_all_pumps(current_user),
        schedules.find(schedule_query).sort("created_at", DESCENDING).to_list(length=None)
    )

    active_plants_count, inactive_plants_count = 0, 0
    plant_table = {}
    for plant in all_plants:
        plant = plant.model_dump()
        if plant.get("status", "active") == "active":
            active_plants_count += 1
        else:
            inactive_plants_count += 1

        plant_table[str(plant.get("id"))] = {
            "plant_name": plant.get("name", "Unknown Plant"),
            "pump_volume": 0,
            "pump_jobs": set(),
            "supply_volume": 0,
            "supply_jobs": set(),
            "tm_used": 0,
            "tm_used_total_hours": 0,
            "line_pump_used": 0,
            "line_pump_used_total_hours": 0,
            "boom_pump_used": 0,
            "boom_pump_used_total_hours": 0,
            "tm_active_but_not_used": 0,
            "line_pump_active_but_not_used": 0,
            "boom_pump_active_but_not_used": 0
        }
    
    active_tms_count, inactive_tms_count = 0, 0
    tm_map = {}
    for tm in all_tms:
        tm = tm.model_dump()
        if tm.get("status", "active") == "active":
            active_tms_count += 1
        else:
            inactive_tms_count += 1
        tm_map[str(tm.get("id"))] = {**tm, "seen": False}

    active_line_pumps_count, inactive_line_pumps_count, active_boom_pumps_count, inactive_boom_pumps_count = 0, 0, 0, 0
    pump_map = {}
    for pump in all_pumps:
        pump = pump.model_dump()
        if pump.get("status", "active") == "active":
            if pump.get("type") == "line":
                active_line_pumps_count += 1
            elif pump.get("type") == "boom":
                active_boom_pumps_count += 1
        else:
            if pump.get("type") == "line":
                inactive_line_pumps_count += 1
            elif pump.get("type") == "boom":
                inactive_boom_pumps_count += 1
        pump_map[str(pump.get("id"))] = {**pump, "seen": False}

    for schedule in schedules_in_date:
        schedule_type = "pump" if schedule.get("type", "pumping") == "pumping" else "supply"

        # Check if this schedule uses burst model
        is_burst_model = schedule.get("input_params", {}).get("is_burst_model", False)
        
        # Choose the appropriate table based on is_burst_model
        trips = schedule.get("burst_table", []) if is_burst_model else schedule.get("output_table", [])
        if not trips:
            print("No trips", trips, schedule)
            continue
        start_time = trips[0].get("pump_start")
        end_time = trips[-1].get("unloading_time")
        if not start_time or not end_time:
            print("No start and end time", start_time, end_time)
            continue
        pump_onward_time = schedule.get("input_params", {}).get("pump_onward_time", 0)
        pump_fixing_time = schedule.get("input_params", {}).get("pump_fixing_time", 0)
        pump_removal_time = schedule.get("input_params", {}).get("pump_removal_time", 0)
        start_time = _parse_datetime_with_timezone(start_time)
        end_time = _parse_datetime_with_timezone(end_time)
        actual_start_time = start_time - timedelta(minutes=(pump_onward_time + pump_fixing_time))
        actual_end_time = end_time + timedelta(minutes=pump_removal_time + pump_onward_time)
        if actual_start_time == None or actual_end_time == None:
            print("No actual start and end time", actual_start_time, actual_end_time)
            continue
        
        pump, plant_id_of_pump = None, None
        if str(schedule.get("pump", None)) in pump_map:
            pump = pump_map[str(schedule.get("pump"))]
            plant_id_of_pump = str(pump["plant_id"])
        if pump and plant_id_of_pump and plant_id_of_pump in plant_table:
            plant_table[plant_id_of_pump][f"{schedule_type}_jobs"].add(str(schedule.get("_id")))
            pump_type = "line_pump_used" if pump["type"] == "line" else "boom_pump_used"
            if pump["seen"] == False:
                plant_table[plant_id_of_pump][pump_type] += 1
                pump["seen"] = True
            plant_table[plant_id_of_pump][f"{pump_type}_total_hours"] += (actual_end_time - actual_start_time).total_seconds() / 3600

        tm_usage_in_schedule = {}
        completed_capacity = 0
        for trip in trips:
            tm, plant_id_of_tm = None, None
            tm_id = str(trip.get("tm_id", None))
            if tm_id in tm_map:
                tm = tm_map[tm_id]
                plant_id_of_tm = str(tm["plant_id"])
            if tm and plant_id_of_tm and plant_id_of_tm in plant_table:
                plant_table[plant_id_of_tm][f"{schedule_type}_jobs"].add(str(schedule.get("_id")))
                if tm["seen"] == False:
                    plant_table[plant_id_of_tm]["tm_used"] += 1
                    tm["seen"] = True
                if trip.get("completed_capacity", 0):
                    plant_table[plant_id_of_tm][f"{schedule_type}_volume"] += trip.get("completed_capacity", 0) - completed_capacity
                    completed_capacity = trip.get("completed_capacity", 0)
                if trip.get("plant_buffer", None) is None or trip.get("return", None) is None:
                    continue
                if tm_id not in tm_usage_in_schedule:
                    tm_usage_in_schedule[tm_id] = {"start": trip.get("plant_buffer"), "end": trip.get("return"), "schedule_no": schedule.get("schedule_no", "")}
                    continue
                tm_usage_in_schedule[tm_id]["start"] = min(tm_usage_in_schedule[tm_id]["start"], trip.get("plant_buffer"))
                tm_usage_in_schedule[tm_id]["end"] = max(tm_usage_in_schedule[tm_id]["end"], trip.get("return"))
        for tm_id in tm_usage_in_schedule.keys():
            tm = tm_map[tm_id]
            plant_id_of_tm = str(tm["plant_id"])
            plant_table[plant_id_of_tm]["tm_used_total_hours"] += ( _parse_datetime_with_timezone(tm_usage_in_schedule[tm_id]["end"]) - _parse_datetime_with_timezone(tm_usage_in_schedule[tm_id]["start"]) ).total_seconds() / 3600
        
    # Count active but not used TMs and Pumps
    for tm in tm_map.values():
        if tm["seen"] == False and tm.get("status", "active") == "active":
            plant_table[str(tm["plant_id"])]["tm_active_but_not_used"] += 1
    for pump in pump_map.values():
        if pump["seen"] == False and pump.get("status", "active") == "active":
            if pump.get("type") == "line":
                plant_table[str(pump["plant_id"])]["line_pump_active_but_not_used"] += 1
            elif pump.get("type") == "boom":
                plant_table[str(pump["plant_id"])]["boom_pump_active_but_not_used"] += 1
        
    for column in plant_table.values():
        column["pump_jobs"] = len(column["pump_jobs"])
        column["supply_jobs"] = len(column["supply_jobs"])
        column["tm_used_total_hours"] = round(column["tm_used_total_hours"], 2)
        column["line_pump_used_total_hours"] = round(column["line_pump_used_total_hours"], 2)
        column["boom_pump_used_total_hours"] = round(column["boom_pump_used_total_hours"], 2)

    # Calculate monthly statistics for the past 12 months
    monthly_stats = await get_monthly_stats(current_user)

    # Get recent orders
    recent_orders = await get_recent_orders(current_user)
    
    # Format the response according to the required structure
    return {
        "counts": {
            "active_plants_count": active_plants_count,
            "inactive_plants_count": inactive_plants_count,
            "active_tms_count": active_tms_count,
            "inactive_tms_count": inactive_tms_count,
            "active_line_pumps_count": active_line_pumps_count,
            "inactive_line_pumps_count": inactive_line_pumps_count,
            "active_boom_pumps_count": active_boom_pumps_count,
            "inactive_boom_pumps_count": inactive_boom_pumps_count,
        },
        "plants_table": plant_table,
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

async def get_monthly_stats(current_user: UserModel) -> Dict[str, List[float]]:
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
        month_query = {
            "created_at": {
                "$gte": month_start,
                "$lt": month_end
            }
        }
        
        # Filter by company_id if not super admin
        if current_user.role != "super_admin":
            if not current_user.company_id:
                series["pumping_quantity"].append(0.0)
                series["tms_used"].append(0.0)
                continue
            month_query["company_id"] = ObjectId(current_user.company_id)
        
        month_schedules = schedules.find(month_query)
        
        monthly_quantity = 0
        monthly_tms = set()
        
        async for schedule in month_schedules:
            # Sum up quantities
            input_params = schedule.get("input_params", {})
            monthly_quantity += input_params.get("quantity", 0)
            
            # Count unique TMs used
            # Check if this schedule uses burst model
            is_burst_model = schedule.get("input_params", {}).get("is_burst_model", False)
            
            # Choose the appropriate table based on is_burst_model
            trips_table = schedule.get("burst_table", []) if is_burst_model else schedule.get("output_table", [])
            for trip in trips_table:
                if trip.get("tm_id"):
                    monthly_tms.add(trip["tm_id"])
        
        series["pumping_quantity"].append(monthly_quantity)
        series["tms_used"].append(len(monthly_tms))
    
    return series

async def get_recent_orders(current_user: UserModel, limit: int = 10) -> List[Dict[str, Any]]:
    """Get recent orders with client, quantity, and status information."""
    recent_orders = []
    
    query = {}
    if current_user.role != "super_admin":
        if not current_user.company_id:
            return []
        query["company_id"] = ObjectId(current_user.company_id)
    
    cursor = schedules.find(query).sort("created_at", -1).limit(limit)
    
    async for order in cursor:
        quantity = order.get("input_params", {}).get("quantity", 0)
        recent_orders.append({
            "client": order.get("client_name", "Unknown Client"),
            "quantity": f"{quantity} m³",
            "order_date": order.get("created_at", datetime.utcnow()).strftime("%Y-%m-%d"),
            "status": order.get("status", "draft")
        })
    
    return recent_orders
