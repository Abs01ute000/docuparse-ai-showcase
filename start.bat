@echo off
if not exist .venv python -m venv .venv
call .venv\Scriptsctivate
pip install -r requirements.txt
if not exist .env copy .env.example .env
uvicorn app.main:app --reload
