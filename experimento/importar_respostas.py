"""
importar_respostas.py - converte as respostas salvas em saida\\brutas\\ para o
mesmo formato JSON do rodar_llm.py.

As respostas usadas no artigo foram gravadas automaticamente pelo
rodar_claude_code.ps1 (Claude Code em modo nao interativo), sem copia manual.
O script tambem aceita respostas salvas a mao (por exemplo, do chat do
claude.ai); informe a origem em --interface.
O campo "execucao_manual" do JSON indica apenas que a resposta nao veio do
rodar_llm.py (API); ele nao significa que o texto foi colado a mao.

Passo a passo:
  1. Salve cada resposta em saida\\brutas\\ com o nome  <base>_<NN>.txt  (UTF-8):
       controle_01.txt ... controle_05.txt
       defeitos_01.txt ... defeitos_05.txt
  2. Rode (na pasta do experimento):
       python importar_respostas.py --modelo "Claude Opus 5.5" --interface "..."
     Gera saida\\respostas\\<base>_exec<NN>.json (entrada do comparar.py).

Registra: modelo, interface, data do arquivo, hash do prompt e que a
temperatura NAO foi controlada.

Normalizacao: se a resposta original nao passar na validacao de formato, o
importador remove aspas, crases, asteriscos, espacos e ponto final das bordas.
Se o que sobrar for exatamente "nenhum problema encontrado", a resposta e
validada com essa frase e o JSON registra "normalizado": true. Respostas com
JSON nunca sao alteradas. "resposta_bruta" guarda sempre o texto original.
"""
import argparse
import datetime
import hashlib
import json
import pathlib
import re

import rodar_llm as r

BRUTAS = r.PASTA / "brutas"

FRASE_SEM_PROBLEMAS = "nenhum problema encontrado"
BORDAS = " \t\r\n\"'`*“”‘’."


def ler(arq):
    try:
        return arq.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return arq.read_text(encoding="cp1252")


def normalizar_sem_problemas(texto):
    """Devolve a frase canonica se o texto, sem enfeites nas bordas, for
    'nenhum problema encontrado'. Caso contrario, devolve None."""
    limpo = texto.strip(BORDAS)
    if limpo.lower() == FRASE_SEM_PROBLEMAS:
        return FRASE_SEM_PROBLEMAS
    return None


def validar(texto):
    """Tenta validar o texto original. Se falhar, tenta a normalizacao.
    Retorna (parsed, ok, normalizado)."""
    parsed = r.extrair_json(texto)
    if r.formato_ok(parsed):
        return parsed, True, False

    canonico = normalizar_sem_problemas(texto)
    if canonico is not None:
        parsed = r.extrair_json(canonico)
        if r.formato_ok(parsed):
            return parsed, True, True

    return parsed, False, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modelo", required=True, help='ex.: "Claude Opus 5.5"')
    ap.add_argument("--interface", default="claude.ai (chat)",
                    help='ex.: "Claude Code (claude -p, pasta isolada)"')
    ap.add_argument("--observacao", default="")
    a = ap.parse_args()

    if not BRUTAS.exists():
        raise SystemExit(f"Crie a pasta {BRUTAS} e salve as respostas la dentro.")
    r.RESP.mkdir(parents=True, exist_ok=True)

    resumo = {}
    for arq in sorted(BRUTAS.glob("*.txt")):
        m = re.fullmatch(r"(controle|defeitos)_(\d+)\.txt", arq.name)
        if not m:
            print(f"ignorado (nome fora do padrao): {arq.name}")
            continue
        inst, k = m.group(1), int(m.group(2))
        prompt = (r.PASTA / f"prompt_{inst}.txt").read_text(encoding="utf-8")
        texto = ler(arq)
        parsed, ok, normalizado = validar(texto)
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
            "normalizado": normalizado,
            "resposta_bruta": texto,
            "problemas": parsed if ok else None,
        }
        destino = r.RESP / f"{inst}_exec{k:02d}.json"
        destino.write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                           encoding="utf-8")
        qtd = len(parsed) if ok else "formato invalido"
        aviso = " (normalizado)" if normalizado else ""
        print(f"{arq.name} -> {destino.name}: {qtd} problemas apontados{aviso}")
        resumo.setdefault(inst, []).append(ok)

    for inst, lst in resumo.items():
        print(f"{inst}: {len(lst)} respostas importadas, {sum(lst)} com formato valido")


if __name__ == "__main__":
    main()