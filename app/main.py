from fastapi import FastAPI

from app.routers import user, restaurant, plat, command, livreur, auth

app = FastAPI(
    title="Restaurant API",
    description="API de gestion de restaurants, commandes, utilisateurs et livreurs",
    version="0.0.4"
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