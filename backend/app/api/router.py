from fastapi import APIRouter

from app.api.routes import customers, expense_categories, expenses, projects, time_entries

api_router = APIRouter(prefix="/api")
api_router.include_router(customers.router)
api_router.include_router(projects.router)
api_router.include_router(expense_categories.router)
api_router.include_router(time_entries.router)
api_router.include_router(expenses.router)
