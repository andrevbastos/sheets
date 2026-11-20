"""Rolagem de dados: validação do pedido, sorteio e texto do resultado.

Quem rola é sempre o servidor do mestre (os jogadores só pedem), então ninguém escolhe o
próprio resultado e todos veem o mesmo número.

Vantagem/desvantagem = dados extras: rola (quantidade + extras) e fica com os `quantidade`
maiores (vantagem) ou menores (desvantagem). Cobre o D&D (1 dado extra) e o Ordem Paranormal
(vários d20; atributo 0 = 2d20 pegando o pior).
"""
import secrets
import time

DICE = [4, 6, 8, 10, 12, 20, 100]
MAX_QTY = 20
MAX_EXTRA = 10
MAX_BONUS = 999

NORMAL, VANTAGEM, DESVANTAGEM = "normal", "vantagem", "desvantagem"
MODES = (NORMAL, VANTAGEM, DESVANTAGEM)


def clean_request(req: dict) -> dict:
    """Valida e limita um pedido vindo da rede. Levanta ValueError se não fizer sentido."""
    if not isinstance(req, dict):
        raise ValueError("pedido inválido")
    sides = int(req.get("sides", 20))
    if sides not in DICE:
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
        "label": str(req.get("label", "")).strip()[:60],
        "private": bool(req.get("private", False)),
    }


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
    return {**req, "who": who, "rolled": rolled, "kept": kept, "total": total, "time": time.time()}


def expression(r: dict) -> str:
    """'2d6 (Van 1) + 3'."""
    text = f"{r['qty']}d{r['sides']}"
    if r["mode"] == VANTAGEM:
        text += f" (Van {r['extra']})"
    elif r["mode"] == DESVANTAGEM:
        text += f" (Des {r['extra']})"
    if r["bonus"]:
        text += f" {'+' if r['bonus'] > 0 else '-'} {abs(r['bonus'])}"
    return text


def hidden(r: dict) -> dict:
    """Versão de uma rolagem privada para quem não é o mestre: só diz que houve uma rolagem."""
    return {"who": r["who"], "private": True, "hidden": True, "label": "", "time": r["time"]}


def describe(r: dict) -> str:
    """Linha de histórico: 'Sofia — Ataque: 1d20 (Van 1) + 5 → [12, (9)] = 17'."""
    if r.get("hidden"):
        return f"{r['who']} fez uma rolagem privada"
    head = r["who"] + (f" — {r['label']}" if r.get("label") else "")
    if r.get("private"):
        head += " (privada)"
    # dados descartados pela vantagem/desvantagem aparecem entre parênteses
    dice = ", ".join(str(v) if i in r["kept"] else f"({v})" for i, v in enumerate(r["rolled"]))
    return f"{head}: {expression(r)} → [{dice}] = {r['total']}"
