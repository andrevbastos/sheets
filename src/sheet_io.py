"""Leitura, escrita e normalização de fichas (JSON)."""
import copy
import json
import os
import tempfile

from src import ordem

SHEET_SYSTEM_DND5E = "dnd5e"
SHEETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sheets")

# Sistemas disponíveis: chave -> (nome para mostrar, template)
SYSTEMS = {
    SHEET_SYSTEM_DND5E: ("D&D 5e", os.path.join(SHEETS_DIR, "sheet-template.json")),
    ordem.SYSTEM: ("Ordem Paranormal", os.path.join(SHEETS_DIR, "ordem-template.json")),
}


def load_sheet(filepath: str) -> dict:
    """Carrega uma ficha JSON e devolve já normalizada."""
    with open(filepath, "r", encoding="utf-8") as file:
        return normalize_sheet(json.load(file))


def save_sheet(sheet_data: dict, filepath: str) -> None:
    """Salva a ficha de forma atômica (arquivo temporário + rename), sem risco de corromper."""
    directory = os.path.dirname(os.path.abspath(filepath))
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=directory)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(sheet_data, file, indent=2, ensure_ascii=False)
        os.replace(tmp_path, filepath)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise


def clean_placeholders(data, character_name: str):
    """Troca os placeholders '{{...}}' do template por vazio (ou pelo nome do personagem)."""
    if isinstance(data, dict):
        return {k: clean_placeholders(v, character_name) for k, v in data.items()}
    if isinstance(data, list):
        return [clean_placeholders(item, character_name) for item in data]
    if isinstance(data, str) and data.startswith("{{") and data.endswith("}}"):
        return character_name if data == "{{nome_do_personagem}}" else ""
    return data


def create_new_sheet(character_name: str, template_path: str, output_path: str) -> dict:
    """Cria uma ficha limpa a partir do template, normaliza e salva em output_path.

    `template_path` pode ser um caminho ou a chave de um sistema ("dnd5e", "ordem")."""
    if template_path in SYSTEMS:
        template_path = SYSTEMS[template_path][1]
    with open(template_path, "r", encoding="utf-8") as file:
        template_data = json.load(file)
    sheet = normalize_sheet(clean_placeholders(template_data, character_name))
    save_sheet(sheet, output_path)
    return sheet


# --------------------------------------------------------------------------
# Normalização: garante tipos corretos para a interface não quebrar
# --------------------------------------------------------------------------
def to_int(value, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace("+", "")
        try:
            return int(text)
        except ValueError:
            try:
                return int(float(text.replace(",", ".")))
            except ValueError:
                return default
    return default


def to_bool(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("true", "sim", "s", "1", "x", "yes")
    return bool(value)


def _is_empty(value) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, dict):
        return all(_is_empty(v) for v in value.values())
    if isinstance(value, list):
        return all(_is_empty(v) for v in value)
    return False


def _clean_list(items) -> list:
    """Remove entradas vazias (sobras do template) de uma lista."""
    if not isinstance(items, list):
        return []
    return [item for item in items if not _is_empty(item)]


def normalize_sheet(sheet: dict) -> dict:
    """Devolve uma cópia da ficha com números como int, booleanos como bool e listas sem itens vazios."""
    if isinstance(sheet, dict) and sheet.get("sistema") == ordem.SYSTEM:
        return ordem.normalize(sheet, to_int, _clean_list)
    return _normalize_dnd5e(sheet)


def _normalize_dnd5e(sheet: dict) -> dict:
    s = copy.deepcopy(sheet) if isinstance(sheet, dict) else {}

    s.setdefault("sistema", SHEET_SYSTEM_DND5E)
    s["nome"] = str(s.get("nome") or "Sem Nome")
    cor = str(s.get("cor") or "").strip()
    s["cor"] = cor if cor.startswith("#") and len(cor) in (4, 7) else "#d4af37"
    for key in ("classe_nivel", "raca", "antecedente", "tendencia"):
        s[key] = str(s.get(key) or "")
    s["experiencia"] = to_int(s.get("experiencia"), 0)

    combate = s.setdefault("combate", {})
    combate["hp_max"] = max(0, to_int(combate.get("hp_max"), 0))
    combate["hp_atual"] = max(0, min(to_int(combate.get("hp_atual"), combate["hp_max"]), combate["hp_max"]))
    combate["ca"] = to_int(combate.get("ca"), 10)
    combate["iniciativa"] = to_int(combate.get("iniciativa"), 0)
    combate["deslocamento"] = str(combate.get("deslocamento") or "9m")

    for attr in s.setdefault("atributos", {}).values():
        if isinstance(attr, dict):
            attr["valor"] = to_int(attr.get("valor"), 10)
            attr["mod"] = to_int(attr.get("mod"), (attr["valor"] - 10) // 2)

    for group in ("resistencia", "pericias"):
        for entry in s.setdefault(group, {}).values():
            if isinstance(entry, dict):
                entry["bonus"] = to_int(entry.get("bonus"), 0)
                entry["proficiente"] = to_bool(entry.get("proficiente"))

    magias = s.setdefault("magias", {})
    magias["classe_conjurador"] = str(magias.get("classe_conjurador") or "")
    magias["cd_salvamento"] = to_int(magias.get("cd_salvamento"), 0)
    magias["bonus_ataque"] = to_int(magias.get("bonus_ataque"), 0)
    slots = magias.setdefault("slots", {})
    for lvl in range(1, 10):
        slot = slots.setdefault(str(lvl), {})
        slot["max"] = max(0, to_int(slot.get("max"), 0))
        slot["atual"] = max(0, min(to_int(slot.get("atual"), 0), slot["max"]))
    magias["lista"] = _clean_list(magias.get("lista"))

    for key in ("ataques", "recursos", "inventario", "idiomas", "proficiencias", "caracteristicas"):
        s[key] = _clean_list(s.get(key))
    s["inventario"] = [str(item) for item in s["inventario"]]

    # Fichas antigas usavam "custom" no lugar de "extra"
    extra = s.get("extra")
    if not isinstance(extra, dict):
        extra = s.pop("custom", {}) if isinstance(s.get("custom"), dict) else {}
    else:
        s.pop("custom", None)
    for key, category in list(extra.items()):
        if isinstance(category, list):
            extra[key] = _clean_list(category)
        elif isinstance(category, dict) and "lista" in category:
            category["lista"] = _clean_list(category.get("lista"))
            if "maximo" in category:
                category["maximo"] = max(0, to_int(category.get("maximo"), 3))
    s["extra"] = extra

    return s
