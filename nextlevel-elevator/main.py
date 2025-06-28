from fastapi import FastAPI
from sqlmodel import SQLModel

from src import db
from src import api

app = FastAPI()


def create_db_and_tables():
    engine = db.Engine()
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup():
    # It's not the Ideal but since this project is only for didatical pourpose
    create_db_and_tables()


app.include_router(api.router)