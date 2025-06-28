import enum
from typing import Annotated, Union

from sqlmodel import Field, SQLModel, UniqueConstraint

MAX_LEVEL = 10
MIN_LEVEL = 1


class WeekDay(enum.IntEnum):
    MONDAY = 0
    TUESDAY = 1
    WEDNESDAY = 2
    THURSDAY = 3
    FRIDAY = 4
    SATURDAY = 5
    SUNDAY = 6


class Elevator(SQLModel, table=True):
    id: int = Field(primary_key=True)
    min_level: int = Field(),
    max_level: int = Field()


class ElevatorDemand(SQLModel, table=True):
    __table_args__ = (
        UniqueConstraint(
            "elevator_id",
            "level",
            name="uniq_elevator_id_timestamp_level"
        ),
    )
    id: int = Field(primary_key=True)
    elevator_id: int = Field(foreign_key="elevator.id")
    timestamp: int = Field()
    level: int = Field()


class ElevatorDemandHistory(SQLModel, table=True):
    """
        Storing the demand that was completelly attended by the Elevator
        and splitting the timestamp into week_day, hour, minute and second 
        for the given demand, so it will be more easy to group demand by any 
        time heuristics with second precision.
    """
    id: int = Field(primary_key=True)
    elevator_id: int = Field(foreign_key="elevator.id")
    week_day: int = Field()
    hour: int = Field()
    minute: int = Field()
    second: int = Field()
    level: int = Field()