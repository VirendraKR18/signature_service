@echo off
echo Starting Signature Detection Service...
call venv_signature\Scripts\activate.bat
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
