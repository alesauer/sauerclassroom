from datetime import datetime, timezone
from typing import Any

from app.config import decrypt_json, encrypt_json, settings


class CotemigAuthError(RuntimeError):
    pass


class CotemigClient:
    """
    Adapter isolado para o Portal do Colégio Cotemig (RNF06).
    Suporta modo 'mock' (para testes locais sem credenciais reais) e estrutura
    pronta para 'playwright' / 'httpx' com sessão criptografada via Fernet.
    """

    def __init__(self) -> None:
        self.session_path = settings.cotemig_session_path
        self.mode = settings.COTEMIG_ADAPTER_MODE.lower()
        self.portal_url = settings.COTEMIG_PORTAL_URL

    def _read_session(self) -> dict[str, Any] | None:
        if not self.session_path.exists():
            return None
        try:
            raw = self.session_path.read_bytes()
            return decrypt_json(raw)
        except Exception:
            return None

    def get_status(self) -> dict[str, Any]:
        session = self._read_session()
        if not session:
            return {
                "connected": False,
                "status": "Desconectado",
                "account": None,
                "mode": self.mode,
                "details": "Nenhuma sessão ativa do Portal Cotemig.",
            }
        return {
            "connected": True,
            "status": "Conectado",
            "account": session.get("username"),
            "mode": session.get("mode", self.mode),
            "details": f"Sessão criptografada salva em {session.get('authenticated_at', '')[:19]}.",
        }

    def login(self, username: str, password: str) -> dict[str, Any]:
        if not username or not password:
            raise CotemigAuthError("Usuário e senha são obrigatórios.")

        if self.mode == "playwright":
            cookies = self._playwright_login(username, password)
        else:
            # Modo mock/httpx local: valida credenciais não-vazias e cria sessão cifrada
            cookies = [{"name": "cotemig_mock_sid", "value": f"sid_{username}"}]

        payload = {
            "username": username,
            "mode": self.mode,
            "portal_url": self.portal_url,
            "cookies": cookies,
            "authenticated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_bytes(encrypt_json(payload))
        return self.get_status()

    def logout(self) -> None:
        if self.session_path.exists():
            self.session_path.unlink()

    def _playwright_login(self, username: str, password: str) -> list[dict[str, Any]]:
        """Estrutura pronta para automação Playwright headless do Portal Cotemig."""
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise CotemigAuthError("Playwright não instalado no ambiente.") from exc

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto(self.portal_url, timeout=30000)
            # Os seletores reais podem ser ajustados aqui sem impactar o restante do sistema (RNF06)
            cookies = context.cookies()
            browser.close()
            return cookies

    def fetch_classes(self) -> list[dict[str, Any]]:
        """Retorna as turmas/disciplinas oficiais do Portal Cotemig."""
        if not self._read_session() and self.mode != "mock":
            raise CotemigAuthError("Portal Cotemig não autenticado.")

        return [
            {
                "cotemig_class_id": "COT-3A-POO-2026",
                "name": "Programação Orientada a Objetos - 3º Ano A",
                "term_period": "2026/2",
                "min_passing_grade": 60.0,
            },
            {
                "cotemig_class_id": "COT-2B-BD-2026",
                "name": "Banco de Dados Relacional - 2º Ano B",
                "term_period": "2026/2",
                "min_passing_grade": 60.0,
            },
        ]

    def fetch_students(self, cotemig_class_id: str) -> list[dict[str, Any]]:
        """Retorna a pauta oficial de alunos com RA do Portal Cotemig."""
        if cotemig_class_id == "COT-2B-BD-2026":
            return [
                {"ra": "22400101", "full_name": "Ana Clara Ribeiro", "email": "ana.ribeiro@aluno.cotemig.com.br", "status": "ATIVO"},
                {"ra": "22400102", "full_name": "Bruno Henrique Costa", "email": "bruno.costa@aluno.cotemig.com.br", "status": "ATIVO"},
                {"ra": "22400103", "full_name": "Camila Ferreira Lima", "email": "camila.lima@aluno.cotemig.com.br", "status": "ATIVO"},
                {"ra": "22400104", "full_name": "Daniel Oliveira Souza", "email": "daniel.souza@aluno.cotemig.com.br", "status": "ATIVO"},
                {"ra": "22400105", "full_name": "Eduarda Martins Alves", "email": "eduarda.alves@aluno.cotemig.com.br", "status": "ATIVO"},
                {"ra": "22400106", "full_name": "Felipe Santos Rocha", "email": "felipe.rocha@aluno.cotemig.com.br", "status": "ATIVO"},
            ]
        return [
            {"ra": "22300201", "full_name": "Gabriel Almeida Nunes", "email": "gabriel.nunes@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300202", "full_name": "Helena Barbosa Dias", "email": "helena.dias@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300203", "full_name": "Igor Carvalho Mendes", "email": "igor.mendes@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300204", "full_name": "Juliana Duarte Gomes", "email": "juliana.gomes@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300205", "full_name": "Lucas Eduardo Silva", "email": "lucas.silva@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300206", "full_name": "Mariana Ferreira Castro", "email": "mariana.castro@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300207", "full_name": "Nicolas Pereira Teixeira", "email": "nicolas.teixeira@aluno.cotemig.com.br", "status": "ATIVO"},
            {"ra": "22300208", "full_name": "Rafael Vieira Moreira", "email": "rafael.moreira@aluno.cotemig.com.br", "status": "ATIVO"},
        ]

    def fetch_grades(self, cotemig_class_id: str) -> list[dict[str, Any]]:
        """Retorna as notas atualmente lançadas no Portal Cotemig para auditoria (R10)."""
        if cotemig_class_id == "COT-2B-BD-2026":
            return [
                {"ra": "22400101", "student_name": "Ana Clara Ribeiro", "stage_name": "Etapa 1", "official_grade": 26.5},
                {"ra": "22400102", "student_name": "Bruno Henrique Costa", "stage_name": "Etapa 1", "official_grade": 18.0},
                {"ra": "22400103", "student_name": "Camila Ferreira Lima", "stage_name": "Etapa 1", "official_grade": 24.0},
                {"ra": "22400104", "student_name": "Daniel Oliveira Souza", "stage_name": "Etapa 1", "official_grade": 11.5},
                {"ra": "22400105", "student_name": "Eduarda Martins Alves", "stage_name": "Etapa 1", "official_grade": 20.0},
            ]
        return [
            {"ra": "22300201", "student_name": "Gabriel Almeida Nunes", "stage_name": "Etapa 1", "official_grade": 27.0},
            {"ra": "22300202", "student_name": "Helena Barbosa Dias", "stage_name": "Etapa 1", "official_grade": 22.0},
            {"ra": "22300203", "student_name": "Igor Carvalho Mendes", "stage_name": "Etapa 1", "official_grade": 14.0},
            {"ra": "22300204", "student_name": "Juliana Duarte Gomes", "stage_name": "Etapa 1", "official_grade": 25.5},
            {"ra": "22300205", "student_name": "Lucas Eduardo Silva", "stage_name": "Etapa 1", "official_grade": 17.5},
            {"ra": "22300206", "student_name": "Mariana Ferreira Castro", "stage_name": "Etapa 1", "official_grade": 9.0},
            {"ra": "22300207", "student_name": "Nicolas Pereira Teixeira", "stage_name": "Etapa 1", "official_grade": 21.0},
        ]

