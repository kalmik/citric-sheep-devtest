import os   
import pytest
from typing import List
from main import app
from src.models import Elevator, ElevatorDemand, ElevatorDemandHistory
from src import db
from src.db import Session, get_session

from sqlmodel import select, create_engine, SQLModel

from fastapi.testclient import TestClient

from datetime import datetime


@pytest.fixture()
def session():
    engine = create_engine(  
        "sqlite:///testing.db", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    with db.sqlmodel.Session(engine) as s:
        yield s

    os.remove("testing.db")
    
@pytest.fixture()
def client(session):
    def get_session_override():
        return session  

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()
    

@pytest.fixture()
def elevator(session):
    elevator = Elevator(
        id=1,
        min_level=1,
        max_level=10
    )
    session.add(elevator)
    session.commit()
    return elevator


@pytest.fixture()
def demands(session, elevator: Elevator) -> List[ElevatorDemand]:
    testdata = [
        (datetime(2001, 12, 12, 8, 1, 0), 1),
        (datetime(2001, 12, 12, 8, 15, 0), 7),
        (datetime(2001, 12, 12, 8, 18, 0), 9),
        (datetime(2001, 12, 12, 8, 24, 0), 6),
    ]
    demands = []
    for date, level in testdata:
        demands.append(
            ElevatorDemand(
                elevator_id=elevator.id,
                timestamp=date.timestamp(),
                level=level
            )
        )
    session.add_all(demands)
    session.commit()
    return demands

@pytest.fixture()
def demand_history(session, elevator: Elevator) -> List[ElevatorDemand]:
    testdata = [
        (datetime(2001, 12, 12, 8, 1, 0), 1),
        (datetime(2001, 12, 12, 8, 15, 0), 7),
        (datetime(2001, 12, 12, 8, 18, 0), 9),
        (datetime(2001, 12, 12, 8, 24, 0), 6),
    ]
    history = []
    for date, level in testdata:
        dt = date
        history.append(
            ElevatorDemandHistory(
                elevator_id=elevator.id,
                week_day=dt.weekday(),
                hour=dt.hour,
                minute=dt.minute,
                second=dt.second,
                level=level
            )
        )
        
    session.add_all(history)
    session.commit()
    return history

def test_create_elevator(client: TestClient):
    resp = client.post(f"/api/v1/elevator", json={"min_level": 1, "max_level": 10})
    assert resp.status_code == 201
    assert resp.json() == {
        'id': 1,
        "min_level": 1,
        "max_level": 10
    }

def test_call_elevator_not_found(client: TestClient, session: db.sqlmodel.Session):
    resp = client.put(f"/api/v1/elevator/1", json={"level": 1})
    assert resp.status_code == 404
    demand_stmt = select(ElevatorDemand).where(
        ElevatorDemand.elevator_id == 1  and
        ElevatorDemand.level == 1
    )
    demands  = session.exec(demand_stmt)
    assert len(list(demands)) == 0

def test_call_elevator(client: TestClient, session: db.sqlmodel.Session, elevator: Elevator):
    resp = client.put(f"/api/v1/elevator/{elevator.id}", json={"level": 1})
    assert resp.status_code == 202
    demand_stmt = select(ElevatorDemand).where(
        ElevatorDemand.elevator_id == elevator.id  and
        ElevatorDemand.level == 1
    )
    demands  = session.exec(demand_stmt)
    assert len(list(demands)) == 1

    resp = client.put(f"/api/v1/elevator/{elevator.id}", json={"level": 1})
    assert resp.status_code == 409
    
def test_call_elevator_overflow(client: TestClient, session: db.sqlmodel.Session, elevator: Elevator):
    resp = client.put(f"/api/v1/elevator/{elevator.id}", json={"level": elevator.min_level-1})
    assert resp.status_code == 400
    demand_stmt = select(ElevatorDemand).where(
        ElevatorDemand.elevator_id == elevator.id
    )
    demands  = session.exec(demand_stmt)
    assert len(list(demands)) == 0

    resp = client.put(f"/api/v1/elevator/{elevator.id}", json={"level": elevator.max_level+1})
    assert resp.status_code == 400
    demand_stmt = select(ElevatorDemand).where(
        ElevatorDemand.elevator_id == elevator.id
    )
    demands  = session.exec(demand_stmt)
    assert len(list(demands)) == 0

def test_set_state(
        client: TestClient, 
        session: db.sqlmodel.Session, 
        elevator: Elevator,
        demands: List[Elevator]
    ):
    resp = client.post(f"/api/v1/elevator/{elevator.id}/state", json={"level": 1})
    assert resp.status_code == 200

    demand_stmt = select(ElevatorDemand)\
                   .where(ElevatorDemand.elevator_id == elevator.id)\
                   .where(ElevatorDemand.level == 1)
    
    demands_for_level_1  = session.exec(demand_stmt).first()
    assert demands_for_level_1 is None

    history_stmt = select(ElevatorDemandHistory)\
                   .where(ElevatorDemandHistory.elevator_id == elevator.id)\
                   .where(ElevatorDemandHistory.level == 1)
    
    history = session.exec(history_stmt).first()
    expected_datetime = datetime(2001, 12, 12, 8, 1, 0)
    assert history.week_day == expected_datetime.weekday()
    assert history.hour == expected_datetime.hour
    assert history.minute == expected_datetime.minute
    assert history.second == expected_datetime.second


def test_get_dataset_csv(
        client: TestClient,
        demand_history: List[ElevatorDemandHistory]
):
    resp = client.get(f"/api/v1/elevator/dataset.csv")
    assert resp.status_code == 200

    assert resp.status_code == 200
    assert "Content-Disposition" in resp.headers
    assert "filename=dataset.csv" in resp.headers["Content-Disposition"]
    
    processed_content = resp.text.splitlines()
    expected_headers = "elevator_id,week_day,hour,minute,second,level"
    assert processed_content[0] == expected_headers
    for i, h in enumerate(demand_history):
        print(processed_content)
        row = [
            str(h.elevator_id),
            str(h.week_day),
            str(h.hour),
            str(h.minute),
            str(h.second),
            str(h.level),
        ]
        assert processed_content[i+1] == ",".join(row)