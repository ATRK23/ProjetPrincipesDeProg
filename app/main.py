import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routers import user, restaurant, plat, command, livreur, auth


def get_cors_origins() -> list[str]:
    origins = os.getenv(
        "CORS_ORIGINS",
        "http://127.0.0.1:8000,http://localhost:8000,"
        "http://127.0.0.1:5500,http://localhost:5500,null",
    )
    return [origin.strip() for origin in origins.split(",") if origin.strip()]

app = FastAPI(
    title="Restaurant API",
    description="API de gestion de restaurants, commandes, utilisateurs et livreurs",
    version="0.0.4"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(restaurant.router)
app.include_router(plat.router)
app.include_router(command.router)
app.include_router(livreur.router)
app.include_router(auth.router)


@app.get("/")
def read_root():
    return {"message": "API restaurant OK"}


frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/frontend", StaticFiles(directory=frontend_dir, html=True), name="frontend")