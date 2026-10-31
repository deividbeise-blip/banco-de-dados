-- 01_papeis.sql
-- Papeis do experimento (nivel de cluster). NOLOGIN: os testes usam SET ROLE.
CREATE ROLE admin_bd  NOLOGIN;
CREATE ROLE gerente   NOLOGIN;
CREATE ROLE atendente NOLOGIN;
CREATE ROLE cliente   NOLOGIN;
