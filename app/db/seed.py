import asyncio
import json
import os 
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.database import get_pool, init_db
from app.utils.uuid7 import generate_uuid7

def determine_age_group(age: int) -> str:
    if age < 13:
        return "child"
    elif age < 18:
        return "teenager"
    elif age < 65:
        return "adult"
    else:
        return "senior"
    
async def seed():
    from app.db.database import get_pool, CREATE_TABLE_SQL, INDEXES
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
        for index_sql in INDEXES:
            await conn.execute(index_sql)
    print("Database ready")

    
    json_path = Path(__file__).resolve().parents[2] / "profiles.json"
    if not json_path.exists():
        print(f"profiles.json not found at {json_path}")
        sys.exit(1)
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        profiles = data["profiles"] if isinstance(data, dict) else data

    pool = await get_pool()
    inserted = 0

    async with pool.acquire() as conn:
        for i in range(0, len(profiles), 200):
            chunk = profiles[i : i + 200]
            rows = []
            for p in chunk:
                age = int(p.get("age", 0))
                rows.append((
                    generate_uuid7(),
                    str(p["name"]).strip().lower(),
                    str(p.get("gender", "")).lower(),
                    float(p.get("gender_probability", 0)),
                    age,
                    determine_age_group(age),
                    str(p.get("country_id", "")).upper(),
                    str(p.get("country_name", "")),
                    float(p.get("country_probability", 0)),
                ))
            
            await conn.executemany(
                """
                INSERT INTO profiles
                    (id, name, gender, gender_probability, age, age_group, country_id, country_name, country_probability, created_at)
                VALUES  ($1,$2,$3,$4,$5,$6,$7,$8,$9, NOW())
                ON CONFLICT (name) DO NOTHING
                """,
                rows,

            )
            inserted += len(chunk)
            print(f"Seeded {inserted}/{len(profiles)}...")
    async with pool.acquire() as conn:
        total = await conn.fetchval("SELECT COUNT(*) FROM profiles")
    
    print(f"Seed complete. Total profiles in the DB: {total}")


asyncio.run(seed())