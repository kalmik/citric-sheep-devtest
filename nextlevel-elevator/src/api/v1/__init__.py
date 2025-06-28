from fastapi import APIRouter

from . import elevator

router = APIRouter(
    prefix="/v1",
    responses={404: {"description": "Not found"}},
)

router.include_router(elevator.router)