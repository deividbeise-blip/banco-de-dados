-- 06_extracao.sql
-- Consultas ao CATALOGO (somente metadados, nenhum dado das tabelas).
-- Executar em qualquer das duas instancias. A ordem abaixo e a ordem
-- fixa do texto enviado ao LLM.

-- 1) Tabelas e colunas
SELECT c.relname AS tabela, a.attname AS coluna,
       format_type(a.atttypid, a.atttypmod) AS tipo,
       pg_get_userbyid(c.relowner) AS dono
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY c.relname, a.attnum;

-- 2) Papeis e atributos
SELECT rolname AS papel, rolsuper, rolbypassrls, rolinherit, rolcanlogin
FROM pg_roles
WHERE rolname NOT LIKE 'pg\_%' AND rolname <> 'postgres'
ORDER BY rolname;

-- 3) Heranca entre papeis (quem e membro de quem)
SELECT pg_get_userbyid(m.member) AS membro,
       pg_get_userbyid(m.roleid) AS papel_concedido,
       m.inherit_option AS herda_privilegios
FROM pg_auth_members m
WHERE pg_get_userbyid(m.member)
        IN ('admin_bd','gerente','atendente','cliente')
  AND pg_get_userbyid(m.roleid)
        IN ('admin_bd','gerente','atendente','cliente')
ORDER BY 1, 2;

-- 4) Privilegios de tabela concedidos (exclui o proprio dono)
SELECT c.relname AS tabela,
       CASE WHEN a.grantee = 0 THEN 'PUBLIC'
            ELSE pg_get_userbyid(a.grantee) END AS papel,
       string_agg(a.privilege_type, ', ' ORDER BY a.privilege_type) AS privilegios
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace,
     LATERAL aclexplode(c.relacl) a
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND a.grantee <> c.relowner
GROUP BY c.relname, a.grantee
ORDER BY c.relname, papel;

-- 5) Estado do RLS por tabela
SELECT c.relname AS tabela,
       c.relrowsecurity      AS rls_habilitado,
       c.relforcerowsecurity AS rls_forcado
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname;

-- 6) Politicas RLS
SELECT tablename AS tabela, policyname AS politica, permissive AS tipo,
       roles, cmd AS comando, qual AS using_expr, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
