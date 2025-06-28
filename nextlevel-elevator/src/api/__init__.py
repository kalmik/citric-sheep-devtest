from fastapi import APIRouter

from . import v1

router = APIRouter(
    prefix="/api",
    responses={404: {"description": "Not found"}},
)

router.include_router(v1.router)
