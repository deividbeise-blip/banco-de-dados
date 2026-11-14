"""
importar_manual.py - converte as respostas COLADAS A MAO (execucoes feitas no
chat do Claude) para o mesmo formato JSON do rodar_llm.py.

Passo a passo:
  1. Em cada conversa nova, cole o prompt e copie a resposta inteira.
  2. Salve em saida\\manual\\ com o nome  <base>_<NN>.txt  (UTF-8):
       controle_01.txt ... controle_05.txt
       defeitos_01.txt ... defeitos_05.txt
  3. Rode (na pasta do experimento):
       python importar_manual.py --modelo "Claude Opus 5.5"
     Gera saida\\respostas\\<base>_exec<NN>.json (o que o Donjoe usa nas metricas).

Registra: modelo, interface, data do arquivo, hash do prompt e que a
temperatura NAO foi controlada.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re

import rodar_llm as r

MANUAL = r.PASTA / "manual"


def ler(arq):
    try:
        return arq.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return arq.read_text(encoding="cp1252")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True, help='ex.: "Claude Opus 5.5"')
    ap.add_argument("--interface", default="claude.ai (chat)")
    ap.add_argument("--observacao", default="")
    a = ap.parse_args()

    if not MANUAL.exists():
        raise SystemExit(f"Crie a pasta {MANUAL} e salve as respostas la dentro.")
    r.RESP.mkdir(parents=True, exist_ok=True)

    resumo = {}
    for arq in sorted(MANUAL.glob("*.txt")):
        m = re.fullmatch(r"(controle|defeitos)_(\d+)\.txt", arq.name)
        if not m:
            print(f"ignorado (nome fora do padrao): {arq.name}")
            continue
        inst, k = m.group(1), int(m.group(2))
        prompt = (r.PASTA / f"prompt_{inst}.txt").read_text(encoding="utf-8")
        texto = ler(arq)
        parsed = r.extrair_json(texto)
        ok = r.formato_ok(parsed)
        data = datetime.datetime.fromtimestamp(
            arq.stat().st_mtime, tz=datetime.timezone.utc).isoformat()
        registro = {
            "instancia": inst,
            "execucao": k,
            "modelo": a.modelo,
            "interface": a.interface,
            "execucao_manual": True,
            "temperatura": None,
            "temperatura_controlada": False,
            "data_utc": data,
            "hash_prompt": hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12],
            "observacao": a.observacao,
            "formato_ok": ok,
            "resposta_bruta": texto,
            "problemas": parsed if ok else None,
        }
        destino = r.RESP / f"{inst}_exec{k:02d}.json"
        destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        qtd = len(parsed) if ok else "formato invalido"
        print(f"{arq.name} -> {destino.name}: {qtd} problemas apontados")
        resumo.setdefault(inst, []).append(ok)

    for inst, lst in resumo.items():
        print(f"{inst}: {len(lst)} respostas importadas, {sum(lst)} com formato valido")


if __name__ == "__main__":
    main()
