from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers.data_agent import router as data_agent_router
from app.routers.database_status import router as database_status_router
from app.routers.chat import router as chat_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.routers.patients import router as patients_router

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Synthetic healthcare operations and research API.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(data_agent_router)
app.include_router(database_status_router)
app.include_router(patients_router)
app.include_router(documents_router)
app.include_router(chat_router)
