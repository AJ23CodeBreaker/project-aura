"""
Project Aura — local development entry point.

Run the session bootstrap API with live reload:
    python main.py

Or equivalently:
    uvicorn app.api.session:app --reload --host 127.0.0.1 --port 8000
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.api.session:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )
