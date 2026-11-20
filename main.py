import os
from src.sheet_parser import create_new_sheet, load_sheet

def run_parser_test():
    print("--- Iniciando Teste de Integração do Sheet Parser ---")
    
    template_path = "sheets/sheet-template.json"
    output_path = "sheets/Gimli.json"
    
    # 1. Certificar que o template existe
    if not os.path.exists(template_path):
        print(f"Erro: O arquivo de template '{template_path}' não foi encontrado.")
        return
        
    print(f"Carregando template de: {template_path}")
    print("Criando nova ficha limpa para 'Gimli'...")
    
    # 2. Criar a ficha limpa a partir do template
    create_new_sheet("Gimli", template_path, output_path)
    
    # 3. Validar se o arquivo foi escrito
    if os.path.exists(output_path):
        print(f"Sucesso: Ficha gerada em '{output_path}'")
        
        # 4. Carregar os dados para validar
        ficha = load_sheet(output_path)
        print(f"Nome do Personagem na Ficha: {ficha['nome']}")
        print(f"Classe/Nível na Ficha (deve ser vazio): '{ficha['classe_nivel']}'")
        print(f"HP Atual (deve ser vazio): '{ficha['combate']['hp_atual']}'")
        print(f"Cartas de Destino Iniciais: {len(ficha['custom']['cartas_destino']['lista'])} (todas vazias)")
    else:
        print("Erro: A ficha de Gimli não foi gerada no disco.")
        
    print("--- Teste de Integração Finalizado ---")

if __name__ == "__main__":
    run_parser_test()
