-- 05_defeitos.sql
-- Defeitos D1 a D6. Executar SOMENTE na instancia bd_defeitos.
-- Cada defeito e uma unica alteracao sobre o estado correto.

-- D1: RLS desabilitado em tabela com dados pessoais (CPF, e-mail)
ALTER TABLE clientes DISABLE ROW LEVEL SECURITY;

-- D2: politica de leitura sem filtro por usuario (condicao sempre verdadeira)
ALTER POLICY pedidos_cliente_sel ON pedidos USING (true);

-- D3: privilegio excessivo a papel de baixo privilegio (atendente apaga pedidos)
GRANT DELETE ON pedidos TO atendente;

-- D4: politica de insercao sem verificacao (cliente grava em nome de outro)
ALTER POLICY pedidos_cliente_ins ON pedidos WITH CHECK (true);

-- D5: papel com atributo que contorna o RLS sem necessidade
ALTER ROLE cliente BYPASSRLS;

-- D6: heranca indevida de papel administrativo
GRANT admin_bd TO atendente;
