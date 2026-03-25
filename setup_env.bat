@echo off
echo Creating virtual environment for signature detection service...
python -m venv venv_signature

echo Activating virtual environment...
call venv_signature\Scripts\activate.bat

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Setup complete! Virtual environment created at: venv_signature
echo.
echo To activate: venv_signature\Scripts\activate.bat
echo To run service: uvicorn app.main:app --host 0.0.0.0 --port 8001
