from fastapi import FastAPI

from app.database import Base, engine
from app.models import User

app = FastAPI()

Base.metadata.create_all(bind=engine)


@app.get("/")
def read_root():
    return {"message": "API restaurant OK"}