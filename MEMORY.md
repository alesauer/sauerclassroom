# MEMORY.md — Estado Persistente do Projeto SauerClassroom

**Última Atualização:** 2026-11-13  
**Repositório:** `https://github.com/alesauer/sauerclassroom.git` (branch `main`)

---

## 1. Estado Atual do Desenvolvimento

### Infraestrutura & Segurança
- [x] Estrutura de diretórios (`backend/`, `frontend/`, `data/`, `credentials/`).
- [x] `.gitignore` blindado contra vazamento de `.env`, `*.db`, `*.sqlite`, `credentials/`, `token.json`, `credentials.json`, `.venv/`, `node_modules/`, `dist/`.
- [x] `.env.example`, `docker-compose.yml` (portas vinculadas a `127.0.0.1:8000` e `127.0.0.1:5173`), `backend/Dockerfile` e `frontend/Dockerfile`.

### Requisitos Funcionais (RF01–RF14)
- [x] **RF01–RF03:** Autenticação Google Classroom (OAuth 2.0 Web Redirect + `token.json`) e Portal Cotemig (`CotemigClient` com sessão criptografada via Fernet em `credentials/cotemig_session.json`).
- [x] **RF04–RF07:** Importação de turmas, conciliação De/Para (e-mail -> RA -> similaridade de nome), coleta de atividades/entregas, sincronização manual/seletiva e `seed_demo_data` para testes imediatos.
- [x] **RF08–RF11:** Motor de cálculo (`calc_engine.py`) com peso customizável por atividade (`custom_points_weight`), agrupamento por temas (`themes`), teto máximo (`max_points_cap`), arredondamento (`decimal_1`, `half_point`, `integer`, `none`), suporte a `draftGrade` e classificação de risco (`APROVADO`, `ATENCAO`, `RISCO`).
- [x] **RF12–RF14:** Interface React + Vite + TypeScript com 6 telas (`Dashboard`, `Gradebook`, `GradingRules`, `ReportsHub`, `CourseMapping`, `Connections`) + 18 relatórios (`R01`–`R18`) com exportação real em `.xlsx`, `.csv` e `.pdf`.

### Catálogo de Relatórios (`R01`–`R18`)
- [x] `R01` Boletim Consolidado por Tema | `R02` Espelho por Atividade | `R03` Ranking e Distribuição | `R04` Comparativo por Tema | `R05` Simulador de Fechamento
- [x] `R06` Pendências por Aluno | `R07` Pontualidade e Atrasos | `R08` Taxa de Adesão | `R09` Evolução Temporal
- [x] `R10` Auditoria de Divergência de Notas | `R11` Auditoria Matrículas vs. Sala Virtual | `R12` Espelho Pronto para Lançamento
- [x] `R13` Lista Vermelha | `R14` Entregam mas Não Pontuam | `R15` Boa Nota mas Não Entregam
- [x] `R16` Fila de Correção Pendente | `R17` Notas em Rascunho | `R18` Panorama Geral Multi-Turmas

---

## 2. Decisões Técnicas Tomadas
- **Frontend UI:** React 18 + Vite 5 + TypeScript + Tailwind CSS v4 (`@tailwindcss/vite`), `lucide-react` para ícones e `recharts` para gráficos.
- **Backend:** FastAPI + SQLAlchemy 2.0 + SQLite (`./data/academic_hub.db`).
- **Exportação:** `openpyxl` para `.xlsx` estilizado, `csv` nativo (UTF-8 com BOM) para `.csv`, e `reportlab` (A4 paisagem) para `.pdf` (evitando dependências nativas pesadas de sistema).
- **Portal Cotemig (`RNF06`):** Isolado em `backend/app/connectors/cotemig_client.py` com modo `mock` padrão para testes locais e estrutura `playwright` pronta para produção.
- **Criptografia (`RNF03`):** Chave Fernet derivada via SHA-256 de `SECRET_KEY` para cifrar `cotemig_session.json`.

---

## 3. Endpoints REST Principais
- `GET /api/health`
- `GET /api/auth/status`, `GET /api/auth/google/url`, `GET /api/auth/google/callback`, `POST /api/auth/google/disconnect`
- `POST /api/auth/cotemig/login`, `POST /api/auth/cotemig/logout`
- `GET /api/courses`, `POST /api/courses/mapping`, `PUT /api/courses/{id}`
- `GET /api/courses/{id}/students`, `POST /api/courses/{id}/students/link`
- `GET /api/sync/courses/external`, `POST /api/sync/course/{id}`, `POST /api/sync/all`, `POST /api/sync/demo-seed`, `GET /api/sync/history`
- `GET /api/courses/{id}/gradebook`, `POST /api/courses/{id}/themes`, `PUT /api/courses/{id}/rules`
- `GET /api/reports/catalog`, `GET /api/reports/{code}`, `GET /api/reports/{code}/export?format=xlsx|csv|pdf`

---

## 4. Comandos de Execução

### Via Docker Compose (Recomendado em Produção Local)
```bash
cp .env.example .env
docker compose up -d --build
```

### Execução Local (Sem Docker)
- **Backend:**
  ```bash
  cd backend
  .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
  ```
- **Testes Backend:**
  ```bash
  cd backend
  .\.venv\Scripts\python.exe -m pytest -v
  ```
- **Frontend:**
  ```bash
  cd frontend
  npm run dev
  ```

---

## 5. Pendências e Próximos Passos
1. Inserir o arquivo `credentials.json` (OAuth 2.0 do Google Cloud) em `./credentials/` para autenticar com contas reais do Google Classroom.
2. Ajustar os seletores HTML/formulário de login e leitura de pauta em `backend/app/connectors/cotemig_client.py` (`_playwright_login`, `fetch_classes`, `fetch_students`, `fetch_grades`) para o portal real do Cotemig quando `COTEMIG_ADAPTER_MODE=playwright`.
3. Validar `docker compose up -d --build` em uma máquina com Docker Desktop / Engine instalado.

