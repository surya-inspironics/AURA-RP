import uvicorn
import os

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Starting AURA Enterprise Python Backend on http://{host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True)
