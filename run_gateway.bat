@echo off
cd apps\api-gateway
set DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/enterprise_auth
set REDIS_URL=redis://127.0.0.1:6379/0
set DIFY_BASE_URL=http://127.0.0.1/v1
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
