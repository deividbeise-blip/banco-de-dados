# Experimento: LLM como auditor de politicas de acesso (PostgreSQL + RLS)

## Estrutura
- sql/01_papeis.sql ........ papeis (admin_bd, gerente, atendente, cliente)
- sql/02_esquema.sql ....... tabelas e dados ficticios
- sql/03_privilegios.sql ... GRANTs
- sql/04_rls.sql ........... RLS e politicas CORRETAS
- sql/05_defeitos.sql ...... defeitos D1 a D6 (somente na instancia bd_defeitos)
- sql/06_extracao.sql ...... consultas ao catalogo (entrada do LLM)
- sql/07_provas.sql ........ prova de que cada defeito expoe dados
- gabarito_modelo.csv ...... gabarito dos defeitos D1 a D6
- docker-compose.yml ....... duas instancias: bd_controle (5433) e bd_defeitos (5434)
- extrator.py .............. gera os prompts e as listas de unidades em saida/
- rodar_claude_code.ps1 .... executa os prompts no Claude Code, isolado do repositorio
- importar_respostas.py .... converte as respostas de saida/brutas em JSON
- comparar.py .............. compara as respostas com o gabarito e calcula as metricas
- saida/brutas ............. respostas do LLM (5 por base)
- saida/respostas .......... respostas convertidas em JSON
- saida/*.csv .............. metricas por execucao, deteccao por defeito e falsos alertas
- saida/PROVENIENCIA.txt ... como as respostas foram geradas

## Como rodar
1. docker compose up -d
2. Provas (na instancia de controle):
   docker compose exec bd_controle psql -U postgres -d bd_controle -f /scripts/07_provas.sql
3. Extracao (em cada instancia):
   docker compose exec bd_controle psql -U postgres -d bd_controle -f /scripts/06_extracao.sql
   docker compose exec bd_defeitos psql -U postgres -d bd_defeitos -f /scripts/06_extracao.sql
   Para gerar os prompts e as unidades de analise em saida/:
   python extrator.py controle
   python extrator.py defeitos
4. Execucao do LLM (Windows, Claude Code instalado e logado):
   powershell -ExecutionPolicy Bypass -File .\rodar_claude_code.ps1
5. Conversao das respostas:
   python importar_respostas.py --modelo "Claude Opus 5.5" --interface "Claude Code (claude -p, pasta isolada, ferramentas desabilitadas)"
6. Comparacao com o gabarito e metricas:
   python comparar.py
7. Para recriar do zero: docker compose down && docker compose up -d
   (os scripts de inicializacao so rodam com a instancia vazia).

## Observacoes
- Papeis sao globais ao cluster; por isso sao DUAS instancias.
- Todos os dados sao ficticios. Nenhum dado real vai ao LLM: so metadados.
- As provas aplicam um defeito por vez na base de controle e dao ROLLBACK.
- O LLM roda em uma pasta vazia, sem ferramentas, para nao ler o gabarito
  (detalhes em saida/PROVENIENCIA.txt).
