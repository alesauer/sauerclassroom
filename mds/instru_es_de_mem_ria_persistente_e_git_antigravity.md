# Diretrizes de Contexto, Memória Persistente e Fluxo Git (Antigravity)

Este arquivo contém as instruções obrigatórias para o agente de IA (**Antigravity**) manter continuidade total do desenvolvimento deste projeto, independentemente da máquina, diretório ou sessão em que o workspace for aberto.

---

## 1. Repositório Oficial e Sincronização Contínua

* **Repositório GitHub:** `https://github.com/alesauer/sauerclassroom.git`
* **Branch Principal:** `main`

### Regra de Ouro de Versionamento (Git)
1. **Ao Iniciar Qualquer Sessão:**
   * Antes de editar qualquer arquivo, verifique o status do repositório e baixe as atualizações mais recentes:
     ```bash
     git status
     git pull origin main --rebase
     ```
   * Leia o arquivo `MEMORY.md` (se existir) e os documentos `especificacao_requisitos.md` e `arquitetura_sistema.md` para restaurar o estado atual do projeto.
2. **Ao Finalizar Qualquer Tarefa ou Alteração Relevante:**
   * **Sempre** envie as alterações para o repositório remoto (`https://github.com/alesauer/sauerclassroom.git`) para garantir que qualquer outro computador tenha acesso imediato ao código atualizado:
     ```bash
     git add .
     git commit -m "tipo(escopo): descrição clara do que foi feito"
     git push origin main
     ```
3. **Configuração Automática do Remote (caso seja um clone novo):**
   * Se o remote `origin` não estiver configurado, execute:
     ```bash
     git remote add origin https://github.com/alesauer/sauerclassroom.git
     ```

---

## 2. Protocolo de Memória Persistente Entre Sessões

Como sessões abertas em outros locais não compartilham cache local volátil da IDE, **toda a memória do projeto deve ser versionada no próprio repositório** através do arquivo `MEMORY.md` na raiz do projeto.

### O que o Agente deve manter atualizado em `MEMORY.md`:
* **Estado Atual do Desenvolvimento:** Checklist das funcionalidades concluídas, em andamento e pendentes (baseado nos RFs e Relatórios R01–R18).
* **Decisões Técnicas Tomadas:** Alterações no schema SQLite, ajustes nos seletores/endpoints do Portal Cotemig ou bibliotecas adicionadas.
* **Pendências e Próximos Passos:** Exatamente onde a última sessão parou, para retomada imediata em outro local.

> **Instrução para o Agente:** Sempre que concluir uma feature, corrigir um bug ou alterar a arquitetura, atualize o `MEMORY.md` **antes** de executar o `git push`.

---

## 3. Resumo da Arquitetura e Regras de Negócio (Contexto Fixo)

* **Objetivo:** Sistema local-first para integrar **Google Classroom** + **Portal do Colégio Cotemig**, calcular notas por atividade agrupadas por temas e gerar 18 relatórios gerenciais/pedagógicos.
* **Stack Obrigatória:**
  * **Frontend:** React + Vite + TypeScript (Porta `5173`)
  * **Backend:** Python 3.11 + FastAPI (Porta `8000`)
  * **Banco de Dados:** SQLite (`./data/academic_hub.db`)
  * **Infraestrutura:** Docker e Docker Compose (`docker-compose.yml`)
* **Regra de Cálculo Principal (RF08):**
  * Cada atividade possui um peso em pontos customizável (`custom_points_weight`), independente do `maxPoints` original do Classroom.
  * Nota proporcional da atividade: $P_{ativ} = (\text{Nota Classroom} / \text{MaxPoints Classroom}) \times \text{Pontos Configurados}$.
  * Soma-se os pontos por **Tema/Tópico** (aplicando teto máximo `max_points_cap` e arredondamento configuráveis) e consolida-se o total geral do aluno.

---

## 4. Segurança Crítica (NUNCA COMMITAR)

Antes de qualquer `git add` ou `git push`, o agente **DEVE** verificar o `.gitignore` para garantir que dados sensíveis e arquivos locais de alunos (LGPD) **jamais** subam para o GitHub:

```gitignore
# Credenciais e Sessões (NUNCA VERSIONAR)
credentials/
*.json
!package.json
!tsconfig.json
.env

# Banco de Dados Local (Contém dados de alunos - LGPD)
data/
*.db
*.sqlite
*.sqlite3

# Dependências e Builds
node_modules/
__pycache__/
.venv/
dist/
```