import json
import time
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.config import settings

CLASSROOM_SCOPES = [
    "https://www.googleapis.com/auth/classroom.courses.readonly",
    "https://www.googleapis.com/auth/classroom.rosters.readonly",
    "https://www.googleapis.com/auth/classroom.coursework.students.readonly",
    "https://www.googleapis.com/auth/classroom.topics.readonly",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


class ClassroomNotConfiguredError(RuntimeError):
    pass


class ClassroomClient:
    """Conector isolado para Google Classroom API v1 com OAuth 2.0, paginação e retry."""

    def __init__(self) -> None:
        self.secrets_path = settings.google_client_secrets_path
        self.token_path = settings.google_token_path

    def has_client_secrets(self) -> bool:
        return self.secrets_path.exists()

    def get_credentials(self) -> Credentials | None:
        if not self.token_path.exists():
            return None
        try:
            creds = Credentials.from_authorized_user_file(str(self.token_path), CLASSROOM_SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                self.token_path.write_text(creds.to_json(), encoding="utf-8")
            return creds
        except Exception:
            return None

    def get_status(self) -> dict[str, Any]:
        if not self.has_client_secrets() and not self.token_path.exists():
            return {
                "connected": False,
                "status": "Desconectado",
                "account": None,
                "mode": "oauth2",
                "details": "Arquivo credentials.json não encontrado em /credentials. Use o Modo Demo ou adicione suas credenciais OAuth.",
            }
        creds = self.get_credentials()
        if not creds:
            return {
                "connected": False,
                "status": "Desconectado",
                "account": None,
                "mode": "oauth2",
                "details": "Pronto para autenticar via OAuth 2.0.",
            }
        if not creds.valid:
            return {
                "connected": False,
                "status": "Expirado",
                "account": None,
                "mode": "oauth2",
                "details": "Token expirado e sem refresh_token válido.",
            }
        account_email = None
        try:
            oauth2 = build("oauth2", "v2", credentials=creds, cache_discovery=False)
            info = oauth2.userinfo().get().execute()
            account_email = info.get("email")
        except Exception:
            account_email = "Conta Google Conectada"
        return {
            "connected": True,
            "status": "Conectado",
            "account": account_email,
            "mode": "oauth2",
            "details": "Sessão OAuth 2.0 ativa e renovável.",
        }

    def get_authorization_url(self) -> str:
        if not self.has_client_secrets():
            raise ClassroomNotConfiguredError(
                f"Arquivo OAuth não encontrado em {self.secrets_path}. Adicione credentials.json ou utilize o Modo Demo."
            )
        flow = Flow.from_client_secrets_file(
            str(self.secrets_path),
            scopes=CLASSROOM_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code(self, code: str) -> dict[str, Any]:
        if not self.has_client_secrets():
            raise ClassroomNotConfiguredError("Arquivo credentials.json não encontrado.")
        flow = Flow.from_client_secrets_file(
            str(self.secrets_path),
            scopes=CLASSROOM_SCOPES,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
        )
        flow.fetch_token(code=code)
        creds = flow.credentials
        self.token_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_path.write_text(creds.to_json(), encoding="utf-8")
        return self.get_status()

    def disconnect(self) -> None:
        if self.token_path.exists():
            self.token_path.unlink()

    def _build_service(self):
        creds = self.get_credentials()
        if not creds or not creds.valid:
            raise ClassroomNotConfiguredError("Google Classroom não autenticado.")
        return build("classroom", "v1", credentials=creds, cache_discovery=False)

    @staticmethod
    def _execute_with_retry(request_fn, max_retries: int = 4) -> dict[str, Any]:
        delay = 1.0
        for attempt in range(max_retries):
            try:
                return request_fn()
            except HttpError as exc:
                status = getattr(exc.resp, "status", 500)
                if status in (429, 500, 502, 503, 504) and attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        return {}

    def _paginate(self, list_fn, result_key: str, **kwargs) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page_token: str | None = None
        while True:
            params = dict(kwargs)
            if page_token:
                params["pageToken"] = page_token
            resp = self._execute_with_retry(lambda: list_fn(**params).execute())
            items.extend(resp.get(result_key, []))
            page_token = resp.get("nextPageToken")
            if not page_token:
                break
        return items

    def fetch_courses(self) -> list[dict[str, Any]]:
        service = self._build_service()
        return self._paginate(service.courses().list, "courses", courseStates=["ACTIVE"])

    def fetch_topics(self, course_id: str) -> list[dict[str, Any]]:
        service = self._build_service()
        return self._paginate(service.courses().topics().list, "topic", courseId=course_id)

    def fetch_students(self, course_id: str) -> list[dict[str, Any]]:
        service = self._build_service()
        return self._paginate(service.courses().students().list, "students", courseId=course_id)

    def fetch_coursework(self, course_id: str) -> list[dict[str, Any]]:
        service = self._build_service()
        return self._paginate(
            service.courses().courseWork().list,
            "courseWork",
            courseId=course_id,
            courseWorkStates=["PUBLISHED"],
        )

    def fetch_submissions(self, course_id: str, coursework_id: str) -> list[dict[str, Any]]:
        service = self._build_service()
        return self._paginate(
            service.courses().courseWork().studentSubmissions().list,
            "studentSubmissions",
            courseId=course_id,
            courseWorkId=coursework_id,
        )

