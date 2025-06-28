import io
import csv
from src.models import Elevator, ElevatorDemand, ElevatorDemandHistory
from fastapi import APIRouter,  HTTPException
from fastapi.responses import StreamingResponse

from datetime import date, datetime
from pydantic import BaseModel

from sqlalchemy.exc import IntegrityError
from sqlmodel import select

from typing import List


from src.db import Session


router = APIRouter(
    prefix="/elevator"
)


class DemandParameters(BaseModel):
    level: int


class SteteParameters(BaseModel):
    level: int


class DatasetParameters(BaseModel):
    format: str = "csv"

class ElevatorParameters(BaseModel):
    min_level: int
    max_level: int


@router.post("/", status_code=201)
def create_elevator(params: ElevatorParameters, session: Session) -> Elevator:
    elevator = Elevator(
        min_level=params.min_level,
        max_level=params.max_level
    )
    session.add(elevator)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=400)
    finally:
        session.commit()
        session.refresh(elevator)
        return elevator


@router.put("/{elevator_id}", status_code=202)
async def call(elevator_id: int, params: DemandParameters, session: Session):
    """
        Provide the API to call the given elevator stores a ElevatorDemand,
        and the demand is unique for the given level, if there is a Intergrity
        Error it will returns 409 Conflict
    """
    elevator = session.get(Elevator, elevator_id)
    if not elevator:
        session.rollback()
        raise HTTPException(status_code=404, detail="Not found")
    
    if not (elevator.min_level <= params.level <= elevator.max_level):
        session.rollback()
        raise HTTPException(status_code=400, detail="Level overflow")

    now = datetime.now()
    demand = ElevatorDemand(
        elevator_id=elevator_id,
        timestamp=now.timestamp(),
        level=params.level
    )
    session.add(demand)
    try:
        session.flush()
    except IntegrityError:
        session.rollback()
        raise HTTPException(status_code=409, detail="Conflict, demaind already has been made")
    finally:
        session.commit()

    return "Accepted"


def create_history(demand: ElevatorDemand):
    dt = datetime.fromtimestamp(demand.timestamp)
    history = ElevatorDemandHistory(
        elevator_id=demand.elevator_id,
        week_day=dt.weekday(),
        hour=dt.hour,
        minute=dt.minute,
        second=dt.second,
        level=demand.level
    )
    return history


@router.post("/{elevator_id}/state")
async def set_state(elevator_id: int, params: SteteParameters, session: Session):
    """
        Provide the sufficient API to set the state, the main business logic 
        is whenever a elevetor reach the the level, check if there is an 
        open demand to that level, since demand has unique for level the 
        very first demand will be stored to that level it will be cleared when
        the elevator reach that level.

        For that purpose we don't need to store the state itself, just reacting
    """

    elevator = session.get(Elevator, elevator_id)
    if not elevator:
        raise HTTPException(status_code=404, detail="Not found")
    
    demand_stmt = select(ElevatorDemand)\
                   .where(ElevatorDemand.elevator_id == elevator.id)\
                   .where(ElevatorDemand.level == params.level)
    
    demand  = session.exec(demand_stmt).first()
    if not demand:
        session.rollback()
        return "Noop"
    
    history = create_history(demand)
    session.add(history)
    session.flush()
    session.delete(demand)
    session.commit()
    return "Accepted"
    

def format_dataset_csv(history: List[ElevatorDemandHistory]):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "elevator_id",
        "week_day",
        "hour",
        "minute",
        "second",
        "level"
    ])
    for h in history:
        row = [
            h.elevator_id,
            h.week_day,
            h.hour,
            h.minute,
            h.second,
            h.level,
        ]
        writer.writerow(row)
    
    output.seek(0)  # Rewind to the beginning of the stream

    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8')),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dataset.csv"}
    )

@router.get("/dataset.{format}")
async def get_dataset(format: str, session: Session):
    history_stmt = select(ElevatorDemandHistory)
    
    history = session.exec(history_stmt)
    if format == "csv":
        return format_dataset_csv(history)
    
    raise HTTPException(status_code=400, detail="Format Not suppoted")