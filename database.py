import os 
from databases import Database 
from sqlalchemy import create_engine, MetaData
from dotenv import load_dotenv 


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable not set")
SYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://")

database = Database(DATABASE_URL, min_size=1, max_size=5)

metadata = MetaData()
engine = create_engine(SYNC_DATABASE_URL, connect_args={"connect_timeout": 10})

print("DEBUG DB URL:", DATABASE_URL)

metadata.drop_all(engine)
metadata.create_all(engine)
