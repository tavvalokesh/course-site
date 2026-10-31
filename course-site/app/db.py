import os
from dotenv import load_dotenv
from pymongo import AsyncMongoClient, ASCENDING, DESCENDING

load_dotenv()

client = AsyncMongoClient(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))
db = client[os.getenv("MONGODB_DB", "course_site").strip()]
courses = db["courses"]


async def ensure_indexes():
    await courses.create_index([("uploaded_at", DESCENDING)])
    await courses.create_index([("tags", ASCENDING)])
    await courses.create_index([("views", DESCENDING)])
