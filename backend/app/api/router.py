from fastapi import APIRouter

from app.api.routes import customers, projects

api_router = APIRouter(prefix="/api")
api_router.include_router(customers.router)
api_router.include_router(projects.router)
