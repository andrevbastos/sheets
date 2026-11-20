import json
import os

def load_sheet(filepath: str) -> dict:
    """Carrega um arquivo de ficha JSON e retorna como dicionário."""
    with open(filepath, 'r', encoding='utf-8') as file:
        return json.load(file)

def save_sheet(sheet_data: dict, filepath: str) -> None:
    """Salva o dicionário da ficha no disco como JSON formatado."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as file:
        json.dump(sheet_data, file, indent=2, ensure_ascii=False)

def clean_placeholders(data: any, character_name: str) -> any:
    """
    Função recursiva para remover placeholders '{{...}}' do template,
    substituindo-os por valores padrão (string vazia ou o nome do personagem).
    """
    if isinstance(data, dict):
        return {k: clean_placeholders(v, character_name) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_placeholders(item, character_name) for item in data]
    elif isinstance(data, str):
        if data.startswith("{{") and data.endswith("}}"):
            if data == "{{nome_do_personagem}}":
                return character_name
            return ""
        return data
    return data

def create_new_sheet(character_name: str, template_path: str, output_path: str) -> dict:
    """
    Carrega o template, limpa todos os placeholders substituindo-os
    por valores padrão e salva o novo arquivo de ficha.
    """
    template_data = load_sheet(template_path)
    clean_data = clean_placeholders(template_data, character_name)
    save_sheet(clean_data, output_path)
    return clean_data
