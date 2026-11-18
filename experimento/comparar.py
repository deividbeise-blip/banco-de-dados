"""
comparar.py - compara as respostas do LLM com o gabarito e calcula as metricas.

Entradas (geradas pelo extrator e pelo importador):
  saida/unidades_<base>.csv          unidades de analise e defeito (gabarito)
  saida/respostas/<base>_execNN.json respostas convertidas pelo importar_respostas.py

Saidas:
  saida/metricas_por_execucao.csv    VP, FP, FN, VN e metricas por execucao
  saida/deteccao_por_defeito.csv     defeito x execucao (1 = apontado)
  saida/falsos_alertas.csv           unidade correta apontada, base e execucao
  resumo no terminal, com intervalos de confianca

Regras (definidas antes dos resultados, Secao 5.4 do artigo):
  - cada objeto conta uma vez por resposta;
  - o objeto e casado com a unidade pelo identificador exato; se nao casar e
    for "politica:<nome>", casa pelo nome da politica, desde que seja unico;
  - objeto que nao existe na base conta como apontamento a objeto inexistente;
  - apontamento em unidade correta conta como falso alerta (FP), mesmo que
    seja sugestao de endurecimento plausivel.

Uso (na pasta do experimento):
  python comparar.py
"""
import csv
import json
import math
import pathlib
import statistics

PASTA = pathlib.Path(__file__).resolve().parent / "saida"
BASES = ["controle", "defeitos"]
EXECUCOES = range(1, 6)


def ler_unidades(base):
    with open(PASTA / f"unidades_{base}.csv", encoding="utf-8") as f:
        return {l["unidade"]: (l["defeito"] or None) for l in csv.DictReader(f)}


def casar(objeto, unidades):
    """Devolve (unidade, normalizado) ou (None, False) se nao existir."""
    objeto = objeto.strip()
    if objeto in unidades:
        return objeto, False
    if objeto.startswith("politica:"):
        nome = objeto.split(":", 1)[1].split(".")[-1]
        cand = [u for u in unidades
                if u.startswith("politica:") and u.split(".")[-1] == nome]
        if len(cand) == 1:
            return cand[0], True
    return None, False


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return max(0.0, centro - meia), min(1.0, centro + meia)


def limite_inferior_exato(n, alfa=0.05):
    """Limite inferior de Clopper-Pearson (bicaudal) quando k = n."""
    return (alfa / 2) ** (1 / n)


def pct(x):
    return round(100 * x, 1)


def main():
    linhas, deteccao, alertas = [], [], []
    for base in BASES:
        unidades = ler_unidades(base)
        defeitos = {u: d for u, d in unidades.items() if d}
        corretas = [u for u, d in unidades.items() if not d]
        for k in EXECUCOES:
            dados = json.loads((PASTA / "respostas" / f"{base}_exec{k:02d}.json")
                               .read_text(encoding="utf-8"))
            apontadas, inexistentes, normalizados = set(), [], []
            for p in dados.get("problemas") or []:
                u, norm = casar(p["objeto"], unidades)
                if u is None:
                    inexistentes.append(p["objeto"])
                else:
                    apontadas.add(u)
                    if norm:
                        normalizados.append((p["objeto"], u))
            vp = len(apontadas & set(defeitos))
            fp = len(apontadas & set(corretas))
            fn = len(defeitos) - vp
            vn = len(corretas) - fp
            cob = vp / (vp + fn) if defeitos else None
            prec = vp / (vp + fp) if (vp + fp) else None
            f1 = (2 * prec * cob / (prec + cob)) if (cob and prec) else None
            linhas.append({
                "base": base, "execucao": k, "VP": vp, "FP": fp, "FN": fn,
                "VN": vn, "cobertura": cob, "precisao": prec, "F1": f1,
                "FPR": fp / (fp + vn), "objetos_inexistentes": len(inexistentes),
                "formato_ok": dados.get("formato_ok"),
            })
            for u, d in defeitos.items():
                deteccao.append({"defeito": d, "execucao": k,
                                 "apontado": int(u in apontadas)})
            for u in sorted(apontadas & set(corretas)):
                alertas.append({"base": base, "execucao": k, "unidade": u})
            for o, u in normalizados:
                print(f"[{base} E{k}] objeto '{o}' casado com '{u}' pelo nome")

    def gravar(nome, rows):
        with open(PASTA / nome, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)

    gravar("metricas_por_execucao.csv", linhas)
    gravar("deteccao_por_defeito.csv", deteccao)
    gravar("falsos_alertas.csv", alertas)

    for base in BASES:
        ls = [l for l in linhas if l["base"] == base]
        print(f"\n== Base {base} ==")
        for l in ls:
            print(f"E{l['execucao']}: VP={l['VP']} FP={l['FP']} FN={l['FN']} "
                  f"VN={l['VN']} FPR={pct(l['FPR'])}% "
                  f"prec={pct(l['precisao']) if l['precisao'] is not None else '-'} "
                  f"inexistentes={l['objetos_inexistentes']}")
        for m in ["cobertura", "precisao", "F1", "FPR"]:
            v = [l[m] for l in ls if l[m] is not None]
            if v:
                print(f"{m}: media {pct(statistics.mean(v))}% "
                      f"DP {pct(statistics.stdev(v))} p.p.")
        fp = sum(l["FP"] for l in ls)
        n = sum(l["FP"] + l["VN"] for l in ls)
        lo, hi = wilson(fp, n)
        print(f"FPR agregada: {fp}/{n} = {pct(fp / n)}% "
              f"(Wilson 95%: {pct(lo)}% a {pct(hi)}%)")
        vp = sum(l["VP"] for l in ls)
        if vp:
            print(f"Precisao agregada: {vp}/{vp + fp} = {pct(vp / (vp + fp))}%")
            print(f"Cobertura 6/6 por execucao: limite inferior exato 95% = "
                  f"{pct(limite_inferior_exato(6))}%")

    print("\nDeteccao por defeito (defeito: execucoes em que foi apontado)")
    for d in sorted({x["defeito"] for x in deteccao}):
        ks = [x["execucao"] for x in deteccao if x["defeito"] == d and x["apontado"]]
        print(f"{d}: {ks}")


if __name__ == "__main__":
    main()
