# SauerClassroom — Sistema de Gestão Acadêmica e Cálculo de Notas

Sistema **local-first** para integração entre **Google Classroom** e **Portal do Colégio Cotemig**, com motor de cálculo proporcional agrupado por temas/tópicos, auditoria de divergências e geração de **18 relatórios (`R01`–`R18`)** exportáveis em `.xlsx`, `.csv` e `.pdf`.

## Stack Tecnológica
- **Frontend:** React + Vite + TypeScript + Tailwind CSS v4 + Recharts (`http://localhost:5173`)
- **Backend:** Python 3.11+ + FastAPI + SQLAlchemy (`http://localhost:8000`)
- **Banco de Dados:** SQLite local (`./data/academic_hub.db`)
- **Containerização:** Docker & Docker Compose

## Início Rápido

### Com Docker Compose
```bash
cp .env.example .env
docker compose up -d --build
```

### Desenvolvimento Local
1. **Backend:**
   ```bash
   cd backend
   python -m venv .venv
   .\.venv\Scripts\pip install -r requirements.txt
   .\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
   ```
2. **Frontend:**
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
3. Acesse `http://localhost:5173` e clique em **Carregar Dados Demo** no Panorama Geral ou conecte suas credenciais reais na aba **Conexões**.

