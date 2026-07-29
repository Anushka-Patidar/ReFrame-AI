from pymongo import ASCENDING

from app.db.database import get_database
from app.models.collections import PROFESSIONALS, USERS
from app.services.mongo import utc_now

DEMO_PROFESSIONALS = [
    {
        "name": "Rahul Sharma",
        "profession": "Interior Designer",
        "city": "Indore",
        "area": "Vijay Nagar",
        "phone": "+91 90000 11111",
        "experience_years": 6,
        "rating": 4.5,
        "availability": "Available",
    },
    {
        "name": "Neha Jain",
        "profession": "Interior Designer",
        "city": "Indore",
        "area": "Palasia",
        "phone": "+91 90000 22222",
        "experience_years": 4,
        "rating": 4.3,
        "availability": "Available this week",
    },
    {
        "name": "Amit Verma",
        "profession": "Carpenter",
        "city": "Indore",
        "area": "Scheme 78",
        "phone": "+91 90000 33333",
        "experience_years": 8,
        "rating": 4.7,
        "availability": "Available",
    },
]


async def ensure_seed_data() -> None:
    db = get_database()
    await db[USERS].create_index([("email", ASCENDING)], unique=True)
    await db[PROFESSIONALS].create_index([("profession", ASCENDING), ("city", ASCENDING)])

    professional_count = await db[PROFESSIONALS].count_documents({})
    if professional_count == 0:
        await db[PROFESSIONALS].insert_many(
            [{**professional, "created_at": utc_now()} for professional in DEMO_PROFESSIONALS]
        )
