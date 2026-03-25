#!/usr/bin/env python
"""Start the signature detection service"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8001))
    host = "0.0.0.0" if os.environ.get("DEPLOYMENT_MODE") == "render" else "127.0.0.1"
    reload = os.environ.get("DEPLOYMENT_MODE") != "render"
    uvicorn.run("app.main:app", host=host, port=port, reload=reload)
