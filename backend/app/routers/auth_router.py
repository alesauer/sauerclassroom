from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse

from app.connectors.classroom_client import ClassroomClient, ClassroomNotConfiguredError
from app.connectors.cotemig_client import CotemigAuthError, CotemigClient
from app.schemas import AuthStatusResponse, CotemigLoginRequest

router = APIRouter(prefix="/api/auth", tags=["Autenticação"])


@router.get("/status", response_model=AuthStatusResponse)
def get_auth_status():
    classroom = ClassroomClient()
    cotemig = CotemigClient()
    return {
        "google_classroom": classroom.get_status(),
        "cotemig_portal": cotemig.get_status(),
    }


@router.get("/google/url")
def get_google_auth_url():
    classroom = ClassroomClient()
    try:
        url = classroom.get_authorization_url()
        return {"url": url}
    except ClassroomNotConfiguredError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/google/callback")
def google_oauth_callback(code: str | None = None, error: str | None = None):
    if error:
        return RedirectResponse(url=f"http://localhost:5173/connections?google_error={error}")
    if not code:
        raise HTTPException(status_code=400, detail="Código de autorização ausente.")
    classroom = ClassroomClient()
    try:
        classroom.exchange_code(code)
        return RedirectResponse(url="http://localhost:5173/connections?google_connected=1")
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/google/disconnect")
def disconnect_google():
    ClassroomClient().disconnect()
    return {"status": "disconnected"}


@router.post("/cotemig/login")
def login_cotemig(payload: CotemigLoginRequest):
    cotemig = CotemigClient()
    try:
        return cotemig.login(payload.username, payload.password)
    except CotemigAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/cotemig/logout")
def logout_cotemig():
    CotemigClient().logout()
    return {"status": "disconnected"}

