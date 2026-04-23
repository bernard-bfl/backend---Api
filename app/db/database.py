import asyncpg 
import os 
from dotenv import load_dotenv

load_dotenv()
_pool = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        database_url = os.getenv("DATABASE_URL")
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        _pool = await asyncpg.create_pool(
            dsn=database_url,
            min_size=2,
            max_size=10,
            ssl="require",
            
        )
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS profiles (
    id                  VARCHAR(36)   PRIMARY KEY,
    name                VARCHAR(255)  NOT NULL UNIQUE,
    gender              VARCHAR(10)   NOT NULL,
    gender_probability  FLOAT         NOT NULL,
    age                 INT           NOT NULL,
    age_group           VARCHAR(20)   NOT NULL,
    country_id          VARCHAR(2)    NOT NULL,
    country_name        VARCHAR(100)  NOT NULL,
    country_probability FLOAT         NOT NULL,
    created_at          TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);
"""

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_profiles_gender ON profiles(gender);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_age_group ON profiles(age_group);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_country_id ON profiles(country_id);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_age ON profiles(age);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_created_at ON profiles(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_gender_prob ON profiles(gender_probability);",
    "CREATE INDEX IF NOT EXISTS idx_profiles_country_prob ON profiles(country_probability);",
]


async def init_db():
    global _pool
    _pool = await get_pool()
    async with _pool.acquire() as conn:
        await conn.execute(CREATE_TABLE_SQL)
        for index_sql in INDEXES:
            await conn.execute(index_sql)
    print("✅ Database tables and indexes ready.")
