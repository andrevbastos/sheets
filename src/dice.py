"""Rolagem de dados: validação do pedido, sorteio e texto do resultado.

Quem rola é sempre o servidor do mestre (os jogadores só pedem), então ninguém escolhe o
próprio resultado e todos veem o mesmo número.

Vantagem/desvantagem = dados extras: rola (quantidade + extras) e fica com os `quantidade`
maiores (vantagem) ou menores (desvantagem). Cobre o D&D (1 dado extra) e o Ordem Paranormal
(vários d20; atributo 0 = 2d20 pegando o pior).
"""
import re
import secrets
import time

DICE = [4, 6, 8, 10, 12, 20, 100]          # botões da janela de dados
ROLLABLE = sorted(set(DICE) | {2, 3})      # aceitos num pedido (ex.: soco de civil, 1d3+1)
MAX_LABEL = 60
MAX_QTY = 20
MAX_EXTRA = 10
MAX_BONUS = 999

NORMAL, VANTAGEM, DESVANTAGEM = "normal", "vantagem", "desvantagem"
CRIT_SUCCESS, CRIT_FAIL = "sucesso", "falha"
CRIT_TEXT = {CRIT_SUCCESS: "SUCESSO CRÍTICO", CRIT_FAIL: "FALHA CRÍTICA"}
MODES = (NORMAL, VANTAGEM, DESVANTAGEM)


def clean_request(req: dict) -> dict:
    """Valida e limita um pedido vindo da rede. Levanta ValueError se não fizer sentido."""
    if not isinstance(req, dict):
        raise ValueError("pedido inválido")
    sides = int(req.get("sides", 20))
    if sides not in ROLLABLE:
        raise ValueError(f"dado d{sides} não existe")
    mode = req.get("mode", NORMAL)
    if mode not in MODES:
        mode = NORMAL
    extra = int(req.get("extra", 1)) if mode != NORMAL else 0
    return {
        "sides": sides,
        "qty": max(1, min(int(req.get("qty", 1)), MAX_QTY)),
        "mode": mode,
        "extra": max(1, min(extra, MAX_EXTRA)) if mode != NORMAL else 0,
        "bonus": max(-MAX_BONUS, min(int(req.get("bonus", 0)), MAX_BONUS)),
        "private": bool(req.get("private", False)),
        "label": " ".join(str(req.get("label") or "").split())[:MAX_LABEL],  # "Luta", "Sofia · Garras"
    }


_DICE_RE = re.compile(r"(?<![\wÀ-ÿ])(\d*)d(\d+)(?:\s*([+\-−])\s*(\d+)(?!\d)(?!\s*d\d))?", re.I)


def parse_dice(text):
    """Primeira expressão de dados do texto: '2d6+4 corte' -> {'qty': 2, 'sides': 6, 'bonus': 4}.

    Devolve None se não houver dado que dê para rolar. Só a primeira parte de '2d6+4 + 1d6 Morte' é rolada.
    """
    match = _DICE_RE.search(str(text or ""))
    if not match:
        return None
    qty, sides = int(match.group(1) or 1), int(match.group(2))
    if sides not in ROLLABLE or not 1 <= qty <= MAX_QTY:
        return None
    bonus = int(match.group(4) or 0) * (-1 if match.group(3) in ("-", "−") else 1)
    return {"qty": qty, "sides": sides, "mode": NORMAL, "extra": 0, "bonus": bonus}


def roll(req: dict, who: str, rng=None) -> dict:
    """Rola um pedido já validado e devolve o resultado completo."""
    rand = rng or secrets.SystemRandom()
    rolled = [rand.randint(1, req["sides"]) for _ in range(req["qty"] + req["extra"])]
    if req["mode"] == VANTAGEM:
        kept_idx = sorted(range(len(rolled)), key=lambda i: -rolled[i])[:req["qty"]]
    elif req["mode"] == DESVANTAGEM:
        kept_idx = sorted(range(len(rolled)), key=lambda i: rolled[i])[:req["qty"]]
    else:
        kept_idx = list(range(len(rolled)))
    kept = sorted(kept_idx)
    total = sum(rolled[i] for i in kept) + req["bonus"]
    result = {**req, "who": who, "rolled": rolled, "kept": kept, "total": total, "time": time.time()}
    result["critical"] = critical(result)
    return result


def critical(r: dict):
    """'sucesso' (20 natural) ou 'falha' (1 natural) num teste de 1d20; None nos outros casos.

    Vale o dado que ficou depois da vantagem/desvantagem. Com vários d20 somados não há crítico.
    """
    if r.get("hidden") or r.get("sides") != 20 or r.get("qty") != 1 or not r.get("kept"):
        return None
    natural = r["rolled"][r["kept"][0]]
    return CRIT_SUCCESS if natural == 20 else CRIT_FAIL if natural == 1 else None


def expression(r: dict) -> str:
    """'2d6 + 3', '3d20 (maior) + 10', '2d20 (menor)', '4d6 (2 maiores)': mostra todos os dados rolados."""
    text = f"{r['qty'] + r['extra']}d{r['sides']}"
    if r["mode"] in (VANTAGEM, DESVANTAGEM):
        word = "maior" if r["mode"] == VANTAGEM else "menor"
        text += f" ({word})" if r["qty"] == 1 else f" ({r['qty']} {word}es)"
    if r["bonus"]:
        text += f" {'+' if r['bonus'] > 0 else '-'} {abs(r['bonus'])}"
    return text


def hidden(r: dict) -> dict:
    """Versão de uma rolagem privada para quem não é o mestre: só diz que houve uma rolagem."""
    return {"who": r["who"], "private": True, "hidden": True, "time": r["time"]}  # sem o rótulo também


def describe(r: dict) -> str:
    """Linha de histórico: 'Sofia · Luta: 2d20 (maior) + 5 → [20, (9)] = 25 — SUCESSO CRÍTICO'."""
    if r.get("hidden"):
        return f"{r['who']}: ?d? = ?"
    head = r["who"] + (f" · {r['label']}" if r.get("label") else "") + (" (privada)" if r.get("private") else "")
    # dados descartados pela vantagem/desvantagem aparecem entre parênteses
    dice = ", ".join(str(v) if i in r["kept"] else f"({v})" for i, v in enumerate(r["rolled"]))
    text = f"{head}: {expression(r)} → [{dice}] = {r['total']}"
    crit = critical(r)
    return f"{text} — {CRIT_TEXT[crit]}" if crit else text
