from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routes
from app.routes import tms, schedules, auth

# Create FastAPI app
app = FastAPI(
    title="Concrete Supply Scheduling API",
    description="API for concrete supply scheduling and transit mixer management",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # 👈 No wildcard here
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(tms.router, prefix="/tms", tags=["Transit Mixers"])
app.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])

@app.get("/")
async def root():
    return {"message": "Welcome to Concrete Supply Scheduling API"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 