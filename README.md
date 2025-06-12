# Concrete Supply Scheduling Backend

A FastAPI backend application for concrete supply scheduling with MongoDB integration.

## Features

- User authentication with Google SSO (placeholder implementation)
- Plant management for organizing Transit Mixers
- Transit Mixer management (CRUD operations)
- Schedule management with dynamic output table generation
- Schedule calendar system for tracking TM availability and booking
- Advanced scheduling algorithm to optimize TM utilization
- Asynchronous MongoDB operations using Motor

## Setup

1. Clone the repository
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

Create a `.env` file in the project root with the following variables:

```
MONGODB_URI=mongodb://localhost:27017
DB_NAME=concrete_supply
SECRET_KEY=your_secret_key
```

For production, you should use a MongoDB Atlas URI or another MongoDB server.

## Running the application

Start the server:

```bash
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

## API Documentation

Once the server is running, you can access the API documentation at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Authentication

- `POST /auth/google`: Google SSO login (placeholder)
- `POST /auth/token`: OAuth2 token login (for testing)

### Plants

- `GET /plants`: Get all plants
- `POST /plants`: Create a new plant
- `GET /plants/{id}`: Get a specific plant
- `PUT /plants/{id}`: Update a plant
- `DELETE /plants/{id}`: Delete a plant
- `GET /plants/{id}/tms`: Get all transit mixers for a specific plant

### Transit Mixers

- `GET /tms`: Get all transit mixers
- `POST /tms`: Create a new transit mixer
- `GET /tms/{id}`: Get a specific transit mixer
- `PUT /tms/{id}`: Update a transit mixer
- `DELETE /tms/{id}`: Delete a transit mixer
- `GET /tms/average-capacity`: Get average capacity of all transit mixers

### Schedules

- `GET /schedules`: Get all schedules
- `POST /schedules`: Create a new schedule
- `GET /schedules/{id}`: Get a specific schedule
- `PUT /schedules/{id}`: Update a schedule
- `DELETE /schedules/{id}`: Delete a schedule
- `POST /schedules/calculate-tm`: Calculate required TM count for a schedule
- `POST /schedules/{id}/generate-schedule`: Generate output table for a schedule

### Schedule Calendar

- `POST /calendar`: Get calendar data for a date range
- `GET /calendar/tm/{tm_id}`: Get availability slots for a specific TM on a specific date 