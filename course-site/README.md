# Course Site

A course video website built with FastAPI, MongoDB Atlas, and scikit-learn search.

## Setup in PyCharm

1. Open this folder in PyCharm (File > Open).
2. Create a virtual environment: File > Settings > Project > Python Interpreter > Add.
3. Open a terminal in PyCharm and run:
   pip install -r requirements.txt
4. Open `.env` and replace the MongoDB URI with your Atlas connection string,
   and set ADMIN_PASSWORD to a password only you know.
5. Start the server:
   uvicorn app.main:app --reload
6. Visit http://127.0.0.1:8000 and upload your first course at /upload.

## Notes

- Videos are saved in the `uploads/` folder. For a live website, use cloud
  storage (S3, Cloudflare R2, or Backblaze B2) instead, since most free hosts
  erase local files on restart.
- Search uses TF-IDF machine learning ranking over titles, tags, categories,
  and descriptions, with small boosts for popularity and freshness.
