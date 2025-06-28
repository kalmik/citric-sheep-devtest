import sqlmodel
from fastapi import Depends

from typing import Annotated
from src import db

def create_engine():
    sqlite_file_name = "database.db"
    sqlite_url = f"sqlite:///{sqlite_file_name}"
    return sqlmodel.create_engine(sqlite_url)


class Engine:
    __instance__ = None
    def __new__(cls):
        if cls.__instance__ is None:
            cls.__instance__ = create_engine()
        return cls.__instance__


def get_session():
    engine = Engine()
    with sqlmodel.Session(engine) as session:
        yield session


Session = Annotated[sqlmodel.Session, Depends(db.get_session)]