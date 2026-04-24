# Insighta Labs – Intelligence Query Engine

A FastAPI-powered demographic intelligence API with advanced filtering, sorting, pagination, and natural language search.

## Tech Stack
- Python 3.11+ / FastAPI / Uvicorn
- PostgreSQL (asyncpg)
- Railway (deployment)

## Local Setup

```bash
git clone <your-repo-url>
cd backend-wizards-stage2
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and set DATABASE_URL
python -m app.db.seed
uvicorn app.main:app --reload --port 8000