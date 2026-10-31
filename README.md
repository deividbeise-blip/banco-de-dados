# Experimento: LLM como auditor de politicas de acesso (PostgreSQL + RLS)

## Estrutura
- sql/01_papeis.sql ........ papeis (admin_bd, gerente, atendente, cliente)
- sql/02_esquema.sql ....... tabelas e dados ficticios
- sql/03_privilegios.sql ... GRANTs
- sql/04_rls.sql ........... RLS e politicas CORRETAS
- sql/05_defeitos.sql ...... defeitos D1 a D6 (somente na instancia bd_defeitos)
- sql/06_extracao.sql ...... consultas ao catalogo (entrada do LLM)
- sql/07_provas.sql ........ prova de que cada defeito expoe dados
- gabarito_modelo.csv ...... modelo do gabarito (completar com todas as unidades)
- docker-compose.yml ....... duas instancias: bd_controle (5433) e bd_defeitos (5434)

## Como rodar
1. docker compose up -d
2. Provas (na instancia de controle):
   docker compose exec bd_controle psql -U postgres -d bd_controle -f /scripts/07_provas.sql
3. Extracao (em cada instancia):
   docker compose exec bd_controle psql -U postgres -d bd_controle -f /scripts/06_extracao.sql
   docker compose exec bd_defeitos psql -U postgres -d bd_defeitos -f /scripts/06_extracao.sql
4. Para recriar do zero: docker compose down && docker compose up -d
   (os scripts de inicializacao so rodam com a instancia vazia).

## Observacoes
- Papeis sao globais ao cluster; por isso sao DUAS instancias.
- Todos os dados sao ficticios. Nenhum dado real vai ao LLM: so metadados.
- As provas aplicam um defeito por vez na base de controle e dao ROLLBACK.
