-- 03_privilegios.sql
-- Privilegios minimos por papel (GRANT). O dono (admin_bd) ja tem todos.
REVOKE ALL ON clientes, pedidos, funcionarios FROM PUBLIC;

GRANT USAGE ON SCHEMA public TO gerente, atendente, cliente;

-- gerente: consulta clientes, pedidos e funcionarios (inclusive salarios)
GRANT SELECT ON clientes, pedidos, funcionarios TO gerente;

-- atendente: consulta clientes e pedidos e cria pedidos; nao acessa salarios
GRANT SELECT ON clientes, pedidos TO atendente;
GRANT INSERT ON pedidos TO atendente;

-- cliente: consulta o proprio cadastro e consulta/cria os proprios pedidos
GRANT SELECT ON clientes TO cliente;
GRANT SELECT, INSERT ON pedidos TO cliente;

GRANT USAGE ON SEQUENCE pedidos_id_seq TO atendente, cliente;
