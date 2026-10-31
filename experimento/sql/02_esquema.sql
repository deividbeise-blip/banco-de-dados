-- 02_esquema.sql
-- Esquema multiusuario simplificado. Todos os dados sao FICTICIOS.
CREATE TABLE clientes (
  id    serial PRIMARY KEY,
  nome  text NOT NULL,
  cpf   text NOT NULL,
  email text NOT NULL
);

CREATE TABLE pedidos (
  id         serial PRIMARY KEY,
  cliente_id integer NOT NULL REFERENCES clientes (id),
  descricao  text NOT NULL,
  valor      numeric(10,2) NOT NULL,
  criado_em  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE funcionarios (
  id      serial PRIMARY KEY,
  nome    text NOT NULL,
  cargo   text NOT NULL,
  salario numeric(10,2) NOT NULL
);

INSERT INTO clientes (nome, cpf, email) VALUES
  ('Cliente Um',   '000.000.000-01', 'cliente1@exemplo.com'),
  ('Cliente Dois', '000.000.000-02', 'cliente2@exemplo.com'),
  ('Cliente Tres', '000.000.000-03', 'cliente3@exemplo.com');

INSERT INTO pedidos (cliente_id, descricao, valor) VALUES
  (1, 'Pedido 1 do cliente 1', 100.00),
  (1, 'Pedido 2 do cliente 1', 150.00),
  (2, 'Pedido 1 do cliente 2', 200.00),
  (2, 'Pedido 2 do cliente 2', 250.00),
  (3, 'Pedido 1 do cliente 3', 300.00),
  (3, 'Pedido 2 do cliente 3', 350.00);

INSERT INTO funcionarios (nome, cargo, salario) VALUES
  ('Funcionario A', 'gerente',   9000.00),
  ('Funcionario B', 'atendente', 3000.00),
  ('Funcionario C', 'atendente', 3200.00);

-- O dono das tabelas (e das sequences ligadas a elas) passa a ser admin_bd.
ALTER TABLE clientes     OWNER TO admin_bd;
ALTER TABLE pedidos      OWNER TO admin_bd;
ALTER TABLE funcionarios OWNER TO admin_bd;
