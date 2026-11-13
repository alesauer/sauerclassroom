from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth_router, reports_router, rules_router, sync_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SauerClassroom — Gestão Acadêmica & Notas",
    description="Integração local-first Google Classroom + Portal Cotemig com cálculo por temas e 18 relatórios.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(sync_router.router)
app.include_router(rules_router.router)
app.include_router(reports_router.router)


@app.get("/api/health", tags=["Sistema"])
def healthcheck():
    return {"status": "ok", "service": "sauerclassroom-backend"}

