import tkinter as tk
import customtkinter as ctk
import json
import os

# Configuração global do CustomTkinter
ctk.set_appearance_mode("dark")

class PlayerMockupGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Mockup D&D Cheat Sheet - Jogador")
        self.root.geometry("1100x750")
        self.root.minsize(1050, 700)
        
        # Carrega dados da ficha de exemplo
        self.sheet = self.load_mock_sheet()
        
        # Cor de destaque padrão (Padrão ouro do exemplo)
        self.current_color = self.sheet.get("cor", "#d4af37")
        
        # Listas de controle para atualização dinâmica de cor
        self.color_framed_widgets = []
        self.main_tab_indicators = {}
        self.sub_tab_indicators = {}
        
        self.build_ui()
        
        # Desfoca o campo de entrada ao clicar fora dele
        self.root.bind("<Button-1>", self.on_click_outside)
        
    def load_mock_sheet(self):
        filepath = "sheets/sheet-example.json"
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "nome": "Erro ao Carregar",
            "cor": "#d4af37",
            "classe_nivel": "Desconhecido",
            "combate": {"hp_atual": 12, "hp_max": 12, "ca": 16, "iniciativa": 2, "deslocamento": "9m"},
            "atributos": {}
        }
        
    def save_to_disk_mock(self):
        """Salva as alterações em tempo real no arquivo de ficha do mockup."""
        filepath = "sheets/sheet-example.json"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.sheet, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Erro ao salvar arquivo de mockup: {e}")
            
    def on_click_outside(self, event):
        """Remove o foco dos campos de entrada de texto se o usuário clicar fora."""
        curr = event.widget
        is_entry = False
        while curr:
            try:
                class_name = curr.__class__.__name__.lower()
                if "entry" in class_name:
                    is_entry = True
                    break
                w_class = curr.winfo_class().lower()
                if "entry" in w_class:
                    is_entry = True
                    break
            except Exception:
                pass
            try:
                parent_path = curr.winfo_parent()
                if not parent_path:
                    break
                curr = curr._nametowidget(parent_path)
            except Exception:
                break
        if not is_entry:
            self.root.focus()

    def build_ui(self):
        # Frame Principal de Fundo (Grayscale)
        self.bg_frame = ctk.CTkFrame(self.root, fg_color="#121212", corner_radius=0)
        self.bg_frame.pack(fill=tk.BOTH, expand=True)
        
        # === BARRA DE SELEÇÃO DE CORES NO TOPO ===
        self.color_bar = ctk.CTkFrame(self.bg_frame, fg_color="#1e1e1e", height=45, corner_radius=0)
        self.color_bar.pack(fill=tk.X, side=tk.TOP)
        
        lbl_selector = ctk.CTkLabel(
            self.color_bar, 
            text="CORES DOS JOGADORES:", 
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#888888"
        )
        lbl_selector.pack(side=tk.LEFT, padx=20, pady=10)
        
        test_colors = [
            ("Aya (Verde)", "#2ecc71"),
            ("Kara (Vermelho)", "#e74c3c"),
            ("Akta (Laranja)", "#e67e22"),
            ("Exemplo (Dourado)", "#d4af37"),
            ("Neutro (Cinza)", "#888888")
        ]
        
        for label, hex_color in test_colors:
            btn = ctk.CTkButton(
                self.color_bar,
                text=label,
                fg_color="#2b2b2b",
                hover_color="#3e3e3e",
                border_color=hex_color,
                border_width=1,
                text_color="#ffffff",
                width=110,
                height=24,
                font=ctk.CTkFont(size=10),
                command=lambda c=hex_color: self.change_ui_color(c)
            )
            btn.pack(side=tk.LEFT, padx=8, pady=10)
            
        # === CABEÇALHO ===
        self.header_frame = ctk.CTkFrame(
            self.bg_frame, 
            fg_color="#1e1e1e", 
            border_color=self.current_color, 
            border_width=2,
            corner_radius=10,
            height=60
        )
        self.header_frame.pack(fill=tk.X, padx=20, pady=(15, 10))
        self.color_framed_widgets.append(self.header_frame)
        
        self.lbl_nome = ctk.CTkLabel(
            self.header_frame, 
            text=self.sheet.get("nome", "Sem Nome").upper(),
            font=ctk.CTkFont(family="Cinzel", size=20, weight="bold"),
            text_color="#ffffff"
        )
        self.lbl_nome.pack(side=tk.LEFT, padx=20, pady=12)
        
        self.lbl_info = ctk.CTkLabel(
            self.header_frame, 
            text=f"Classe/Nível: {self.sheet.get('classe_nivel', '')}  |  Raça: {self.sheet.get('raca', '')}  |  Antecedente: {self.sheet.get('antecedente', '')}  |  Tendência: {self.sheet.get('tendencia', '')}",
            font=ctk.CTkFont(size=12),
            text_color="#aaaaaa"
        )
        self.lbl_info.pack(side=tk.RIGHT, padx=20, pady=12)
        
        # === CORPO CENTRAL (Grid de Colunas) ===
        self.body_frame = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        self.body_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))
        
        self.left_col = ctk.CTkFrame(self.body_frame, fg_color="transparent", width=380)
        self.left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        self.left_col.pack_propagate(False)
        
        self.right_col = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # ==========================================
        # === COLUNA ESQUERDA (Status e Atributos - Divisão 50/50) ===
        # ==========================================
        
        # 1. Bloco de Combate (50% da altura)
        self.combat_card = ctk.CTkFrame(
            self.left_col,
            fg_color="#1e1e1e",
            border_color=self.current_color,
            border_width=2,
            corner_radius=10
        )
        self.combat_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.color_framed_widgets.append(self.combat_card)
        
        # Grid para CA, Iniciativa e Deslocamento
        stats_subframe = ctk.CTkFrame(self.combat_card, fg_color="transparent")
        stats_subframe.pack(fill=tk.X, pady=(10, 5), padx=10)
        
        self.create_stat_widget(stats_subframe, "CA", self.sheet.get("combate", {}).get("ca", 10)).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.create_stat_widget(stats_subframe, "INICIATIVA", f"+{self.sheet.get('combate', {}).get('iniciativa', 0)}").pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        self.create_stat_widget(stats_subframe, "DESLOCAMENTO", self.sheet.get("combate", {}).get("deslocamento", "9m")).pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        # Seção de Pontos de Vida (HP)
        self.hp_subframe = ctk.CTkFrame(self.combat_card, fg_color="#151515", corner_radius=6)
        self.hp_subframe.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 15))
        
        hp_title = ctk.CTkLabel(self.hp_subframe, text="PONTOS DE VIDA", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        hp_title.pack(pady=(12, 2))
        
        hp_atual = self.sheet.get("combate", {}).get("hp_atual", 12)
        hp_max = self.sheet.get("combate", {}).get("hp_max", 12)
        self.hp_val_lbl = ctk.CTkLabel(self.hp_subframe, text=f"{hp_atual} / {hp_max}", font=ctk.CTkFont(size=24, weight="bold"), text_color="#ffffff")
        self.hp_val_lbl.pack(pady=2)
        
        self.hp_bar = ctk.CTkProgressBar(self.hp_subframe, fg_color="#2b2b2b", progress_color="#444444", width=280, height=10)
        self.hp_bar.pack(pady=4)
        self.hp_bar.set(hp_atual / max(1, hp_max))
        
        # Controles de HP (Grayscale Neutro)
        hp_ctrls = ctk.CTkFrame(self.hp_subframe, fg_color="transparent")
        hp_ctrls.pack(pady=(8, 12))
        
        ctk.CTkButton(hp_ctrls, text="-5", width=35, height=22, fg_color="#2b2b2b", hover_color="#3e3e3e", font=ctk.CTkFont(size=10), command=lambda: self.adjust_hp(-5)).pack(side=tk.LEFT, padx=3)
        ctk.CTkButton(hp_ctrls, text="-1", width=35, height=22, fg_color="#2b2b2b", hover_color="#3e3e3e", font=ctk.CTkFont(size=10), command=lambda: self.adjust_hp(-1)).pack(side=tk.LEFT, padx=3)
        
        self.hp_input = ctk.CTkEntry(hp_ctrls, width=55, height=22, fg_color="#121212", border_color="#333333", font=ctk.CTkFont(size=11), placeholder_text="Val")
        self.hp_input.pack(side=tk.LEFT, padx=4)
        self.hp_input.bind("<Return>", lambda e: (self.set_hp_fine(), self.root.focus()))
        
        ctk.CTkButton(hp_ctrls, text="Def", width=35, height=22, fg_color="#2b2b2b", hover_color="#3e3e3e", font=ctk.CTkFont(size=10), command=self.set_hp_fine).pack(side=tk.LEFT, padx=3)
        
        ctk.CTkButton(hp_ctrls, text="+1", width=35, height=22, fg_color="#2b2b2b", hover_color="#3e3e3e", font=ctk.CTkFont(size=10), command=lambda: self.adjust_hp(1)).pack(side=tk.LEFT, padx=3)
        ctk.CTkButton(hp_ctrls, text="+5", width=35, height=22, fg_color="#2b2b2b", hover_color="#3e3e3e", font=ctk.CTkFont(size=10), command=lambda: self.adjust_hp(5)).pack(side=tk.LEFT, padx=3)
        
        # 2. Bloco de Atributos (50% da altura)
        self.attr_card = ctk.CTkFrame(
            self.left_col,
            fg_color="#1e1e1e",
            border_color=self.current_color,
            border_width=2,
            corner_radius=10
        )
        self.attr_card.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        self.color_framed_widgets.append(self.attr_card)
        
        attr_title = ctk.CTkLabel(self.attr_card, text="ATRIBUTOS", font=ctk.CTkFont(family="Cinzel", size=13, weight="bold"), text_color="#ffffff")
        attr_title.pack(pady=8)
        
        attr_grid = ctk.CTkFrame(self.attr_card, fg_color="transparent")
        attr_grid.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        
        attrs_list = [
            ("FOR", "forca"), ("DES", "destreza"), ("CON", "constituicao"),
            ("INT", "inteligencia"), ("SAB", "sabedoria"), ("CAR", "carisma")
        ]
        
        for idx, (sigla, key) in enumerate(attrs_list):
            row = idx // 3
            col = idx % 3
            
            card = ctk.CTkFrame(attr_grid, fg_color="#151515", corner_radius=6, height=90)
            card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            card.pack_propagate(False)
            
            attr_grid.grid_columnconfigure(col, weight=1)
            attr_grid.grid_rowconfigure(row, weight=1)
            
            sigla_lbl = ctk.CTkLabel(card, text=sigla, font=ctk.CTkFont(size=10, weight="bold"), text_color="#666666")
            sigla_lbl.pack(pady=(8, 2))
            
            attr_data = self.sheet.get("atributos", {}).get(key, {"valor": 10, "mod": 0})
            val = attr_data.get("valor", 10)
            mod = attr_data.get("mod", 0)
            mod_sign = f"+{mod}" if mod >= 0 else f"{mod}"
            
            # Modificador grande no topo
            mod_lbl = ctk.CTkLabel(card, text=mod_sign, font=ctk.CTkFont(size=20, weight="bold"), text_color="#ffffff")
            mod_lbl.pack(pady=2)
            
            # Valor bruto menor embaixo
            val_lbl = ctk.CTkLabel(card, text=str(val), font=ctk.CTkFont(size=11), text_color="#888888")
            val_lbl.pack(pady=(2, 8))
            
        # ============================================
        # === COLUNA DIREITA (Abas Principais/Tabs) ===
        # ============================================
        self.right_tab_container = ctk.CTkFrame(
            self.right_col,
            fg_color="#1e1e1e",
            border_color=self.current_color,
            border_width=2,
            corner_radius=10
        )
        self.right_tab_container.pack(fill=tk.BOTH, expand=True)
        self.color_framed_widgets.append(self.right_tab_container)
        
        # Barra de Abas Principais (Horizontal)
        self.main_tab_header = ctk.CTkFrame(self.right_tab_container, fg_color="#151515", height=40, corner_radius=0)
        self.main_tab_header.pack(fill=tk.X, side=tk.TOP)
        
        self.main_tabs = ["Testes", "Detalhes", "Ações", "Inventário", "Extra"]
        self.active_main_tab = "Testes"
        self.main_tab_views = {}
        
        # Grid para 5 colunas iguais
        for i in range(5):
            self.main_tab_header.grid_columnconfigure(i, weight=1)
        self.main_tab_header.grid_rowconfigure(0, weight=1)
        self.main_tab_header.grid_rowconfigure(1, weight=0)
        
        for idx, name in enumerate(self.main_tabs):
            btn = ctk.CTkButton(
                self.main_tab_header,
                text=name.upper(),
                fg_color="transparent",
                hover_color="#1e1e1e",
                text_color="#ffffff",
                font=ctk.CTkFont(size=10, weight="bold"),
                corner_radius=0,
                width=10,
                command=lambda n=name: self.switch_main_tab(n)
            )
            btn.grid(row=0, column=idx, sticky="nsew")
            
            indicator = ctk.CTkFrame(self.main_tab_header, height=3, fg_color="transparent", corner_radius=0)
            indicator.grid(row=1, column=idx, sticky="ew")
            self.main_tab_indicators[name] = indicator
            
        self.main_content_area = ctk.CTkFrame(self.right_tab_container, fg_color="transparent")
        self.main_content_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)
        
        self.create_all_main_tab_contents()
        self.switch_main_tab("Testes")
        
    def create_stat_widget(self, parent, label_text, value):
        frame = ctk.CTkFrame(parent, fg_color="#151515", corner_radius=6)
        lbl = ctk.CTkLabel(frame, text=label_text, font=ctk.CTkFont(size=9, weight="bold"), text_color="#666666")
        lbl.pack(pady=(4, 0))
        val_lbl = ctk.CTkLabel(frame, text=str(value), font=ctk.CTkFont(size=18, weight="bold"), text_color="#ffffff")
        val_lbl.pack(pady=(0, 4))
        return frame
        
    def create_all_main_tab_contents(self):
        # ----------------------------------------------------
        # 1. ABA: TESTES
        # ----------------------------------------------------
        self.view_testes = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Testes"] = self.view_testes
        
        self.sub_header_testes = ctk.CTkFrame(self.view_testes, fg_color="#151515", height=32, corner_radius=5)
        self.sub_header_testes.pack(fill=tk.X, pady=(0, 10))
        
        self.sub_testes_views = {}
        self.active_sub_testes = "Perícias"
        self.create_sub_tab_button(self.sub_header_testes, "Perícias", 0, lambda: self.switch_sub_testes("Perícias"))
        self.create_sub_tab_button(self.sub_header_testes, "Resistências", 1, lambda: self.switch_sub_testes("Resistências"))
        
        self.sub_content_testes = ctk.CTkFrame(self.view_testes, fg_color="transparent")
        self.sub_content_testes.pack(fill=tk.BOTH, expand=True)
        
        # Sub-aba: Perícias
        self.view_sub_pericias = ctk.CTkScrollableFrame(self.sub_content_testes, fg_color="#151515")
        self.sub_testes_views["Perícias"] = self.view_sub_pericias
        
        pericias_dict = self.sheet.get("pericias", {})
        for name, data in pericias_dict.items():
            row = ctk.CTkFrame(self.view_sub_pericias, fg_color="#1e1e1e", height=30)
            row.pack(fill=tk.X, pady=2, padx=5)
            
            prof = data.get("proficiente", False)
            dot = "●" if prof else "○"
            dot_color = self.current_color if prof else "#444444"
            
            lbl_dot = ctk.CTkLabel(row, text=dot, font=ctk.CTkFont(size=14), text_color=dot_color)
            lbl_dot.pack(side=tk.LEFT, padx=10)
            if prof:
                self.color_framed_widgets.append(lbl_dot)
            
            lbl_name = ctk.CTkLabel(row, text=name.upper(), font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff")
            lbl_name.pack(side=tk.LEFT)
            
            bonus = data.get("bonus", 0)
            bonus_sign = f"+{bonus}" if bonus >= 0 else f"{bonus}"
            lbl_bonus = ctk.CTkLabel(row, text=bonus_sign, font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
            lbl_bonus.pack(side=tk.RIGHT, padx=15)
            
        # Sub-aba: Resistências
        self.view_sub_resistencias = ctk.CTkScrollableFrame(self.sub_content_testes, fg_color="#151515")
        self.sub_testes_views["Resistências"] = self.view_sub_resistencias
        
        resist_dict = self.sheet.get("resistencia", {})
        for name, data in resist_dict.items():
            row = ctk.CTkFrame(self.view_sub_resistencias, fg_color="#1e1e1e", height=35)
            row.pack(fill=tk.X, pady=3, padx=5)
            
            prof = data.get("proficiente", False)
            dot = "●" if prof else "○"
            dot_color = self.current_color if prof else "#444444"
            
            lbl_dot = ctk.CTkLabel(row, text=dot, font=ctk.CTkFont(size=16), text_color=dot_color)
            lbl_dot.pack(side=tk.LEFT, padx=10)
            if prof:
                self.color_framed_widgets.append(lbl_dot)
                
            lbl_name = ctk.CTkLabel(row, text=f"TESTE DE RESISTÊNCIA DE {name.upper()}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#ffffff")
            lbl_name.pack(side=tk.LEFT)
            
            bonus = data.get("bonus", 0)
            bonus_sign = f"+{bonus}" if bonus >= 0 else f"{bonus}"
            lbl_bonus = ctk.CTkLabel(row, text=bonus_sign, font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888")
            lbl_bonus.pack(side=tk.RIGHT, padx=15)

        # ----------------------------------------------------
        # 2. ABA: DETALHES
        # ----------------------------------------------------
        self.view_detalhes = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Detalhes"] = self.view_detalhes
        
        self.sub_header_detalhes = ctk.CTkFrame(self.view_detalhes, fg_color="#151515", height=32, corner_radius=5)
        self.sub_header_detalhes.pack(fill=tk.X, pady=(0, 10))
        
        self.sub_detalhes_views = {}
        self.active_sub_detalhes = "Características"
        self.create_sub_tab_button(self.sub_header_detalhes, "Características", 0, lambda: self.switch_sub_detalhes("Características"))
        self.create_sub_tab_button(self.sub_header_detalhes, "Outros", 1, lambda: self.switch_sub_detalhes("Outros"))
        
        self.sub_content_detalhes = ctk.CTkFrame(self.view_detalhes, fg_color="transparent")
        self.sub_content_detalhes.pack(fill=tk.BOTH, expand=True)
        
        # Sub-aba: Características
        self.view_sub_caract = ctk.CTkScrollableFrame(self.sub_content_detalhes, fg_color="#151515")
        self.sub_detalhes_views["Características"] = self.view_sub_caract
        
        caracteristicas = self.sheet.get("caracteristicas", [])
        for feat in caracteristicas:
            row = ctk.CTkFrame(self.view_sub_caract, fg_color="#1e1e1e")
            row.pack(fill=tk.X, pady=4, padx=5)
            
            title = ctk.CTkLabel(row, text=feat.get("nome", "Habilidade").upper(), font=ctk.CTkFont(size=12, weight="bold"), text_color="#ffffff")
            title.pack(anchor=tk.W, padx=12, pady=(6, 2))
            
            desc = ctk.CTkLabel(row, text=feat.get("detalhes", ""), font=ctk.CTkFont(size=11), text_color="#888888", wraplength=450, justify=tk.LEFT)
            desc.pack(anchor=tk.W, padx=12, pady=(0, 6))
            
        # Sub-aba: Outros
        self.view_sub_outros = ctk.CTkScrollableFrame(self.sub_content_detalhes, fg_color="#151515")
        self.sub_detalhes_views["Outros"] = self.view_sub_outros
        
        lang_title = ctk.CTkLabel(self.view_sub_outros, text="IDIOMAS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888")
        lang_title.pack(anchor=tk.W, padx=10, pady=(10, 5))
        
        idiomas = self.sheet.get("idiomas", [])
        for lang in idiomas:
            lang_row = ctk.CTkFrame(self.view_sub_outros, fg_color="#1e1e1e", height=26)
            lang_row.pack(fill=tk.X, pady=2, padx=5)
            ctk.CTkLabel(lang_row, text=lang, font=ctk.CTkFont(size=11), text_color="#ffffff").pack(side=tk.LEFT, padx=15)
            
        prof_title = ctk.CTkLabel(self.view_sub_outros, text="PROFICIÊNCIAS", font=ctk.CTkFont(size=12, weight="bold"), text_color="#888888")
        prof_title.pack(anchor=tk.W, padx=10, pady=(15, 5))
        
        proficiencias = self.sheet.get("proficiencias", [])
        for prof in proficiencias:
            prof_row = ctk.CTkFrame(self.view_sub_outros, fg_color="#1e1e1e", height=26)
            prof_row.pack(fill=tk.X, pady=2, padx=5)
            ctk.CTkLabel(prof_row, text=prof, font=ctk.CTkFont(size=11), text_color="#ffffff").pack(side=tk.LEFT, padx=15)

        # ----------------------------------------------------
        # 3. ABA: AÇÕES
        # ----------------------------------------------------
        self.view_acoes = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Ações"] = self.view_acoes
        
        self.sub_header_acoes = ctk.CTkFrame(self.view_acoes, fg_color="#151515", height=32, corner_radius=5)
        self.sub_header_acoes.pack(fill=tk.X, pady=(0, 10))
        
        self.sub_acoes_views = {}
        self.active_sub_acoes = "Ataques"
        self.create_sub_tab_button(self.sub_header_acoes, "Ataques", 0, lambda: self.switch_sub_acoes("Ataques"))
        self.create_sub_tab_button(self.sub_header_acoes, "Magias", 1, lambda: self.switch_sub_acoes("Magias"))
        
        self.sub_content_acoes = ctk.CTkFrame(self.view_acoes, fg_color="transparent")
        self.sub_content_acoes.pack(fill=tk.BOTH, expand=True)
        
        # Sub-aba: Ataques
        self.view_sub_ataques = ctk.CTkFrame(self.sub_content_acoes, fg_color="transparent")
        self.sub_acoes_views["Ataques"] = self.view_sub_ataques
        self.populate_sub_ataques()
            
        # Sub-aba: Magias
        self.view_sub_magias = ctk.CTkFrame(self.sub_content_acoes, fg_color="transparent")
        self.sub_acoes_views["Magias"] = self.view_sub_magias
        self.populate_sub_magias()

        # ----------------------------------------------------
        # 4. ABA: INVENTÁRIO (Com Edição Inline)
        # ----------------------------------------------------
        self.view_inventario = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Inventário"] = self.view_inventario
        
        # Campo para adicionar item
        add_item_frame = ctk.CTkFrame(self.view_inventario, fg_color="transparent")
        add_item_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.item_entry = ctk.CTkEntry(add_item_frame, placeholder_text="Conceder novo item ao inventário...", fg_color="#121212", border_color="#333333")
        self.item_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.item_entry.bind("<Return>", lambda e: (self.add_mock_item(), self.root.focus()))
        
        add_btn = ctk.CTkButton(add_item_frame, text="Adicionar", fg_color="#2b2b2b", hover_color="#3e3e3e", width=80, command=self.add_mock_item)
        add_btn.pack(side=tk.RIGHT)
        
        # Lista scrollable de itens
        self.inv_scroll = ctk.CTkScrollableFrame(self.view_inventario, fg_color="#151515")
        self.inv_scroll.pack(fill=tk.BOTH, expand=True)
        self.populate_mock_inventory()

        # ----------------------------------------------------
        # 5. ABA: EXTRA (Edição inline de recursos)
        # ----------------------------------------------------
        self.view_extra = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Extra"] = self.view_extra
        
        self.sub_header_extra = ctk.CTkFrame(self.view_extra, fg_color="#151515", height=32, corner_radius=5)
        self.sub_header_extra.pack(fill=tk.X, pady=(0, 10))
        
        self.sub_extra_views = {}
        self.active_sub_extra = ""
        
        # Suporta tanto "extra" quanto "custom"
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        self.custom_keys_mapping = {"cartas_destino": "Cartas de Destino"}
        
        for idx, key in enumerate(custom_data.keys()):
            readable_name = self.custom_keys_mapping.get(key, key.replace("_", " ").title())
            if not self.active_sub_extra:
                self.active_sub_extra = readable_name
                
            self.create_sub_tab_button(
                self.sub_header_extra, 
                readable_name, 
                idx,
                lambda n=readable_name: self.switch_sub_extra(n)
            )
            
            sub_view = ctk.CTkFrame(self.view_extra, fg_color="transparent")
            self.sub_extra_views[readable_name] = sub_view
            self.populate_sub_extra_tab(key)

    # --- FUNÇÕES AUXILIARES DE SUB-ABAS (GRID) ---
    def create_sub_tab_button(self, parent, name, column_idx, command):
        parent.grid_columnconfigure(column_idx, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=0)
        
        btn = ctk.CTkButton(
            parent,
            text=name.upper(),
            fg_color="transparent",
            hover_color="#1e1e1e",
            text_color="#aaaaaa",
            font=ctk.CTkFont(size=9, weight="bold"),
            corner_radius=0,
            width=10,
            command=command
        )
        btn.grid(row=0, column=column_idx, sticky="nsew")
        
        indicator = ctk.CTkFrame(parent, height=2, fg_color="transparent", corner_radius=0)
        indicator.grid(row=1, column=column_idx, sticky="ew")
        self.sub_tab_indicators[name] = indicator
        
    def switch_sub_testes(self, sub_name):
        self.active_sub_testes = sub_name
        for name, view in self.sub_testes_views.items():
            if name == sub_name:
                view.pack(fill=tk.BOTH, expand=True)
                self.sub_tab_indicators[name].configure(fg_color=self.current_color)
            else:
                view.pack_forget()
                self.sub_tab_indicators[name].configure(fg_color="transparent")
                
    def switch_sub_detalhes(self, sub_name):
        self.active_sub_detalhes = sub_name
        for name, view in self.sub_detalhes_views.items():
            if name == sub_name:
                view.pack(fill=tk.BOTH, expand=True)
                self.sub_tab_indicators[name].configure(fg_color=self.current_color)
            else:
                view.pack_forget()
                self.sub_tab_indicators[name].configure(fg_color="transparent")
                
    def switch_sub_acoes(self, sub_name):
        self.active_sub_acoes = sub_name
        for name, view in self.sub_acoes_views.items():
            if name == sub_name:
                view.pack(fill=tk.BOTH, expand=True)
                self.sub_tab_indicators[name].configure(fg_color=self.current_color)
            else:
                view.pack_forget()
                self.sub_tab_indicators[name].configure(fg_color="transparent")
                
    def switch_sub_extra(self, sub_name):
        self.active_sub_extra = sub_name
        for name, view in self.sub_extra_views.items():
            if name == sub_name:
                view.pack(fill=tk.BOTH, expand=True)
                self.sub_tab_indicators[name].configure(fg_color=self.current_color)
            else:
                view.pack_forget()
                self.sub_tab_indicators[name].configure(fg_color="transparent")
                
    # --- FUNÇÃO DE SWITCH DE ABA PRINCIPAL ---
    def switch_main_tab(self, tab_name):
        self.active_main_tab = tab_name
        
        # Oculta todas as abas principais
        for name, view in self.main_tab_views.items():
            if name == tab_name:
                view.pack(fill=tk.BOTH, expand=True)
                self.main_tab_indicators[name].configure(fg_color=self.current_color)
            else:
                view.pack_forget()
                self.main_tab_indicators[name].configure(fg_color="transparent")
                
        # Garante que as sub-abas sejam ativadas corretamente ao entrar
        if tab_name == "Testes":
            self.switch_sub_testes(self.active_sub_testes)
        elif tab_name == "Detalhes":
            self.switch_sub_detalhes(self.active_sub_detalhes)
        elif tab_name == "Ações":
            self.switch_sub_acoes(self.active_sub_acoes)
        elif tab_name == "Extra":
            self.switch_sub_extra(self.active_sub_extra)

    # --- INVENTÁRIO POPULATE E AÇÕES ---
    def populate_mock_inventory(self):
        for child in self.inv_scroll.winfo_children():
            child.destroy()
            
        items = self.sheet.get("inventario", [])
        for idx, item in enumerate(items):
            row = ctk.CTkFrame(self.inv_scroll, fg_color="#1e1e1e", height=32)
            row.pack(fill=tk.X, pady=2, padx=5)
            
            # Campo de entrada de texto (Entry) sem bordas para edição inline
            entry = ctk.CTkEntry(
                row, 
                fg_color="transparent", 
                border_width=0, 
                text_color="#ffffff",
                font=ctk.CTkFont(size=12)
            )
            entry.insert(0, item)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
            
            # Salva a edição ao apertar Enter ou sair da caixa (desfocar)
            entry.bind("<Return>", lambda e, i=idx, ent=entry: (self.save_inventory_edit(i, ent.get()), self.root.focus()))
            entry.bind("<FocusOut>", lambda e, i=idx, ent=entry: self.save_inventory_edit(i, ent.get()))
            
            del_btn = ctk.CTkButton(
                row, 
                text="X", 
                width=24, 
                height=20, 
                fg_color="#2b2b2b", 
                hover_color="#a83232", 
                command=lambda name=item: self.remove_mock_item(name)
            )
            del_btn.pack(side=tk.RIGHT, padx=5, pady=5)
            
    def save_inventory_edit(self, idx, new_text):
        new_text = new_text.strip()
        if new_text and idx < len(self.sheet["inventario"]):
            self.sheet["inventario"][idx] = new_text
            self.save_to_disk_mock()
            
    def add_mock_item(self):
        item = self.item_entry.get().strip()
        if item:
            self.sheet.setdefault("inventario", []).append(item)
            self.item_entry.delete(0, tk.END)
            self.populate_mock_inventory()
            self.save_to_disk_mock()
            
    def remove_mock_item(self, item):
        if "inventario" in self.sheet and item in self.sheet["inventario"]:
            self.sheet["inventario"].remove(item)
            self.populate_mock_inventory()
            self.save_to_disk_mock()

    # --- SALVAR ALTERAÇÃO DE RECURSOS EXTRA INLINE ---
    def save_extra_value_edit(self, key, item_idx, new_val):
        new_val = new_val.strip()
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        category_data = custom_data.get(key, {})
        
        items_list = []
        if isinstance(category_data, list):
            items_list = category_data
        elif isinstance(category_data, dict):
            items_list = category_data.get("lista", [])
            
        if item_idx < len(items_list):
            items_list[item_idx]["valor_atual"] = new_val
            self.save_to_disk_mock()

    # --- POPULATE E AÇÕES DA ABA EXTRA (RECURSOS E CARTAS DE DESTINO) ---
    def populate_sub_extra_tab(self, key):
        readable_name = self.custom_keys_mapping.get(key, key.replace("_", " ").title())
        sub_view = self.sub_extra_views[readable_name]
        
        # Limpa widgets existentes
        for child in sub_view.winfo_children():
            child.destroy()
            
        # Limpa referências a widgets destruídos
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
            
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        category_data = custom_data.get(key, {})
        
        if key == "cartas_destino":
            max_cards = category_data.get("maximo", 3)
            cards_list = category_data.get("lista", [])
            curr_cards = len(cards_list)
            
            # Painel de controle superior (não rola)
            ctrl_frame = ctk.CTkFrame(sub_view, fg_color="transparent")
            ctrl_frame.pack(fill=tk.X, pady=(0, 10))
            
            # Indicador de atual/maximo
            count_lbl = ctk.CTkLabel(
                ctrl_frame, 
                text=f"CARTAS: {curr_cards} / {max_cards}", 
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#ffffff"
            )
            count_lbl.pack(side=tk.LEFT, padx=(5, 15))
            
            # Campo de entrada: Nome
            name_entry = ctk.CTkEntry(
                ctrl_frame, 
                placeholder_text="Nome da carta...", 
                fg_color="#121212", 
                border_color="#333333",
                height=26,
                font=ctk.CTkFont(size=11)
            )
            name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            # Campo de entrada: Efeito
            effect_entry = ctk.CTkEntry(
                ctrl_frame, 
                placeholder_text="Efeito/detalhes...", 
                fg_color="#121212", 
                border_color="#333333",
                height=26,
                font=ctk.CTkFont(size=11)
            )
            effect_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            # Botão Adicionar
            add_btn = ctk.CTkButton(
                ctrl_frame, 
                text="Adicionar", 
                fg_color="#2b2b2b", 
                hover_color="#3e3e3e", 
                width=80,
                height=26,
                font=ctk.CTkFont(size=11),
                command=lambda: self.add_mock_card(key, name_entry, effect_entry)
            )
            add_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            # Desativa botão e campos se estiver cheio
            if curr_cards >= max_cards:
                add_btn.configure(state="disabled", fg_color="#1a1a1a", text_color="#555555")
                name_entry.configure(state="disabled")
                effect_entry.configure(state="disabled")
                
            # Atalho de Enter (Return) nos inputs
            name_entry.bind("<Return>", lambda e: add_btn.invoke() if curr_cards < max_cards else None)
            effect_entry.bind("<Return>", lambda e: add_btn.invoke() if curr_cards < max_cards else None)
            
            # Scrollable frame para a lista de cartas
            scroll_frame = ctk.CTkScrollableFrame(sub_view, fg_color="#151515")
            scroll_frame.pack(fill=tk.BOTH, expand=True)
            
            for item_idx, item_obj in enumerate(cards_list):
                row = ctk.CTkFrame(scroll_frame, fg_color="#1e1e1e")
                row.pack(fill=tk.X, pady=4, padx=5)
                
                nome = item_obj.get("nome", "").upper()
                efeito = item_obj.get("efeito", "")
                
                # Container para textos
                text_container = ctk.CTkFrame(row, fg_color="transparent")
                text_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=6)
                
                title = ctk.CTkLabel(text_container, text=nome, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.current_color)
                title.pack(anchor=tk.W)
                self.color_framed_widgets.append(title)
                
                desc = ctk.CTkLabel(text_container, text=efeito, font=ctk.CTkFont(size=11), text_color="#888888", wraplength=400, justify=tk.LEFT)
                desc.pack(anchor=tk.W, pady=(2, 0))
                
                # Botão Deletar (X)
                del_btn = ctk.CTkButton(
                    row, 
                    text="X", 
                    width=24, 
                    height=20, 
                    fg_color="#2b2b2b", 
                    hover_color="#a83232", 
                    command=lambda idx=item_idx: self.remove_mock_card(key, idx)
                )
                del_btn.pack(side=tk.RIGHT, padx=10, pady=10)
                
        else:
            # Layout padrão para recursos gerais (como recursos de classe)
            scroll_frame = ctk.CTkScrollableFrame(sub_view, fg_color="#151515")
            scroll_frame.pack(fill=tk.BOTH, expand=True)
            
            items_list = []
            if isinstance(category_data, list):
                items_list = category_data
            elif isinstance(category_data, dict):
                items_list = category_data.get("lista", [])
                
            for item_idx, item_obj in enumerate(items_list):
                row = ctk.CTkFrame(scroll_frame, fg_color="#1e1e1e")
                row.pack(fill=tk.X, pady=4, padx=5)
                
                if isinstance(item_obj, dict):
                    nome = item_obj.get("nome", "").upper()
                    
                    title = ctk.CTkLabel(row, text=nome, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.current_color)
                    title.pack(anchor=tk.W, padx=12, pady=(6, 2))
                    self.color_framed_widgets.append(title)
                    
                    val_at = item_obj.get("valor_atual")
                    val_max = item_obj.get("valor_maximo")
                    detalhes = item_obj.get("efeito", item_obj.get("detalhes", ""))
                    
                    if val_at is not None and val_max is not None:
                        val_row = ctk.CTkFrame(row, fg_color="transparent")
                        val_row.pack(anchor=tk.W, padx=12, pady=2)
                        
                        ctk.CTkLabel(val_row, text="Valor: ", font=ctk.CTkFont(size=11), text_color="#aaaaaa").pack(side=tk.LEFT)
                        
                        val_entry = ctk.CTkEntry(
                            val_row, 
                            width=35, 
                            height=20, 
                            fg_color="#121212", 
                            border_color="#333333", 
                            font=ctk.CTkFont(size=10)
                        )
                        val_entry.insert(0, str(val_at))
                        val_entry.pack(side=tk.LEFT, padx=3)
                        
                        val_entry.bind("<Return>", lambda e, k=key, i_idx=item_idx, entry=val_entry: (self.save_extra_value_edit(k, i_idx, entry.get()), self.root.focus()))
                        val_entry.bind("<FocusOut>", lambda e, k=key, i_idx=item_idx, entry=val_entry: (self.save_extra_value_edit(k, i_idx, entry.get()), self.root.focus()))
                        
                        ctk.CTkLabel(val_row, text=f"/ {val_max}", font=ctk.CTkFont(size=11), text_color="#aaaaaa").pack(side=tk.LEFT, padx=3)
                        
                        desc = ctk.CTkLabel(row, text=detalhes, font=ctk.CTkFont(size=11), text_color="#888888", wraplength=450, justify=tk.LEFT)
                        desc.pack(anchor=tk.W, padx=12, pady=(2, 6))
                    else:
                        desc = ctk.CTkLabel(row, text=detalhes, font=ctk.CTkFont(size=11), text_color="#888888", wraplength=450, justify=tk.LEFT)
                        desc.pack(anchor=tk.W, padx=12, pady=(0, 6))
                else:
                    lbl = ctk.CTkLabel(row, text=str(item_obj), font=ctk.CTkFont(size=12), text_color="#ffffff")
                    lbl.pack(anchor=tk.W, padx=12, pady=8)

    def add_mock_card(self, key, name_entry, effect_entry):
        name = name_entry.get().strip()
        effect = effect_entry.get().strip()
        if not name:
            return
            
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        category_data = custom_data.get(key, {})
        max_cards = category_data.get("maximo", 3)
        cards_list = category_data.setdefault("lista", [])
        
        if len(cards_list) < max_cards:
            cards_list.append({"nome": name, "efeito": effect})
            self.save_to_disk_mock()
            self.populate_sub_extra_tab(key)

    def remove_mock_card(self, key, item_idx):
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        category_data = custom_data.get(key, {})
        cards_list = category_data.get("lista", [])
        
        if item_idx < len(cards_list):
            cards_list.pop(item_idx)
            self.save_to_disk_mock()
            self.populate_sub_extra_tab(key)

    # --- POPULATE E AÇÕES DE ATAQUES CUSTOMIZADOS ---
    def populate_sub_ataques(self):
        sub_view = self.view_sub_ataques
        
        # Limpa widgets existentes
        for child in sub_view.winfo_children():
            child.destroy()
            
        # Limpa referências a widgets destruídos
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        
        # Painel de controle superior para adicionar novo ataque
        ctrl_frame = ctk.CTkFrame(sub_view, fg_color="transparent")
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Campo de entrada: Nome do Ataque
        atk_name_entry = ctk.CTkEntry(
            ctrl_frame, 
            placeholder_text="Nome do novo ataque...", 
            fg_color="#121212", 
            border_color="#333333",
            height=26,
            font=ctk.CTkFont(size=11)
        )
        atk_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # Campo de entrada: Descrição (bônus, dano, etc)
        atk_desc_entry = ctk.CTkEntry(
            ctrl_frame, 
            placeholder_text="Descrição (ex: Bônus: +5 | Dano: 2d6+3)...", 
            fg_color="#121212", 
            border_color="#333333",
            height=26,
            font=ctk.CTkFont(size=11)
        )
        atk_desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # Botão Adicionar
        add_btn = ctk.CTkButton(
            ctrl_frame, 
            text="Adicionar", 
            fg_color="#2b2b2b", 
            hover_color="#3e3e3e", 
            width=80,
            height=26,
            font=ctk.CTkFont(size=11),
            command=lambda: self.add_mock_attack(atk_name_entry, atk_desc_entry)
        )
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Bind do Enter nos inputs para adicionar
        atk_name_entry.bind("<Return>", lambda e: add_btn.invoke())
        atk_desc_entry.bind("<Return>", lambda e: add_btn.invoke())
        
        # Scrollable frame para listar os ataques
        scroll_frame = ctk.CTkScrollableFrame(sub_view, fg_color="#151515")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        ataques = self.sheet.get("ataques", [])
        for idx, atk in enumerate(ataques):
            row = ctk.CTkFrame(scroll_frame, fg_color="#1e1e1e")
            row.pack(fill=tk.X, pady=4, padx=5)
            
            # Container para os inputs editáveis
            inputs_container = ctk.CTkFrame(row, fg_color="transparent")
            inputs_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=4)
            
            # Nome do ataque editável
            name_entry = ctk.CTkEntry(
                inputs_container,
                fg_color="transparent",
                border_width=0,
                text_color=self.current_color,
                font=ctk.CTkFont(size=12, weight="bold"),
                height=22
            )
            name_entry.insert(0, atk.get("nome", "Ataque").upper())
            name_entry.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(2, 0))
            self.color_framed_widgets.append(name_entry)
            
            # Descrição do ataque editável
            desc_entry = ctk.CTkEntry(
                inputs_container,
                fg_color="transparent",
                border_width=0,
                text_color="#888888",
                font=ctk.CTkFont(size=11),
                height=20
            )
            desc_entry.insert(0, atk.get("descricao", ""))
            desc_entry.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(0, 2))
            
            # Bindings de salvar ao teclar Enter ou tirar o foco
            name_entry.bind("<Return>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: (self.save_attack_edit(i, n_ent.get(), d_ent.get()), self.root.focus()))
            name_entry.bind("<FocusOut>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: self.save_attack_edit(i, n_ent.get(), d_ent.get()))
            
            desc_entry.bind("<Return>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: (self.save_attack_edit(i, n_ent.get(), d_ent.get()), self.root.focus()))
            desc_entry.bind("<FocusOut>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: self.save_attack_edit(i, n_ent.get(), d_ent.get()))
            
            # Botão Deletar (X)
            del_btn = ctk.CTkButton(
                row, 
                text="X", 
                width=24, 
                height=20, 
                fg_color="#2b2b2b", 
                hover_color="#a83232", 
                command=lambda i=idx: self.remove_mock_attack(i)
            )
            del_btn.pack(side=tk.RIGHT, padx=10, pady=10)

    def save_attack_edit(self, idx, new_name, new_desc):
        new_name = new_name.strip()
        new_desc = new_desc.strip()
        ataques = self.sheet.setdefault("ataques", [])
        if idx < len(ataques):
            ataques[idx]["nome"] = new_name
            ataques[idx]["descricao"] = new_desc
            self.save_to_disk_mock()
            
    def add_mock_attack(self, name_entry, desc_entry):
        name = name_entry.get().strip()
        desc = desc_entry.get().strip()
        if not name:
            return
            
        self.sheet.setdefault("ataques", []).append({
            "nome": name,
            "descricao": desc
        })
        name_entry.delete(0, tk.END)
        desc_entry.delete(0, tk.END)
        self.populate_sub_ataques()
        self.save_to_disk_mock()
        
    def remove_mock_attack(self, idx):
        ataques = self.sheet.get("ataques", [])
        if idx < len(ataques):
            ataques.pop(idx)
            self.populate_sub_ataques()
            self.save_to_disk_mock()

    # --- POPULATE E AÇÕES DE MAGIAS CUSTOMIZADAS E SLOTS ---
    def populate_sub_magias(self):
        sub_view = self.view_sub_magias
        
        # Limpa widgets anteriores
        for child in sub_view.winfo_children():
            child.destroy()
            
        # Limpa referências a widgets destruídos
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        
        mag_data = self.sheet.setdefault("magias", {})
        
        # 1. Faixa de Informações Gerais (Classe, CD, Bônus)
        info_conj = ctk.CTkFrame(sub_view, fg_color="#1e1e1e")
        info_conj.pack(fill=tk.X, pady=(5, 10), padx=5)
        
        info_str = f"CLASSE: {mag_data.get('classe_conjurador', 'Nenhuma').upper()}  |  CD: {mag_data.get('cd_salvamento', 8)}  |  BÔNUS: +{mag_data.get('bonus_ataque', 0)}"
        lbl_info_conj = ctk.CTkLabel(info_conj, text=info_str, font=ctk.CTkFont(size=10, weight="bold"), text_color="#aaaaaa")
        lbl_info_conj.pack(pady=8, padx=10)
        
        # 2. Espaços de Magia
        slots_title = ctk.CTkLabel(sub_view, text="ESPAÇOS DE MAGIA", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        slots_title.pack(anchor=tk.W, padx=10, pady=(5, 2))
        
        slots_frame_top = ctk.CTkFrame(sub_view, fg_color="transparent")
        slots_frame_top.pack(fill=tk.X, pady=(0, 4), padx=5)
        
        slots_frame_bottom = ctk.CTkFrame(sub_view, fg_color="transparent")
        slots_frame_bottom.pack(fill=tk.X, pady=(0, 10), padx=5)
        
        slots_data = mag_data.setdefault("slots", {})
        
        for slot_idx in range(1, 10):
            slot_lvl = str(slot_idx)
            details = slots_data.setdefault(slot_lvl, {"atual": 0, "max": 0})
            
            try:
                atual_val = int(details.get("atual", 0))
            except ValueError:
                atual_val = 0
            try:
                max_val = int(details.get("max", 0))
            except ValueError:
                max_val = 0
            
            # Determina a linha correta dos slots (1-5 em cima, 6-9 em baixo)
            parent_frame = slots_frame_top if slot_idx <= 5 else slots_frame_bottom
            
            # Slot Box widget
            slot_box = ctk.CTkFrame(parent_frame, fg_color="#1e1e1e", width=70, height=52)
            slot_box.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            slot_box.pack_propagate(False)
            
            ctk.CTkLabel(slot_box, text=f"SLOT {slot_lvl}", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(pady=(4, 0))
            
            # Frame interno para inputs
            val_frame = ctk.CTkFrame(slot_box, fg_color="transparent")
            val_frame.pack(pady=(0, 4))
            
            # Input Atual
            at_entry = ctk.CTkEntry(
                val_frame, 
                width=24, 
                height=18, 
                fg_color="#121212", 
                border_color="#333333", 
                font=ctk.CTkFont(size=10),
                justify="center"
            )
            at_entry.insert(0, str(atual_val))
            at_entry.pack(side=tk.LEFT, padx=1)
            
            ctk.CTkLabel(val_frame, text="/", font=ctk.CTkFont(size=10), text_color="#888888").pack(side=tk.LEFT, padx=1)
            
            # Input Maximo
            mx_entry = ctk.CTkEntry(
                val_frame, 
                width=24, 
                height=18, 
                fg_color="#121212", 
                border_color="#333333", 
                font=ctk.CTkFont(size=10),
                justify="center"
            )
            mx_entry.insert(0, str(max_val))
            mx_entry.pack(side=tk.LEFT, padx=1)
            
            # Bindings de salvamento automático
            at_entry.bind("<Return>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: (self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()), self.root.focus()))
            at_entry.bind("<FocusOut>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()))
            
            mx_entry.bind("<Return>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: (self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()), self.root.focus()))
            mx_entry.bind("<FocusOut>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()))
            
        # 3. Painel para adicionar nova magia
        add_spell_title = ctk.CTkLabel(sub_view, text="LISTA DE TRUQUES E MAGIAS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888")
        add_spell_title.pack(anchor=tk.W, padx=10, pady=(5, 2))
        
        ctrl_frame = ctk.CTkFrame(sub_view, fg_color="transparent")
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        spell_name_entry = ctk.CTkEntry(
            ctrl_frame, 
            placeholder_text="Nome da nova magia...", 
            fg_color="#121212", 
            border_color="#333333",
            height=26,
            font=ctk.CTkFont(size=11)
        )
        spell_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        spell_desc_entry = ctk.CTkEntry(
            ctrl_frame, 
            placeholder_text="Descrição/efeito da magia...", 
            fg_color="#121212", 
            border_color="#333333",
            height=26,
            font=ctk.CTkFont(size=11)
        )
        spell_desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        # Botão Adicionar
        add_btn = ctk.CTkButton(
            ctrl_frame, 
            text="Adicionar", 
            fg_color="#2b2b2b", 
            hover_color="#3e3e3e", 
            width=80,
            height=26,
            font=ctk.CTkFont(size=11),
            command=lambda: self.add_mock_spell(spell_name_entry, spell_desc_entry)
        )
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Bind do Enter
        spell_name_entry.bind("<Return>", lambda e: add_btn.invoke())
        spell_desc_entry.bind("<Return>", lambda e: add_btn.invoke())
        
        # 4. Scrollable frame para listar as magias
        scroll_frame = ctk.CTkScrollableFrame(sub_view, fg_color="#151515")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        magias_lista = mag_data.setdefault("lista", [])
        for idx, spell in enumerate(magias_lista):
            row = ctk.CTkFrame(scroll_frame, fg_color="#1e1e1e")
            row.pack(fill=tk.X, pady=4, padx=5)
            
            inputs_container = ctk.CTkFrame(row, fg_color="transparent")
            inputs_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=4)
            
            name_entry = ctk.CTkEntry(
                inputs_container,
                fg_color="transparent",
                border_width=0,
                text_color=self.current_color,
                font=ctk.CTkFont(size=12, weight="bold"),
                height=22
            )
            name_entry.insert(0, spell.get("nome", "Magia").upper())
            name_entry.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(2, 0))
            self.color_framed_widgets.append(name_entry)
            
            desc_entry = ctk.CTkEntry(
                inputs_container,
                fg_color="transparent",
                border_width=0,
                text_color="#888888",
                font=ctk.CTkFont(size=11),
                height=20
            )
            desc_entry.insert(0, spell.get("descricao", spell.get("detalhes", "")))
            desc_entry.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(0, 2))
            
            name_entry.bind("<Return>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: (self.save_spell_edit(i, n_ent.get(), d_ent.get()), self.root.focus()))
            name_entry.bind("<FocusOut>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: self.save_spell_edit(i, n_ent.get(), d_ent.get()))
            
            desc_entry.bind("<Return>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: (self.save_spell_edit(i, n_ent.get(), d_ent.get()), self.root.focus()))
            desc_entry.bind("<FocusOut>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: self.save_spell_edit(i, n_ent.get(), d_ent.get()))
            
            del_btn = ctk.CTkButton(
                row, 
                text="X", 
                width=24, 
                height=20, 
                fg_color="#2b2b2b", 
                hover_color="#a83232", 
                command=lambda i=idx: self.remove_mock_spell(i)
            )
            del_btn.pack(side=tk.RIGHT, padx=10, pady=10)

    def save_slot_edit(self, slot_lvl, new_atual, new_max):
        try:
            val_at = int(new_atual)
            val_mx = int(new_max)
            
            val_mx = max(0, val_mx)
            val_at = max(0, min(val_at, val_mx))
            
            self.sheet.setdefault("magias", {}).setdefault("slots", {})[str(slot_lvl)] = {
                "atual": val_at,
                "max": val_mx
            }
            self.save_to_disk_mock()
            self.populate_sub_magias()
        except ValueError:
            pass

    def save_spell_edit(self, idx, new_name, new_desc):
        new_name = new_name.strip()
        new_desc = new_desc.strip()
        magias_lista = self.sheet.setdefault("magias", {}).setdefault("lista", [])
        if idx < len(magias_lista):
            magias_lista[idx]["nome"] = new_name
            magias_lista[idx]["descricao"] = new_desc
            if "detalhes" in magias_lista[idx]:
                del magias_lista[idx]["detalhes"]
            self.save_to_disk_mock()

    def add_mock_spell(self, name_entry, desc_entry):
        name = name_entry.get().strip()
        desc = desc_entry.get().strip()
        if not name:
            return
            
        self.sheet.setdefault("magias", {}).setdefault("lista", []).append({
            "nome": name,
            "descricao": desc
        })
        name_entry.delete(0, tk.END)
        desc_entry.delete(0, tk.END)
        self.populate_sub_magias()
        self.save_to_disk_mock()

    def remove_mock_spell(self, idx):
        magias_lista = self.sheet.get("magias", {}).get("lista", [])
        if idx < len(magias_lista):
            magias_lista.pop(idx)
            self.populate_sub_magias()
            self.save_to_disk_mock()

    # --- MUDANÇA DE COR DINÂMICA DA UI ---
    def change_ui_color(self, new_hex_color):
        self.current_color = new_hex_color
        
        # Limpa referências a widgets destruídos
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        
        # 1. Borda colorida dos cards principais e dots de proficiência
        for widget in self.color_framed_widgets:
            if hasattr(widget, "configure"):
                try:
                    if isinstance(widget, (ctk.CTkLabel, ctk.CTkEntry)):
                        widget.configure(text_color=new_hex_color)
                    else:
                        widget.configure(border_color=new_hex_color)
                except Exception:
                    pass
                    
        # 2. Atualiza a linha indicadora da aba principal ativa
        self.switch_main_tab(self.active_main_tab)
        
    # --- COMBATE HP AJUSTES ---
    def adjust_hp(self, delta):
        hp_max = self.sheet.get("combate", {}).get("hp_max", 12)
        try:
            val_text = self.hp_val_lbl.cget("text").split("/")[0].strip()
            hp_atual = int(val_text)
        except Exception:
            hp_atual = hp_max
            
        novo_hp = max(0, min(hp_atual + delta, hp_max))
        self.hp_val_lbl.configure(text=f"{novo_hp} / {hp_max}")
        self.hp_bar.set(novo_hp / max(1, hp_max))
        
        # Salva o HP alterado no JSON local
        self.sheet["combate"]["hp_atual"] = novo_hp
        self.save_to_disk_mock()
        
    def set_hp_fine(self):
        hp_max = self.sheet.get("combate", {}).get("hp_max", 12)
        val_str = self.hp_input.get().strip()
        if not val_str: return
        
        try:
            val = int(val_str)
            novo_hp = max(0, min(val, hp_max))
            self.hp_val_lbl.configure(text=f"{novo_hp} / {hp_max}")
            self.hp_bar.set(novo_hp / max(1, hp_max))
            self.hp_input.delete(0, tk.END)
            
            # Salva o HP alterado no JSON local
            self.sheet["combate"]["hp_atual"] = novo_hp
            self.save_to_disk_mock()
        except ValueError:
            pass
            
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = PlayerMockupGUI()
    app.run()
