from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
import asyncpg

from app.db.database import get_pool
from app.utils.nlp_parser import parse_natural_language

router = APIRouter(prefix="/api/profiles", tags=["profiles"])

VALID_SORT_FIELDS = {"age", "created_at", "gender_probability"}
VALID_ORDERS = {"asc", "desc"}


def build_filter_query(
    gender, age_group, country_id, min_age, max_age,
    min_gender_probability, min_country_probability,
    sort_by, order, page, limit,
):
    conditions = []
    params = []
    idx = 1

    if gender is not None:
        conditions.append(f"gender = ${idx}")
        params.append(gender.lower())
        idx += 1

    if age_group is not None:
        conditions.append(f"age_group = ${idx}")
        params.append(age_group.lower())
        idx += 1

    if country_id is not None:
        conditions.append(f"country_id = ${idx}")
        params.append(country_id.upper())
        idx += 1

    if min_age is not None:
        conditions.append(f"age >= ${idx}")
        params.append(min_age)
        idx += 1

    if max_age is not None:
        conditions.append(f"age <= ${idx}")
        params.append(max_age)
        idx += 1

    if min_gender_probability is not None:
        conditions.append(f"gender_probability >= ${idx}")
        params.append(min_gender_probability)
        idx += 1

    if min_country_probability is not None:
        conditions.append(f"country_probability >= ${idx}")
        params.append(min_country_probability)
        idx += 1

    where = "WHERE " + " AND ".join(conditions) if conditions else ""
    order_clause = f"ORDER BY {sort_by} {order.upper()}"
    offset = (page - 1) * limit

    data_sql = f"""
        SELECT id, name, gender, gender_probability, age, age_group,
               country_id, country_name, country_probability,
               to_char(created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"') AS created_at
        FROM profiles
        {where}
        {order_clause}
        LIMIT ${idx} OFFSET ${idx + 1}
    """
    params_data = params + [limit, offset]

    count_sql = f"SELECT COUNT(*) FROM profiles {where}"
    params_count = params

    return data_sql, params_data, count_sql, params_count


def row_to_dict(row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "gender": row["gender"],
        "gender_probability": row["gender_probability"],
        "age": row["age"],
        "age_group": row["age_group"],
        "country_id": row["country_id"],
        "country_name": row["country_name"],
        "country_probability": row["country_probability"],
        "created_at": row["created_at"],
    }


@router.get("/search")
async def search_profiles(
    q: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    pool: asyncpg.Pool = Depends(get_pool),
):
    if not q or not q.strip():
        raise HTTPException(
            status_code=400,
            detail={"status": "error", "message": "Missing or empty parameter"},
        )

    parsed = parse_natural_language(q)

    if not parsed.valid:
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": parsed.error},
        )

    data_sql, params_data, count_sql, params_count = build_filter_query(
        parsed.gender, parsed.age_group, parsed.country_id,
        parsed.min_age, parsed.max_age, None, None,
        "created_at", "asc", page, limit,
    )

    async with pool.acquire() as conn:
        rows = await conn.fetch(data_sql, *params_data)
        total = await conn.fetchval(count_sql, *params_count)

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [row_to_dict(r) for r in rows],
    }


@router.get("")
async def get_profiles(
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    country_id: Optional[str] = Query(None),
    min_age: Optional[int] = Query(None, ge=0),
    max_age: Optional[int] = Query(None, ge=0),
    min_gender_probability: Optional[float] = Query(None, ge=0.0, le=1.0),
    min_country_probability: Optional[float] = Query(None, ge=0.0, le=1.0),
    sort_by: str = Query("created_at"),
    order: str = Query("asc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    pool: asyncpg.Pool = Depends(get_pool),
):
    if sort_by not in VALID_SORT_FIELDS:
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Invalid query parameters"},
        )
    if order not in VALID_ORDERS:
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Invalid query parameters"},
        )
    if gender is not None and gender.lower() not in ("male", "female"):
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Invalid query parameters"},
        )
    if age_group is not None and age_group.lower() not in {"child", "teenager", "adult", "senior"}:
        raise HTTPException(
            status_code=422,
            detail={"status": "error", "message": "Invalid query parameters"},
        )

    data_sql, params_data, count_sql, params_count = build_filter_query(
        gender, age_group, country_id, min_age, max_age,
        min_gender_probability, min_country_probability,
        sort_by, order, page, limit,
    )

    async with pool.acquire() as conn:
        rows = await conn.fetch(data_sql, *params_data)
        total = await conn.fetchval(count_sql, *params_count)

    return {
        "status": "success",
        "page": page,
        "limit": limit,
        "total": total,
        "data": [row_to_dict(r) for r in rows],
    }