🧱 Concrete Supply Scheduling Backend – FastAPI + MongoDB
You are building a full-stack web app for concrete supply scheduling. This is the complete backend specification for a FastAPI project using MongoDB with Motor (async). Structure the project cleanly for real-world scalability.

🧑‍💼 User Authentication
Implement Google SSO login using OAuth2 (placeholder is okay for now).

Store user info:

_id (ObjectId)

email (string)

name (string)

created_at (timestamp)

🚛 Transit Mixers (TMs)
Maintain a separate collection for Transit Mixers.

Each TM document:

json
Copy
Edit
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "identifier": "TM-A",
  "capacity": 8.0,
  "created_at": "2025-05-05T10:00:00"
}
Full CRUD required:

GET /tms

POST /tms

PUT /tms/{id}

DELETE /tms/{id}

Also include a service to compute average capacity for all TMs belonging to a user.

📋 Schedule Management
Each schedule represents a delivery plan for a specific client/project.

Schedule document:

json
Copy
Edit
{
  "_id": ObjectId,
  "user_id": ObjectId,
  "client_name": "ABC Constructions",
  "created_at": "2025-05-05T10:00:00",
  "last_updated": "2025-05-05T10:00:00",
  "input_params": {
    "quantity": 60,
    "pumping_speed": 30,
    "onward_time": 30,
    "return_time": 25,
    "buffer_time": 5
  },
  "output_table": [...], // generated
  "tm_count": 6, // from TM collection
  "pumping_time": 2.0, // derived
  "status": "draft"
}
🧮 Input Params (in schedule)
These are submitted by user and stored:

quantity (m³)

pumping_speed (m³/hr)

onward_time (min)

return_time (min)

buffer_time (min)

🚫 Do not include tm_capacity or unloading_time in inputs. They are dynamically calculated.

🔄 Dynamic Logic
TM Capacity: Calculate average capacity from the user's TM records.

Unloading Time (min): Use this lookup based on average capacity:

Capacity (m³)	Unloading Time
6	10
7	12
8	14
9	16
10	18

Round the average capacity to the nearest key in the above table.

📊 Output Schedule Table
Stored as an array of trips:

json
Copy
Edit
[
  {
    "trip_no": 1,
    "tm_no": "A",
    "plant_start": "08:30",
    "pump_start": "09:00",
    "unloading_time": "09:12",
    "return": "09:52"
  },
  ...
]
🧠 Services Required
Get average TM capacity for a user

Get unloading time from average capacity

Calculate tm_count from TM collection

Calculate pumping_time = quantity / pumping_speed

Optional: table generation logic (/generate)

🔌 API Endpoints
Auth
POST /auth/google

TMs
GET /tms

POST /tms

PUT /tms/{id}

DELETE /tms/{id}

Schedules
GET /schedules

GET /schedules/{id}

POST /schedules

PUT /schedules/{id}

DELETE /schedules/{id}

POST /schedules/{id}/generate

🗂️ Project Directory Structure
bash
Copy
Edit
/app
├── main.py
├── models/        # Mongo models or pydantic schemas
├── schemas/       # Pydantic request/response models
├── routes/        # API routes
├── services/      # Business logic (avg capacity, unloading, etc.)
└── db/            # Mongo connection init
🛠️ Tech Stack
FastAPI (backend framework)

Motor (async MongoDB driver)

Pydantic (schemas & validation)

OAuthlib / Authlib (Google SSO – placeholder for now)

Uvicorn (server)

Optional: Beanie (if ODM is preferred over raw Motor)

✅ Notes
MongoDB is free to host via MongoDB Atlas with a generous free tier (shared cluster).

It works well with FastAPI using Motor (official async driver).

Schema-less flexibility is great for rapidly iterating.

