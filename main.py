from fastapi import FastAPI, Query 
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from contextlib import asynccontextmanager
import httpx
from datetime import datetime, timezone
from database import database, engine, metadata 
from models import profiles
from uuid_extensions import uuid7str
import asyncio
import logging
logging.basicConfig(level=logging.DEBUG)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await database.connect()
    yield
    await database.disconnect()

app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

metadata.create_all(engine)




def get_age_group(age:int) -> str:
    if age <= 12:
        return "child"
    elif age <= 19:
        return "teenager"
    elif age <= 59:
        return "adult"
    else:
        return "senior"
    

@app.post("/api/profiles") 
async def create_profile(payload: dict):
    #validating name 
    name = payload.get("name")
    if not name:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty name"}

        )
    if not isinstance(name, str):
        return JSONResponse(
            status_code=442,
            content={"status": "error", "message": "Invalid type"}
        )
    name = name.strip().lower()
    if name == "":
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Missing or empty name"}
        )
    
    #checking to see if the profile already exists
    query = profiles.select().where(profiles.c.name == name)
    existing = await database.fetch_one(query)
    if existing:
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Profile already exists",
                "data": dict(existing)
            }
        )
    
    #calling all 3 APIs at the same time 
    async with httpx.AsyncClient() as client:
        try:
            genderize, agify, nationalize = await asyncio.gather(
                client.get(f"https://api.genderize.io?name={name}"),
                client.get(f"https://api.agify.io?name={name}"),
                client.get(f"https://api.nationalize.io?name={name}")
            )  
            genderize_data = genderize.json()
            agify_data = agify.json()
            nationalize_data = nationalize.json()
        except Exception:
            return JSONResponse(
                status_code=502,
                content={"status": "error", "message": "Upstream service failure"}
            )
    #validating genderize response 
    if genderize_data.get("gender") is None or genderize_data.get("count") == 0:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Genderize returned an invalid response"}
        )
    
    #validating agify response 
    if agify_data.get("age") is None:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Agify returned an invalid response"}
        )
    
    #validating nationalize repsonse 
    countries = nationalize_data.get("country", [])
    if not countries:
        return JSONResponse(
            status_code=502,
            content={"status": "error", "message": "Nationalize returned an invalid response"}
        )
    
    #processing data 
    gender = genderize_data["gender"]
    gender_probability = genderize_data["probability"]
    sample_size = genderize_data["count"]
    age = agify_data["age"]
    age_group = get_age_group(age)
    top_country = max(countries, key=lambda x: x["probability"])
    country_id = top_country["country_id"]
    country_probability = top_country["probability"]
    created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    profile_id = uuid7str()

    insert_query = profiles.insert().values(
        id=profile_id,
        name=name,
        gender=gender,
        gender_probability=gender_probability,
        sample_size=sample_size,
        age=age,
        age_group=age_group,
        country_id=country_id,
        country_probability=country_probability,
        created_at=created_at
    )


    #save to the db
    await database.execute(insert_query)
    return JSONResponse(
        status_code=201,
        content={
            "status": "success",
            "data": {
                "id": profile_id,
                "name": name,
                "gender": gender,
                "gender_probability": gender_probability,
                "sample_size": sample_size,
                "age": age,
                "age_group": age_group,
                "country_id": country_id,
                "country_probability": country_probability,
                "created_at": created_at


            }
        }
    )
    
       

@app.get("/api/profiles")
async def get_all_profiles(
    gender: str = Query(default=None),
    country_id: str = Query(default=None),
    age_group: str = Query(default=None)
):
    query = profiles.select()
    results = await database.fetch_all(query)

    #applying  filters 
    filtered = []
    for profile in results:
        p = dict(profile)
        if gender and p["gender"].lower() != gender.lower():
            continue
        if country_id and p["country_id"].lower() != country_id.lower():
            continue
        if age_group and p["age_group"].lower() != age_group.lower():
            continue
        filtered.append(p)
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "count": len(filtered),
            "data": filtered
        }
    )

@app.get("/api/profiles/{id}")
async def get_profile(id: str):
    query = profiles.select().where(profiles.c.id == id)
    profile = await database.fetch_one(query)
    if not profile:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Profile not found"}
        )
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "data": dict(profile)
        }

    )

@app.delete("/api/profiles/{id}")
async def delete_profile(id: str):
    query = profiles.select().where(profiles.c.id == id)
    profile = await database.fetch_one(query)
    if not profile:
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Profile not found"}
        )
    delete_query = profiles.delete().where(profiles.c.id == id)
    await database.execute(delete_query)
    return JSONResponse(status_code=204, content=None)