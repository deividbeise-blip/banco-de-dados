-- 07_provas.sql
-- PROVA de cada defeito. Executar na instancia bd_controle (superusuario).
-- Cada bloco: mostra o comportamento CORRETO (antes), aplica UM defeito,
-- mostra a EXPOSICAO (depois) e desfaz tudo com ROLLBACK.
-- Dados: cliente 1 tem 2 pedidos; ha 6 pedidos, 3 clientes e 3 funcionarios.

\echo '=== D1: RLS desabilitado em clientes ==='
BEGIN;
SET LOCAL ROLE cliente;
SELECT set_config('app.cliente_id', '1', true);
\echo 'ANTES (esperado: 1)'
SELECT count(*) AS clientes_visiveis FROM clientes;
RESET ROLE;
ALTER TABLE clientes DISABLE ROW LEVEL SECURITY;
SET LOCAL ROLE cliente;
\echo 'DEPOIS (defeito: 3)'
SELECT count(*) AS clientes_visiveis FROM clientes;
ROLLBACK;

\echo '=== D2: pedidos_cliente_sel com USING (true) ==='
BEGIN;
SET LOCAL ROLE cliente;
SELECT set_config('app.cliente_id', '1', true);
\echo 'ANTES (esperado: 2)'
SELECT count(*) AS pedidos_visiveis FROM pedidos;
RESET ROLE;
ALTER POLICY pedidos_cliente_sel ON pedidos USING (true);
SET LOCAL ROLE cliente;
\echo 'DEPOIS (defeito: 6)'
SELECT count(*) AS pedidos_visiveis FROM pedidos;
ROLLBACK;

\echo '=== D3: atendente com DELETE em pedidos ==='
BEGIN;
SET LOCAL ROLE atendente;
SAVEPOINT antes;
\echo 'ANTES (esperado: ERROR permission denied)'
DELETE FROM pedidos WHERE id = 1;
ROLLBACK TO antes;
RESET ROLE;
GRANT DELETE ON pedidos TO atendente;
SET LOCAL ROLE atendente;
\echo 'DEPOIS (defeito: DELETE 1)'
DELETE FROM pedidos WHERE id = 1;
ROLLBACK;

\echo '=== D4: pedidos_cliente_ins com WITH CHECK (true) ==='
BEGIN;
SET LOCAL ROLE cliente;
SELECT set_config('app.cliente_id', '1', true);
SAVEPOINT antes;
\echo 'ANTES (esperado: ERROR violates row-level security policy)'
INSERT INTO pedidos (cliente_id, descricao, valor) VALUES (2, 'teste D4', 1.00);
ROLLBACK TO antes;
RESET ROLE;
ALTER POLICY pedidos_cliente_ins ON pedidos WITH CHECK (true);
SET LOCAL ROLE cliente;
\echo 'DEPOIS (defeito: INSERT 0 1)'
INSERT INTO pedidos (cliente_id, descricao, valor) VALUES (2, 'teste D4', 1.00);
ROLLBACK;

\echo '=== D5: cliente com BYPASSRLS ==='
BEGIN;
SET LOCAL ROLE cliente;
SELECT set_config('app.cliente_id', '1', true);
\echo 'ANTES (esperado: 2)'
SELECT count(*) AS pedidos_visiveis FROM pedidos;
RESET ROLE;
ALTER ROLE cliente BYPASSRLS;
SET LOCAL ROLE cliente;
\echo 'DEPOIS (defeito: 6)'
SELECT count(*) AS pedidos_visiveis FROM pedidos;
ROLLBACK;

\echo '=== D6: atendente herda admin_bd ==='
BEGIN;
SET LOCAL ROLE atendente;
SAVEPOINT antes;
\echo 'ANTES (esperado: ERROR permission denied)'
SELECT count(*) AS salarios_visiveis FROM funcionarios;
ROLLBACK TO antes;
RESET ROLE;
GRANT admin_bd TO atendente;
SET LOCAL ROLE atendente;
\echo 'DEPOIS (defeito: 3)'
SELECT count(*) AS salarios_visiveis FROM funcionarios;
ROLLBACK;
