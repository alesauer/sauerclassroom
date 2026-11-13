# Especificação de Requisitos de Software (ERS)
**Projeto:** Sistema de Gestão Acadêmica e Cálculo de Notas (Google Classroom + Portal Cotemig)  
**Stack Tecnológica:** React + Vite (Frontend) | Python (Backend API) | SQLite (Banco de Dados Local)

---

## 1. Visão Geral do Sistema
O sistema tem como objetivo integrar os dados de turmas, alunos, atividades e entregas do **Google Classroom** com os dados acadêmicos oficiais do **Portal do Colégio Cotemig**. A aplicação permitirá configurar regras personalizadas de pontuação por atividade e agrupamento por temas/tópicos, automatizando o cálculo de notas, a auditoria entre plataformas e a geração de relatórios gerenciais e pedagógicos.

---

## 2. Requisitos Funcionais (RF)

### 2.1. Autenticação e Conexão com Fontes de Dados
* **RF01 — Autenticação Google Classroom:** O sistema deve permitir conectar-se à conta do professor via fluxo OAuth 2.0, armazenando e renovando automaticamente os tokens de acesso (`token.json` / refresh token).
* **RF02 — Autenticação Portal Cotemig:** O sistema deve permitir o login no portal acadêmico do Colégio Cotemig (via credenciais de usuário ou sessão autenticada) para acesso às turmas, pautas e boletins institucionais.
* **RF03 — Gerenciamento de Conexões:** A interface deve exibir o status atual de conexão de ambas as plataformas (*Conectado*, *Expirado*, *Erro*) e permitir desconectar ou reautenticar a qualquer momento.

### 2.2. Sincronização e Armazenamento Local (SQLite)
* **RF04 — Importação de Disciplinas Correntes:** O sistema deve buscar e listar todas as turmas/disciplinas ativas do período letivo atual no Google Classroom e no Portal Cotemig.
* **RF05 — Vinculação (De/Para) de Turmas e Alunos:** O sistema deve permitir associar uma turma do Google Classroom à sua respectiva disciplina/turma no Portal Cotemig, conciliando os alunos (por e-mail institucional, matrícula ou nome).
* **RF06 — Coleta de Atividades e Entregas:** O sistema deve importar todas as atividades (`courseWork`) de cada disciplina, incluindo título, tópico/categoria, data de entrega, pontuação máxima (`maxPoints`), status da entrega por aluno (entregue, pendente, atrasada) e notas (`assignedGrade` e `draftGrade`).
* **RF07 — Sincronização Manual e Seletiva:** O usuário deve poder acionar a atualização de dados de todas as turmas ou de uma disciplina específica, persistindo o histórico e o carimbo de data/hora da última sincronização no banco SQLite.

### 2.3. Motor de Critérios e Cálculos
* **RF08 — Configuração de Critérios de Pontuação e Agrupamento por Temas:**
  * **RF08.1 — Atribuição de Pontos por Atividade:** O sistema deve permitir definir ou sobrescrever o valor em pontos de cada atividade importada do Classroom (ex: atribuir `2,0 pts` para a Atividade A e `3,5 pts` para a Atividade B, independentemente do `maxPoints` original configurado na plataforma).
  * **RF08.2 — Agrupamento por Temas (Tópicos):** O sistema deve ler automaticamente os Tópicos (`topics`) do Google Classroom — além de permitir criação/edição manual de temas no sistema — para agrupar as atividades (ex: *Tema 1: Lógica de Programação*, *Tema 2: Banco de Dados*, *Tema 3: Projeto Integrador*).
  * **RF08.3 — Cálculo Proporcional e Soma por Tema:** Para cada aluno, o sistema deve calcular a pontuação obtida em cada atividade (proporcional à nota tirada vs. valor configurado no sistema), somar os **pontos acumulados por tema** (ex: `8,5 / 10,0 pts` no Tema 1) e consolidar a **soma total de pontos da etapa/disciplina** (ex: `26,5 / 30,0 pts`).
  * **RF08.4 — Teto e Arredondamento por Tema:** O usuário deve poder configurar opcionalmente um teto máximo de pontos por tema (ex: o tema soma 12 pts em atividades, mas o teto contabilizado na etapa é 10 pts) e a regra de arredondamento (ex: 1 casa decimal, meio em meio ponto ou nota inteira).
* **RF09 — Agrupamento de Atividades:** O sistema deve permitir agrupar atividades importadas do Classroom em blocos avaliativos/temas para aplicar tetos e totalizações distintas.
* **RF10 — Cálculo Automático de Indicadores:** Com base nos critérios configurados, o sistema deve calcular automaticamente para cada aluno: nota parcial/final por tema, soma total de pontos obtidos vs. distribuídos, taxa de entrega (%), quantidade de pendências e entregas com atraso.
* **RF11 — Simulação e Alerta de Risco:** O sistema deve destacar visualmente alunos abaixo da média configurada ou com alto índice de atividades não entregues.

### 2.4. Visualização e Exportação
* **RF12 — Dashboard e Tabela Analítica (React):** O sistema deve exibir uma grade interativa por disciplina contendo alunos, notas por atividade/tema, status de entrega e os resultados calculados, com filtros por status (aprovado, em risco, pendente) e busca por aluno.
* **RF13 — Exportação de Relatórios:** O sistema deve permitir exportar os resultados consolidados e relatórios em formatos `.xlsx` (Excel), `.csv` e `.pdf`.
* **RF14 — Módulo de Relatórios Analíticos e Operacionais:** O sistema deve disponibilizar a geração dos relatórios detalhados na Seção 4 deste documento.

---

## 3. Requisitos Não Funcionais (RNF)

### 3.1. Arquitetura e Stack Tecnológica
* **RNF01 — Separação Frontend/Backend:** O frontend deve ser desenvolvido em **React com Vite** (SPA), comunicando-se via API REST local (ex: **FastAPI** ou **Flask** em Python) com o backend.
* **RNF02 — Persistência Local Leve:** Todos os dados sincronizados, configurações de critérios e vínculos devem ser armazenados em um banco de dados **SQLite** local, dispensando servidores externos de banco de dados.

### 3.2. Segurança e Privacidade
* **RNF03 — Proteção de Credenciais:** Tokens OAuth do Google e credenciais/cookies de sessão do Portal Cotemig devem ser armazenados exclusivamente no ambiente local do usuário, nunca expostos no código-fonte do frontend ou em repositórios públicos (`.gitignore`).
* **RNF04 — Conformidade com Dados Acadêmicos (LGPD):** Por lidar com nomes, matrículas e notas de alunos, o sistema deve operar em modo *local-first* (`localhost`), sem envio de dados de estudantes para servidores de terceiros.

### 3.3. Desempenho e Resiliência
* **RNF05 — Paginação e Rate Limiting:** O backend em Python deve tratar automaticamente a paginação da API do Google Classroom (`nextPageToken`) e aplicar intervalos/tentativas (`retry` com *backoff*) para evitar bloqueios por excesso de requisições tanto no Google quanto no Portal Cotemig.
* **RNF06 — Tolerância a Mudanças no Portal Cotemig:** O módulo de coleta do Portal Cotemig deve ser isolado em um serviço/adaptador próprio no backend Python para facilitar manutenção caso o layout ou estrutura interna do portal sofra alterações.
* **RNF07 — Tempo de Resposta da Interface:** Consultas, filtros e recálculos sobre dados já sincronizados no SQLite devem responder em **menos de 500 ms** na interface React.

### 3.4. Usabilidade
* **RNF08 — Feedback Visual de Sincronização:** Durante a busca de dados nas plataformas externas, a interface deve exibir indicadores de progresso claros (loaders/barras de status) sem bloquear a navegação.

---

## 4. Catálogo de Relatórios (Detalhamento do RF14)

### 4.1. Notas e Desempenho Acadêmico
| Código | Nome do Relatório | Descrição Funcional |
| :--- | :--- | :--- |
| **R01** | **Boletim Consolidado por Tema (Mapa de Pontos)** | Tabela por turma exibindo os alunos nas linhas e os **Temas/Tópicos** nas colunas, mostrando os pontos obtidos em cada tema, a soma total e o percentual de aproveitamento. |
| **R02** | **Espelho Detalhado por Atividade** | Matriz completa cruzando `Aluno x Atividade`, mostrando a nota original do Classroom, a pontuação convertida pela regra do sistema e o status de entrega. |
| **R03** | **Ranking e Distribuição de Notas** | Estatísticas da turma (maior nota, menor nota, média, mediana, desvio padrão) e histograma de faixas de pontuação (0–59%, 60–79%, 80–100%). |
| **R04** | **Desempenho Comparativo por Tema** | Gráfico e tabela comparando a média de aproveitamento da turma em cada tema para diagnóstico pedagógico de conteúdos com maior dificuldade. |
| **R05** | **Simulador de Fechamento** | Cálculo projetivo indicando quantos pontos cada aluno ainda precisa conquistar nas atividades restantes para atingir a média mínima do Cotemig. |

### 4.2. Engajamento, Entregas e Prazos
| Código | Nome do Relatório | Descrição Funcional |
| :--- | :--- | :--- |
| **R06** | **Pendências por Aluno (Lista de Cobrança)** | Lista individualizada mostrando quais atividades cada aluno deixou de entregar (`NEW` / `CREATED`). |
| **R07** | **Pontualidade e Atrasos** | Ranking de entregas fora do prazo (`late: true`), exibindo taxa de pontualidade por aluno e atividades com maior índice de atraso. |
| **R08** | **Taxa de Adesão por Atividade** | Relatório ordenado por atividade mostrando o percentual de entregas no prazo, com atraso, não entregues ou entregues sem anexo. |
| **R09** | **Evolução Temporal de Engajamento** | Linha do tempo ao longo do período letivo mostrando a variação semanal das taxas de entrega e desempenho da turma. |

### 4.3. Conciliação (Google Classroom vs. Portal Cotemig)
| Código | Nome do Relatório | Descrição Funcional |
| :--- | :--- | :--- |
| **R10** | **Auditoria de Divergência de Notas** | Compara a soma total calculada no sistema com a nota lançada no Portal Cotemig, destacando alunos com divergências. |
| **R11** | **Auditoria de Matrículas vs. Sala Virtual** | Cruzamento apontando alunos matriculados no Cotemig ausentes no Classroom e alunos no Classroom que não constam na pauta oficial. |
| **R12** | **Espelho Pronto para Lançamento** | Planilha formatada exatamente na ordem da pauta do Portal Cotemig para facilitar a digitação ou importação das notas finais. |

### 4.4. Alerta e Gestão de Risco
| Código | Nome do Relatório | Descrição Funcional |
| :--- | :--- | :--- |
| **R13** | **Lista Vermelha (Risco de Reprovação/Evasão)** | Filtra alunos que combinam baixo aproveitamento de pontos com sequência recente de atividades não entregues. |
| **R14** | **Entregam mas Não Pontuam** | Identifica alunos com alta taxa de entrega (`TURNED_IN`), mas notas baixas, sinalizando necessidade de reforço técnico/monitoria. |
| **R15** | **Boa Nota mas Não Entregam** | Identifica alunos com bom desempenho nas tarefas realizadas, mas alto índice de atividades em branco por desengajamento. |

### 4.5. Operacionais do Professor
| Código | Nome do Relatório | Descrição Funcional |
| :--- | :--- | :--- |
| **R16** | **Fila de Correção Pendente** | Lista consolidada de entregas (`TURNED_IN`) ainda sem nota atribuída (`assignedGrade == null`) em todas as turmas, ordenadas pelas mais antigas. |
| **R17** | **Notas em Rascunho (`draftGrade`)** | Lista de atividades já corrigidas no Classroom, mas ainda não devolvidas aos alunos. |
| **R18** | **Panorama Geral Multi-Turmas** | Visão executiva consolidando média geral, taxa de entrega e pendências de correção de todas as disciplinas correntes em uma única tela. |