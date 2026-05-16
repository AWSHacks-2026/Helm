from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get("/")
def root():
    return RedirectResponse(url="/docs")


@router.get("/health")
def health():
    return {"status": "ok", "service": "overlord"}
