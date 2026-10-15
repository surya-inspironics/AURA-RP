import os
import sys

# Ensure current working directory and project root are in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
os.environ["PYTHONPATH"] = root_dir + os.pathsep + os.environ.get("PYTHONPATH", "")

import uvicorn

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "127.0.0.1")
    print(f"Starting AURA Enterprise Python Backend on http://{host}:{port}")
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=True, app_dir=root_dir)
