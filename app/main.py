from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import json
from datetime import date, datetime
from typing import Any

# Custom JSON encoder to handle date and datetime objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

# Custom JSONResponse that uses our encoder
class CustomJSONResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
            cls=CustomJSONEncoder,
        ).encode("utf-8")

# Import routes
from app.routes import projects, pumps, tms, schedules, auth, plants, schedule_calendar, clients, dashboard, team_members, company

# Create FastAPI app
app = FastAPI(
    title="Concrete Supply Scheduling API",
    description="API for concrete supply scheduling and transit mixer management",
    version="1.0.0",
    default_response_class=CustomJSONResponse  # Use our custom response class for all endpoints
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000","https://tmhire-frontend.vercel.app", "https://tmgrid.in"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers for standardized error responses
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return CustomJSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "data": None
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return CustomJSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "message": "Validation error",
            "data": {"errors": exc.errors()}
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return CustomJSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "message": "Internal server error",
            "data": {"detail": str(exc)}
        },
    )

# Include routers
# edit
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(company.router, prefix="/company", tags=["Company"])
app.include_router(plants.router, prefix="/plants", tags=["Plants"])
app.include_router(tms.router, prefix="/tms", tags=["Transit Mixers"])
app.include_router(pumps.router, prefix="/pumps", tags=["Pumps"])
app.include_router(schedules.router, prefix="/schedules", tags=["Schedules"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

# TODO: Deprecated - To be replaced by the new endpoints:
# - GET /tm/:id/availability replaces GET /calendar/tm/{tm_id}
# - GET /schedule/daily replaces calendar-based viewing
# The schedule_calendar router can be removed once all clients migrate to the new endpoints.
app.include_router(schedule_calendar.router, prefix="/calendar", tags=["Schedule Calendar"])

app.include_router(clients.router, prefix="/clients", tags=["Clients"])
app.include_router(projects.router, prefix="/projects", tags=["Projects"])
app.include_router(team_members.router, prefix="/team", tags=["Team Members"])

@app.get("/")
async def root():
    return {
        "success": True, 
        "message": "Welcome to Concrete Supply Scheduling API",
        "data": {"version": "1.0.0"}
    }

@app.get("/ping")
async def ping():
    return JSONResponse(content={"message": "pong"}, status_code=200)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)