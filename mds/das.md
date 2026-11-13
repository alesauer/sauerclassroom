# Documento de Arquitetura de Software (DAS)

**Projeto:** Sistema de Gestão Acadêmica e Cálculo de Notas (Google Classroom + Portal Cotemig)

**Stack Tecnológica:** React + Vite (Frontend) | Python + FastAPI (Backend) | SQLite (Banco de Dados Local) | Docker & Docker Compose

**Modelo de Implantação:** Local-First Containerizado (`localhost`)

## 1. Visão Geral da Arquitetura

O sistema adota uma arquitetura **Cliente-Servidor Local Containerizada** desacoplada em três camadas principais, orquestradas via **Docker Compose** na máquina do professor para garantir isolamento de dependências (como navegadores *headless* do Playwright), portabilidade e privacidade dos dados acadêmicos (LGPD):

1. **Camada de Apresentação (Container `frontend` — React + Vite):** Interface SPA responsiva servida em container próprio (servidor Vite em desenvolvimento ou Nginx em produção) para configuração de conexões, mapeamento de critérios de pontuação por temas, visualização analítica e exportação de relatórios.

2. **Camada de Aplicação e Integração (Container `backend` — Python + FastAPI):** API REST local responsável pela orquestração de sincronização com fontes externas (Google Classroom API e Portal Cotemig), execução do motor de cálculo de pontos e geração de relatórios.

3. **Camada de Persistência (Volumes Docker + SQLite):** Banco relacional leve em arquivo único (`academic_hub.db`) e tokens de sessão armazenados em volumes mapeados no host (`./data` e `./credentials`), garantindo que nenhum dado ou autenticação seja perdido ao reiniciar ou reconstruir os containers.

### Diagrama de Componentes e Containers

```
+-----------------------------------------------------------------------------+
|                        HOST LOCAL (Máquina do Professor)                    |
|                                                                             |
|  +-----------------------------------------------------------------------+  |
|  |                     DOCKER COMPOSE NETWORK (academic_net)             |  |
|  |                                                                       |  |
|  |  +-----------------------------------------------------------------+  |  |
|  |  |               CONTAINER: frontend (React + Vite)                |  |  |
|  |  |  Porta: 5173:5173                                               |  |  |
|  |  |  [Dashboard]  [Config. Temas/Pontos]  [Auditoria]  [Relatórios] |  |  |
|  |  +--------------------------------+--------------------------------+  |  |
|  |                                   | HTTP / REST (JSON)                |  |
|  |                                   | http://backend:8000               |  |
|  |  +--------------------------------v--------------------------------+  |  |
|  |  |               CONTAINER: backend (Python + FastAPI)             |  |  |
|  |  |  Porta: 8000:8000                                               |  |  |
|  |  |                                                                 |  |  |
|  |  |  +-----------------------+  +--------------------------------+  |  |  |
|  |  |  |   API Routers         |  |   Motor de Cálculo & Relatórios|  |  |  |
|  |  |  | (/auth, /sync, /calc) |  | (Pontuação Proporcional/Temas) |  |  |  |
|  |  |  +-----------+-----------+  +---------------+----------------+  |  |  |
|  |  |              |                              |                   |  |  |
|  |  |  +-----------v------------------------------v----------------+  |  |  |
|  |  |  |                Camada de Repositórios (SQLAlchemy)        |  |  |  |
|  |  |  +-----------+------------------------------+----------------+  |  |  |
|  |  |              |                              |                   |  |  |
|  |  |  +-----------v-----------+      +-----------v----------------+  |  |  |
|  |  |  | Connector: Classroom  |      | Connector: Portal Cotemig  |  |  |  |
|  |  |  | (Google API Client)   |      | (HTTPX / Playwright)       |  |  |  |
|  |  |  +-----------+-----------+      +-----------+----------------+  |  |  |
|  |  +--------------|------------------------------|-------------------+  |  |
|  +-----------------|------------------------------|----------------------+  |
|                    | Bind Mounts (Volumes)        | Saída Internet (HTTPS)  |
|          +---------v---------+          +---------v---------+               |
|          | ./data/           |          | APIs Externas     |               |
|          |  └academic_hub.db |          | Classroom/Cotemig |               |
|          | ./credentials/    |          +-------------------+               |
|          +-------------------+                                              |
+-----------------------------------------------------------------------------+
```

## 2. Estrutura de Diretórios do Projeto

```
sistema-academico/
├── docker-compose.yml               # Orquestração dos serviços frontend, backend e volumes
├── .env.example                     # Variáveis de ambiente (portas, chaves de criptografia)
├── .gitignore                       # Ignora /data, /credentials e .env
│
├── data/                            # Volume persistente montado no container backend
│   └── academic_hub.db              # Arquivo do banco SQLite
│
├── credentials/                     # Volume persistente de sessões (ignorado no Git)
│   ├── credentials.json             # Credencial OAuth Google Cloud
│   ├── token.json                   # Token de sessão renovável do Google
│   └── cotemig_session.json         # Cookies/tokens locais do portal
│
├── backend/
│   ├── Dockerfile                   # Imagem Python + dependências do Playwright/Chromium
│   ├── requirements.txt
│   └── app/
│       ├── main.py                  # Ponto de entrada FastAPI e configuração CORS
│       ├── database.py              # Conexão SQLite (/app/data/academic_hub.db)
│       ├── models/                  # Modelos ORM (Tabelas SQLite)
│       │   ├── academic.py          # Turmas, Alunos, Vínculos De/Para
│       │   ├── coursework.py        # Temas, Atividades, Entregas e Notas
│       │   └── rules.py             # Critérios de pontuação, tetos e arredondamento
│       ├── schemas/                 # Schemas Pydantic (Validação Request/Response)
│       ├── connectors/              # Adaptadores isolados para fontes externas
│       │   ├── classroom_client.py  # OAuth 2.0 e consumo da Google Classroom API
│       │   └── cotemig_client.py    # Autenticação e coleta de pautas/notas do Cotemig
│       ├── services/                # Regras de negócio
│       │   ├── sync_service.py      # Orquestração de sincronização e conciliação
│       │   ├── calc_engine.py       # Motor de cálculo proporcional e soma por temas
│       │   └── report_service.py    # Geração dos 18 relatórios (JSON, XLSX, CSV, PDF)
│       └── routers/                 # Endpoints REST
│           ├── auth_router.py
│           ├── sync_router.py
│           ├── rules_router.py
│           └── reports_router.py
│
└── frontend/
    ├── Dockerfile                   # Imagem Node.js (Vite dev server / build Nginx)
    ├── package.json
    ├── vite.config.ts               # Proxy configurado para http://backend:8000
    └── src/
        ├── api/                     # Cliente Axios configurado para API backend
        ├── components/              # Componentes reutilizáveis (Tabelas, Cards, Badges)
        ├── pages/
        │   ├── Connections.tsx      # Status e login Google Classroom + Cotemig
        │   ├── CourseMapping.tsx    # Vínculo De/Para de turmas e alunos
        │   ├── GradingRules.tsx     # Configuração de pontos por atividade e temas
        │   ├── Gradebook.tsx        # Grade interativa com soma por temas e alertas
        │   └── ReportsHub.tsx       # Central dos 18 relatórios (R01 a R18) e exportação
        ├── types/                   # Interfaces TypeScript
        └── App.tsx
```

## 3. Camada Docker e Orquestração (`docker-compose.yml`)

A containerização resolve o principal gargalo de ambiente local: a execução do navegador *headless* (Playwright/Chromium) necessário para coletar dados do Portal Cotemig, além de padronizar as versões do Python e Node.js.

### Especificação dos Serviços

* **`backend`:**
  * Baseado em `python:3.11-slim` com instalação automatizada das dependências de sistema do Chromium (`playwright install --with-deps chromium`).
  * Expõe a porta `8000` para o host e para a rede interna `academic_net`.
  * Utiliza `healthcheck` no endpoint `/api/health` para garantir que a API esteja pronta antes de liberar o frontend.
* **`frontend`:**
  * Baseado em `node:20-alpine`.
  * Depende da inicialização saudável do serviço `backend` (`depends_on: backend: condition: service_healthy`).
  * Configurado com proxy reverso no `vite.config.ts` encaminhando chamadas `/api` diretamente para `http://backend:8000` dentro da rede Docker.

### Exemplo de `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: academic_backend
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./credentials:/app/credentials
      - ./backend/app:/app/app # Hot-reload em desenvolvimento
    environment:
      - DATABASE_URL=sqlite:////app/data/academic_hub.db
      - CREDENTIALS_DIR=/app/credentials
      - SECRET_KEY=${SECRET_KEY:-local_dev_secret_key}
    networks:
      - academic_net
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 15s
      timeout: 5s
      retries: 3
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: academic_frontend
    ports:
      - "5173:5173"
    volumes:
      - ./frontend/src:/app/src # Hot-reload em desenvolvimento
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
    networks:
      - academic_net
    restart: unless-stopped

networks:
  academic_net:
    driver: bridge
```

## 4. Modelagem do Banco de Dados (SQLite)

O schema relacional foi projetado para desacoplar os dados brutos importados das plataformas externas das regras de avaliação configuradas pelo professor, permitindo recalcular notas instantaneamente sem precisar refazer requisições de rede.

```
+-----------------------+       +-----------------------+
|   courses_mapping     |       |    students_map       |
+-----------------------+       +-----------------------+
| id (PK)               |<--+   | id (PK)               |
| classroom_course_id   |   |   | course_map_id (FK)    |
| cotemig_class_id      |   +---| classroom_user_id     |
| name                  |   |   | cotemig_ra (Matrícula)|
| term_period           |   |   | full_name             |
| min_passing_grade     |   |   | email                 |
| last_sync_at          |   |   | status_cotemig        |
+-----------------------+   |   +-----------+-----------+
                            |               |
+-----------------------+   |               |
|        themes         |   |               |
+-----------------------+   |               |
| id (PK)               |   |               |
| course_map_id (FK)    |---+               |
| classroom_topic_id    |   |               |
| title                 |   |               |
| max_points_cap (Teto) |   |               |
| rounding_rule         |   |               |
+-----------+-----------+   |               |
            |               |               |
+-----------v-----------+   |   +-----------v-----------+
|      activities       |   |   |     submissions       |
+-----------------------+   |   +-----------------------+
| id (PK)               |   |   | id (PK)               |
| course_map_id (FK)    |---+   | activity_id (FK)      |
| theme_id (FK)         |<------| student_map_id (FK)   |
| classroom_work_id     |       | state (TURNED_IN...)  |
| title                 |       | is_late (Boolean)     |
| due_date              |       | assigned_grade        |
| classroom_max_points  |       | draft_grade           |
| custom_points_weight  |       | calculated_points     |
| include_in_calc       |       | updated_at            |
+-----------------------+       +-----------------------+
```

### Detalhamento das Tabelas Principais

* **`courses_mapping`**: Armazena o vínculo entre uma turma do Google Classroom e sua disciplina correspondente no Portal Cotemig, além da nota mínima de aprovação (`min_passing_grade`) usada pelo simulador (R05) e alertas de risco (R13).

* **`students_map`**: Consolida a lista de alunos, cruzando o `userId` do Google Classroom com o **RA (Matrícula)** do Cotemig. Permite identificar discrepâncias de matrícula (Relatório R11).

* **`themes`**: Representa os **Temas/Tópicos** (importados dos `topics` do Classroom ou criados manualmente). Armazena o **teto máximo de pontos do tema** (`max_points_cap`) e a regra de arredondamento (RF08.4).

* **`activities`**: Armazena cada atividade do Classroom. O campo `classroom_max_points` guarda o valor original da plataforma, enquanto `custom_points_weight` guarda quantos pontos aquela atividade realmente vale no critério do professor (RF08.1).

* **`submissions`**: Guarda o status de entrega (`NEW`, `CREATED`, `TURNED_IN`, `RETURNED`), atraso (`is_late`), notas brutas (`assigned_grade`, `draft_grade`) e o valor já convertido (`calculated_points`).

* **`cotemig_grades_snapshot`**: Tabela auxiliar que guarda a última nota oficial lida do Portal Cotemig para cada aluno/etapa, viabilizando o relatório de **Auditoria de Divergência de Notas (R10)**.

## 5. Fluxos Críticos do Sistema

### 5.1. Fluxo OAuth 2.0 do Google Classroom em Ambiente Docker

Como o backend roda dentro de um container Linux sem interface gráfica nativa, o fluxo de autenticação OAuth 2.0 segue o padrão **Web Redirect**:

1. O frontend solicita a URL de consentimento ao endpoint `GET /api/auth/google/url`.
2. O navegador do usuário abre a tela de login do Google e redireciona de volta para `http://localhost:8000/api/auth/google/callback`.
3. O container `backend` recebe o código de autorização, troca pelos tokens e persiste o arquivo no volume mapeado `/app/credentials/token.json`.

### 5.2. Fluxo de Sincronização e Conciliação (`sync_service.py`)

```
[Usuário clica "Sincronizar"]
       │
       ├──► 1. Classroom Connector:
       │       Busca Courses, Topics, Students, CourseWork e StudentSubmissions
       │       (tratando paginação nextPageToken).
       │
       ├──► 2. Cotemig Connector:
       │       Busca Pauta Oficial, RAs dos alunos e Notas já lançadas no portal.
       │
       ├──► 3. Engine de Conciliação (De/Para):
       │       Cruza alunos por E-mail Institucional -> RA -> Similaridade de Nome.
       │       Sinaliza alunos órfãos (só no Classroom ou só no Cotemig).
       │
       └──► 4. Upsert no SQLite (/app/data/academic_hub.db) + Disparo do Motor de Cálculo.
```

### 5.3. Lógica do Motor de Cálculo (`calc_engine.py`)

Para cada aluno $a$ e cada tema $T$, o cálculo segue a pipeline:

1. **Pontuação Proporcional da Atividade ($P_{ativ}$):**
   $$P_{ativ} = \left( \frac{\text{Nota Obtida no Classroom}}{\text{MaxPoints do Classroom}} \right) \times \text{Pontos Configurados no Sistema}$$
   *(Nota: O professor pode configurar se considera apenas `assignedGrade` ou também `draftGrade`).*

2. **Soma por Tema ($S_{tema}$):**
   $$S_{tema} = \sum_{i \in T} P_{ativ_i}$$

3. **Aplicação de Teto e Arredondamento do Tema ($F_{tema}$):**
   $$F_{tema} = \text{Arredondar}\left(\min(S_{tema}, \text{Teto}_{T})\right)$$

4. **Total Geral da Disciplina ($Total_{aluno}$):**
   $$Total_{aluno} = \sum_{T} F_{tema}$$

## 6. Design da API REST (Backend FastAPI)

| Método | Endpoint | Responsabilidade |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Endpoint de verificação de saúde usado pelo `healthcheck` do Docker. |
| `GET` | `/api/auth/status` | Retorna status de autenticação do Google Classroom e Portal Cotemig. |
| `GET` | `/api/auth/google/url` | Gera URL de autorização OAuth 2.0 para abertura no navegador do host. |
| `GET` | `/api/auth/google/callback` | Recebe o retorno do Google e grava `token.json` no volume `/credentials`. |
| `POST` | `/api/auth/cotemig/login` | Autentica no Portal Cotemig e salva sessão criptografada no volume. |
| `POST` | `/api/sync/course/{course_map_id}` | Executa sincronização completa de uma turma específica. |
| `GET` | `/api/courses/{id}/gradebook` | Retorna a matriz completa de alunos, temas, atividades e somas calculadas. |
| `PUT` | `/api/courses/{id}/rules` | Atualiza pesos em pontos das atividades, agrupamento de temas e tetos. |
| `GET` | `/api/reports/{report_code}` | Gera os dados estruturados de qualquer relatório (`R01` a `R18`). |
| `GET` | `/api/reports/{report_code}/export` | Exporta o relatório solicitado nos formatos `?format=xlsx|csv|pdf`. |

## 7. Estratégia de Isolamento do Portal Cotemig (RNF06)

Como portais acadêmicos institucionais não costumam oferecer API pública documentada, o conector `cotemig_client.py` será implementado seguindo o padrão **Adapter**:

* **Interface Padronizada:** Expõe métodos fixos (`fetch_classes()`, `fetch_students(class_id)`, `fetch_grades(class_id)`).
* **Implementação Desacoplada:** Internamente utiliza `httpx` (caso as requisições XHR/JSON do portal sejam mapeadas) ou `Playwright` (executando o Chromium já embutido na imagem Docker do backend em modo *headless*) para ler a tabela HTML do diário. Se o portal sofrer atualização visual, apenas esse arquivo precisa ser ajustado, sem impactar o banco SQLite, o motor de cálculo ou o frontend React.

## 8. Segurança e Execução Local (RNF03 e RNF04)

* **Isolamento de Rede e Portas:** Apenas as portas `5173` (Frontend) e `8000` (Backend) são mapeadas para `127.0.0.1` no host, impedindo acesso externo na rede local.
* **Criptografia de Sessão em Volume:** Como containers Linux minimalistas não possuem interface gráfica de cofre de senhas (`keyring`), as credenciais/cookies do Portal Cotemig salvos no volume `./credentials` são criptografados simetricamente com **Fernet (`cryptography`)** utilizando a chave `SECRET_KEY` definida no arquivo `.env` local.
* **Execução Única:** Toda a infraestrutura sobe e desce com um único comando:
  * Iniciar sistema: `docker compose up -d --build`
  * Encerrar sistema: `docker compose down`