"""Leitura, escrita e normalização de fichas (JSON)."""
import json
import os
import tempfile

from src import dnd, ordem

SHEET_SYSTEM_DND5E = dnd.SYSTEM
SHEETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "sheets")

# Sistemas disponíveis: chave -> (nome para mostrar, template)
SYSTEMS = {
    SHEET_SYSTEM_DND5E: ("D&D 5e", os.path.join(SHEETS_DIR, "dnd-template.json")),
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


THREAT_TYPES = {ordem.SYSTEM: ordem.TIPO_AMEACA, dnd.SYSTEM: dnd.TIPO_MONSTRO}  # ficha só do mestre


def create_new_threat(name: str, output_path: str, system: str = ordem.SYSTEM) -> dict:
    """Cria em branco a ficha só do mestre do sistema: ameaça (Ordem Paranormal) ou monstro (D&D 5e)."""
    sheet = normalize_sheet({"sistema": system, "tipo": THREAT_TYPES[system], "nome": name})
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
    """Devolve uma cópia da ficha com os tipos certos e as regras do sistema já aplicadas."""
    if isinstance(sheet, dict) and sheet.get("sistema") == ordem.SYSTEM:
        return ordem.normalize(sheet, to_int, _clean_list)
    return dnd.normalize(sheet, to_int, to_bool, _clean_list)  # sem "sistema": fichas antigas eram de D&D
