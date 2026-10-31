"""
extrator.py - le o CATALOGO do PostgreSQL (somente metadados) e gera:
  saida/extracao_<instancia>.txt   texto das 4 secoes enviado ao LLM
  saida/prompt_<instancia>.txt     prompt padronizado completo
  saida/unidades_<instancia>.csv   unidades de analise (para o gabarito)

Uso (na pasta do docker-compose.yml, com os containers rodando):
  python extrator.py controle
  python extrator.py defeitos
Requer apenas Python 3 e o Docker. Sem bibliotecas externas.
"""
import csv
import io
import pathlib
import subprocess
import sys

INSTANCIAS = {
    "controle": ("bd_controle", "bd_controle"),   # (servico, banco)
    "defeitos": ("bd_defeitos", "bd_defeitos"),
}

# Defeitos injetados (chave da unidade -> id). Usado SO para preencher a
# coluna "defeito" do CSV de unidades da instancia "defeitos".
DEFEITOS = {
    "rls:clientes": "D1",
    "politica:pedidos.pedidos_cliente_sel": "D2",
    "privilegio:atendente@pedidos": "D3",
    "politica:pedidos.pedidos_cliente_ins": "D4",
    "papel:cliente": "D5",
    "heranca:atendente->admin_bd": "D6",
}

PAPEIS = "'admin_bd','gerente','atendente','cliente'"

SQL = {
    "colunas": r"""
SELECT c.relname AS tabela, a.attname AS coluna,
       format_type(a.atttypid, a.atttypmod) AS tipo,
       pg_get_userbyid(c.relowner) AS dono
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid
WHERE n.nspname = 'public' AND c.relkind = 'r'
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY c.relname, a.attnum""",
    "papeis": r"""
SELECT rolname AS papel, rolsuper, rolbypassrls, rolinherit, rolcanlogin
FROM pg_roles
WHERE rolname NOT LIKE 'pg\_%' AND rolname <> 'postgres'
ORDER BY rolname""",
    "heranca": f"""
SELECT pg_get_userbyid(m.member) AS membro,
       pg_get_userbyid(m.roleid) AS papel_concedido,
       m.inherit_option AS herda_privilegios
FROM pg_auth_members m
WHERE pg_get_userbyid(m.member) IN ({PAPEIS})
  AND pg_get_userbyid(m.roleid) IN ({PAPEIS})
ORDER BY 1, 2""",
    "privilegios": r"""
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
ORDER BY c.relname, papel""",
    "rls": r"""
SELECT c.relname AS tabela,
       c.relrowsecurity AS rls_habilitado,
       c.relforcerowsecurity AS rls_forcado
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = 'public' AND c.relkind = 'r'
ORDER BY c.relname""",
    "politicas": r"""
SELECT tablename AS tabela, policyname AS politica, permissive AS tipo,
       roles, cmd AS comando, qual AS using_expr, with_check
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname""",
}

MODELO_PROMPT = """Você é um auditor de segurança de bancos de dados PostgreSQL.
A seguir estão o esquema (sem dados), os papéis e privilégios, o estado do RLS, as políticas RLS e os requisitos de acesso.
Identifique violações dos requisitos de acesso ou falhas de segurança.
Para cada problema encontrado, informe: tabela, objeto, descrição, risco, justificativa passo a passo e correção em SQL.
No campo "objeto", use exatamente um destes formatos: politica:tabela.nome_da_politica, privilegio:papel@tabela, rls:tabela, papel:nome_do_papel, heranca:membro->papel_concedido.
Se não houver problema, responda "nenhum problema encontrado".
Não cite objetos que não aparecem nas definições.
Responda somente em JSON: uma lista de objetos com os campos tabela, objeto, descricao, risco, justificativa e correcao_sql.

{secoes}

## REQUISITOS DE ACESSO
{requisitos}
"""


def rodar(servico, banco, sql):
    """Executa uma consulta no catalogo via psql e devolve lista de dicts."""
    cmd = ["docker", "compose", "exec", "-T", servico, "psql", "-X", "--csv",
           "-U", "postgres", "-d", banco, "-c", sql]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit("Erro ao consultar o catalogo:\n" + r.stderr)
    return list(csv.DictReader(io.StringIO(r.stdout)))


def sn(v):
    return "sim" if v == "t" else "nao"


def vazio(v):
    return v if v not in (None, "") else "(nenhum)"


def montar(dados):
    """Recebe as linhas de cada consulta e devolve (texto, unidades)."""
    unidades = []
    linhas = []

    linhas.append("## ESQUEMA (sem dados)")
    por_tabela = {}
    dono = {}
    for r in dados["colunas"]:
        por_tabela.setdefault(r["tabela"], []).append(f'{r["coluna"]} {r["tipo"]}')
        dono[r["tabela"]] = r["dono"]
    for t, cols in por_tabela.items():
        linhas.append(f"Tabela {t} (dono: {dono[t]}): " + ", ".join(cols))

    linhas.append("")
    linhas.append("## PAPEIS E PRIVILEGIOS")
    for r in dados["papeis"]:
        linhas.append(
            f'Papel {r["papel"]}: superusuario={sn(r["rolsuper"])}, '
            f'contorna_rls={sn(r["rolbypassrls"])}, '
            f'herda_privilegios={sn(r["rolinherit"])}, login={sn(r["rolcanlogin"])}')
        unidades.append((f'papel:{r["papel"]}', f'papel {r["papel"]}'))
    if dados["heranca"]:
        for r in dados["heranca"]:
            linhas.append(
                f'Heranca: {r["membro"]} e membro de {r["papel_concedido"]} '
                f'(herda_privilegios={sn(r["herda_privilegios"])})')
            unidades.append((f'heranca:{r["membro"]}->{r["papel_concedido"]}',
                             f'heranca {r["membro"]} -> {r["papel_concedido"]}'))
    else:
        linhas.append("Heranca: nenhuma")
    for r in dados["privilegios"]:
        linhas.append(f'Privilegios: o papel {r["papel"]} tem {r["privilegios"]} em {r["tabela"]}')
        unidades.append((f'privilegio:{r["papel"]}@{r["tabela"]}',
                         f'privilegios de {r["papel"]} em {r["tabela"]}'))

    linhas.append("")
    linhas.append("## ESTADO DO RLS")
    for r in dados["rls"]:
        linhas.append(f'Tabela {r["tabela"]}: rls_habilitado={sn(r["rls_habilitado"])}, '
                      f'rls_forcado={sn(r["rls_forcado"])}')
        unidades.append((f'rls:{r["tabela"]}', f'estado do RLS em {r["tabela"]}'))

    linhas.append("")
    linhas.append("## POLITICAS RLS")
    for r in dados["politicas"]:
        linhas.append(
            f'Politica {r["politica"]} em {r["tabela"]} ({r["tipo"]}) para {r["roles"]}, '
            f'comando {r["comando"]}; USING: {vazio(r["using_expr"])}; '
            f'WITH CHECK: {vazio(r["with_check"])}')
        unidades.append((f'politica:{r["tabela"]}.{r["politica"]}',
                         f'politica {r["politica"]} em {r["tabela"]}'))
    return "\n".join(linhas), unidades


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in INSTANCIAS:
        raise SystemExit("Uso: python extrator.py controle|defeitos")
    nome = sys.argv[1]
    servico, banco = INSTANCIAS[nome]
    dados = {k: rodar(servico, banco, v) for k, v in SQL.items()}
    texto, unidades = montar(dados)

    pasta = pathlib.Path("saida")
    pasta.mkdir(exist_ok=True)
    (pasta / f"extracao_{nome}.txt").write_text(texto + "\n", encoding="utf-8")

    req = pathlib.Path("requisitos.txt").read_text(encoding="utf-8").strip()
    prompt = MODELO_PROMPT.format(secoes=texto, requisitos=req)
    (pasta / f"prompt_{nome}.txt").write_text(prompt, encoding="utf-8")

    with open(pasta / f"unidades_{nome}.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["unidade", "descricao", "defeito"])
        for chave, desc in unidades:
            w.writerow([chave, desc, DEFEITOS.get(chave, "") if nome == "defeitos" else ""])

    print(f"{nome}: {len(unidades)} unidades. Arquivos em {pasta.resolve()}")


if __name__ == "__main__":
    main()
