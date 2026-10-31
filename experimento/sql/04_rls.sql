-- 04_rls.sql
-- Row-Level Security (estado CORRETO, usado na base de controle).
-- A identidade do cliente vem do parametro de sessao app.cliente_id.
-- NULLIF(..., '') evita erro de conversao quando o parametro esta vazio.

ALTER TABLE clientes     ENABLE ROW LEVEL SECURITY;
ALTER TABLE pedidos      ENABLE ROW LEVEL SECURITY;
ALTER TABLE funcionarios ENABLE ROW LEVEL SECURITY;

-- clientes
CREATE POLICY clientes_equipe_sel ON clientes
  FOR SELECT TO atendente, gerente
  USING (true);

CREATE POLICY clientes_cliente_sel ON clientes
  FOR SELECT TO cliente
  USING (id = NULLIF(current_setting('app.cliente_id', true), '')::int);

-- pedidos (a equipe e limitada pelos privilegios; o cliente, pela linha)
CREATE POLICY pedidos_equipe ON pedidos
  FOR ALL TO atendente, gerente
  USING (true) WITH CHECK (true);

CREATE POLICY pedidos_cliente_sel ON pedidos
  FOR SELECT TO cliente
  USING (cliente_id = NULLIF(current_setting('app.cliente_id', true), '')::int);

CREATE POLICY pedidos_cliente_ins ON pedidos
  FOR INSERT TO cliente
  WITH CHECK (cliente_id = NULLIF(current_setting('app.cliente_id', true), '')::int);

-- funcionarios
CREATE POLICY funcionarios_gerente_sel ON funcionarios
  FOR SELECT TO gerente
  USING (true);
