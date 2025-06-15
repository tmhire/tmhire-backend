from fastapi import FastAPI
from mangum import Mangum

# Import your existing app modules
from app.routes import auth, clients, dashboard, plants, pumps, schedule_calendar, schedules, tms
from app.db.mongodb import init_mongodb

app = FastAPI()

# Initialize MongoDB connection
@app.on_event("startup")
async def startup_db_client():
    await init_mongodb()

# Include all your existing routers
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(dashboard.router)
app.include_router(plants.router)
app.include_router(pumps.router)
app.include_router(schedule_calendar.router)
app.include_router(schedules.router)
app.include_router(tms.router)

@app.get("/")
async def read_root():
    return {"message": "Hello from Concrete Management API on Vercel"}

# Convert to AWS Lambda handler
handler = Mangum(app)
