"""
rodar_llm.py - envia o prompt padronizado ao Claude varias vezes e salva
as respostas (uma por arquivo) para o calculo das metricas.

Uso (na pasta do experimento, depois de rodar o extrator.py):
  $env:ANTHROPIC_API_KEY = "sua-chave"          # PowerShell, so nesta janela
  python rodar_llm.py ambos                      # controle e defeitos
  python rodar_llm.py defeitos --execucoes 5 --temperatura 1.0

Parametros do experimento (registrar no artigo):
  modelo padrao ........ claude-sonnet-5-5
  temperatura padrao ... 1.0
  execucoes padrao ..... 5 por base

Sem bibliotecas externas. NUNCA coloque a chave no codigo nem no repositorio.
Somente METADADOS do banco vao no prompt (nenhum dado das tabelas).
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

API_URL = "https://api.anthropic.com/v1/messages"
PASTA = pathlib.Path("saida")
RESP = PASTA / "respostas"


def chamar(modelo, temperatura, prompt, chave, max_tokens=4096):
    corpo = json.dumps({
        "model": modelo,
        "max_tokens": max_tokens,
        "temperature": temperatura,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(API_URL, data=corpo, method="POST", headers={
        "x-api-key": chave,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    for tentativa in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detalhe = e.read().decode("utf-8", "replace")
            if e.code in (429, 500, 502, 503, 529) and tentativa < 3:
                time.sleep(5 * (tentativa + 1))
                continue
            raise SystemExit(f"Erro da API ({e.code}): {detalhe}")
        except urllib.error.URLError as e:
            if tentativa < 3:
                time.sleep(5 * (tentativa + 1))
                continue
            raise SystemExit(f"Falha de rede: {e}")


def texto_da_resposta(resp):
    return "".join(b.get("text", "") for b in resp.get("content", [])
                   if b.get("type") == "text")


def extrair_json(texto):
    """Tenta ler a lista JSON da resposta (aceita cerca ```json)."""
    t = texto.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", t, re.S)
    if m:
        t = m.group(1).strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        pass
    i, j = t.find("["), t.rfind("]")
    if i != -1 and j > i:
        try:
            return json.loads(t[i:j + 1])
        except json.JSONDecodeError:
            return None
    if "nenhum problema encontrado" in texto.lower():
        return []
    return None


def formato_ok(parsed):
    return isinstance(parsed, list) and all(
        isinstance(x, dict) and "objeto" in x for x in parsed)


def executar(inst, n, modelo, temperatura, chave, refazer):
    prompt = (PASTA / f"prompt_{inst}.txt").read_text(encoding="utf-8")
    hash_prompt = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:12]
    RESP.mkdir(parents=True, exist_ok=True)
    for k in range(1, n + 1):
        destino = RESP / f"{inst}_exec{k:02d}.json"
        if destino.exists() and not refazer:
            print(f"{destino.name}: ja existe, pulando")
            continue
        resp = chamar(modelo, temperatura, prompt, chave)
        texto = texto_da_resposta(resp)
        parsed = extrair_json(texto)
        registro = {
            "instancia": inst,
            "execucao": k,
            "modelo": modelo,
            "modelo_retornado": resp.get("model"),
            "temperatura": temperatura,
            "data_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "hash_prompt": hash_prompt,
            "uso_tokens": resp.get("usage"),
            "formato_ok": formato_ok(parsed),
            "resposta_bruta": texto,
            "problemas": parsed if formato_ok(parsed) else None,
        }
        destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        qtd = len(parsed) if formato_ok(parsed) else "formato invalido"
        print(f"{destino.name}: {qtd} problemas apontados")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("instancia", choices=["controle", "defeitos", "ambos"])
    ap.add_argument("--execucoes", type=int, default=5)
    ap.add_argument("--temperatura", type=float, default=1.0)
    ap.add_argument("--modelo", default="claude-sonnet-5-5")
    ap.add_argument("--refazer", action="store_true")
    a = ap.parse_args()

    chave = os.environ.get("ANTHROPIC_API_KEY")
    if not chave:
        sys.exit('Defina a chave primeiro (PowerShell): $env:ANTHROPIC_API_KEY = "sua-chave"')

    alvos = ["controle", "defeitos"] if a.instancia == "ambos" else [a.instancia]
    for inst in alvos:
        executar(inst, a.execucoes, a.modelo, a.temperatura, chave, a.refazer)


if __name__ == "__main__":
    main()
