import os
import secrets
import shutil
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import ReturnDocument

from app.db import courses, ensure_indexes
from app.search import autocomplete, rank_courses

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change-me")
ALLOWED_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v"}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await ensure_indexes()
    yield


app = FastAPI(title="Course Site", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/media", StaticFiles(directory=UPLOAD_DIR), name="media")
templates = Jinja2Templates(directory=BASE_DIR / "app" / "templates")


def _ser(doc):
    doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(value: str) -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId:
        raise HTTPException(status_code=404, detail="Course not found")


async def _all_courses():
    return [d async for d in courses.find()]


async def search_courses(query: str, limit: int = 20):
    ranked = rank_courses(await _all_courses(), query, limit)
    results = []
    for doc, score in ranked:
        doc = _ser(doc)
        doc["score"] = round(score, 3)
        results.append(doc)
    return results


# ---------- Pages ----------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    docs = [_ser(d) async for d in courses.find().sort("uploaded_at", -1).limit(100)]
    return templates.TemplateResponse(request, "index.html",
                                      {"courses": docs, "query": "", "title": "All courses"})


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    results = await search_courses(q)
    return templates.TemplateResponse(request, "index.html",
                                      {"courses": results, "query": q, "title": f"Search: {q}"})


@app.get("/courses/{course_id}", response_class=HTMLResponse)
async def course_page(request: Request, course_id: str):
    oid = _oid(course_id)
    course = await courses.find_one_and_update(
        {"_id": oid}, {"$inc": {"views": 1}}, return_document=ReturnDocument.AFTER
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    course = _ser(course)

    related = [
        _ser(d) async for d in courses.find(
            {"tags": {"$in": course.get("tags", [])}, "_id": {"$ne": oid}}
        ).limit(4)
    ]
    return templates.TemplateResponse(request, "course.html",
                                      {"c": course, "related": related, "title": course["title"]})


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    return templates.TemplateResponse(request, "upload.html", {"title": "Upload a course"})


@app.post("/upload")
async def upload_course(
    password: str = Form(...),
    title: str = Form(...),
    description: str = Form(""),
    category: str = Form("General"),
    tags: str = Form(""),
    video: UploadFile = File(...),
):
    if not secrets.compare_digest(password, ADMIN_PASSWORD):
        raise HTTPException(status_code=403, detail="Wrong admin password")

    ext = Path(video.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Use an .mp4, .webm, .mov or .m4v file")

    filename = f"{uuid.uuid4().hex}{ext}"
    with open(UPLOAD_DIR / filename, "wb") as out:
        shutil.copyfileobj(video.file, out)

    doc = {
        "title": title.strip(),
        "description": description.strip(),
        "category": category.strip() or "General",
        "tags": [t.strip().lower() for t in tags.split(",") if t.strip()],
        "video_url": f"/media/{filename}",
        "views": 0,
        "uploaded_at": datetime.now(timezone.utc),
    }
    result = await courses.insert_one(doc)
    return RedirectResponse(f"/courses/{result.inserted_id}", status_code=303)


# ---------- JSON API ----------

@app.get("/api/search")
async def api_search(q: str = "", limit: int = 20):
    return await search_courses(q, limit)


@app.get("/api/autocomplete")
async def api_autocomplete(q: str = ""):
    return autocomplete(await _all_courses(), q)
