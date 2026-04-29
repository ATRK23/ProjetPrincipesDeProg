from fastapi import FastAPI

from app.database import Base, engine
from app.models import User, Restaurant
from app.routers import user, restaurant

app = FastAPI(
    title="Restaurant API",
    description="API de gestion de restaurants, commandes, utilisateurs et livreurs",
    version="0.0.2"
)

Base.metadata.create_all(bind=engine)

app.include_router(user.router)
app.include_router(restaurant.router)


@app.get("/")
def read_root():
    return {"message": "API restaurant OK"}