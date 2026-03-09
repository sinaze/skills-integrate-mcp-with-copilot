"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""


from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
from sqlalchemy import create_engine, Column, Integer, String, Table, MetaData
from sqlalchemy.orm import sessionmaker
from databases import Database


app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Database setup
DATABASE_URL = "sqlite:///./activities.db"
database = Database(DATABASE_URL)
engine = create_engine(DATABASE_URL.replace('sqlite://', 'sqlite:///'))
metadata = MetaData()

activities_table = Table(
    "activities",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("name", String, unique=True, nullable=False),
    Column("description", String),
    Column("schedule", String),
    Column("max_participants", Integer),
)

participants_table = Table(
    "participants",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("activity_id", Integer),
    Column("email", String),
)

metadata.create_all(engine)

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")




@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")



import asyncio

@app.on_event("startup")
async def startup():
    await database.connect()

@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()

@app.get("/activities")
async def get_activities():
    query = activities_table.select()
    activities_result = await database.fetch_all(query)
    activities_list = []
    for activity in activities_result:
        participants_query = participants_table.select().where(participants_table.c.activity_id == activity["id"])
        participants_result = await database.fetch_all(participants_query)
        participants = [p["email"] for p in participants_result]
        activity_dict = dict(activity)
        activity_dict["participants"] = participants
        activities_list.append(activity_dict)
    return activities_list



@app.post("/activities/{activity_name}/signup")
async def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    # Validate activity exists
    query = activities_table.select().where(activities_table.c.name == activity_name)
    activity = await database.fetch_one(query)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is not already signed up
    participants_query = participants_table.select().where(
        (participants_table.c.activity_id == activity["id"]) & (participants_table.c.email == email)
    )
    participant = await database.fetch_one(participants_query)
    if participant:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    # Add student
    insert_query = participants_table.insert().values(activity_id=activity["id"], email=email)
    await database.execute(insert_query)
    return {"message": f"Signed up {email} for {activity_name}"}



@app.delete("/activities/{activity_name}/unregister")
async def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    # Validate activity exists
    query = activities_table.select().where(activities_table.c.name == activity_name)
    activity = await database.fetch_one(query)
    if not activity:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Validate student is signed up
    participants_query = participants_table.select().where(
        (participants_table.c.activity_id == activity["id"]) & (participants_table.c.email == email)
    )
    participant = await database.fetch_one(participants_query)
    if not participant:
        raise HTTPException(status_code=400, detail="Student is not signed up for this activity")

    # Remove student
    delete_query = participants_table.delete().where(
        (participants_table.c.activity_id == activity["id"]) & (participants_table.c.email == email)
    )
    await database.execute(delete_query)
    return {"message": f"Unregistered {email} from {activity_name}"}
