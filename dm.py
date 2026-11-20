import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
import json
import os
from src.dm_server import DNDServer
from src.sheet_parser import save_sheet

# Configuração global do CustomTkinter
ctk.set_appearance_mode("dark")

class DMGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("D&D Cheat Sheet - Mestre (DM)")
        self.root.geometry("1350x780")
        self.root.minsize(1200, 700)
        
        # Estrutura: {nome_personagem: {"filepath": str ou None, "sheet_data": dict ou None, "addr": tuple}}
        self.players = {}
        
        self.selected_player_name = None
        self.sheet = None
        self.current_color = "#ffffff"
        
        # Listas de controle de estilos
        self.color_framed_widgets = []
        self.main_tab_indicators = {}
        self.sub_tab_indicators = {}
        
        self.build_ui()
        
        # Desfoca inputs ao clicar fora
        self.root.bind("<Button-1>", self.on_click_outside)
        
        # Inicializa o servidor na porta 5000
        self.server = DNDServer(host='0.0.0.0', port=5000)
        self.server.on_connect = lambda name, addr: self.root.after(0, lambda: self.handle_connect(name, addr))
        self.server.on_disconnect = lambda name: self.root.after(0, lambda: self.handle_disconnect(name))
        self.server.on_update = lambda name, updated_sheet: self.root.after(0, lambda: self.handle_player_update(name, updated_sheet))
        
        try:
            self.server.start()
        except Exception as e:
            messagebox.showerror("Erro de Servidor", f"Não foi possível iniciar o servidor na porta 5000:\n{e}")
            self.root.destroy()
            return

    def handle_connect(self, character_name, addr):
        print(f"[MESTRE] Conexão recebida de {character_name} ({addr})")
        # Registra na memória local como pendente de ficha
        self.players[character_name] = {
            "filepath": None,
            "sheet_data": None,
            "addr": addr
        }
        self.update_sidebar()

    def handle_disconnect(self, character_name):
        print(f"[MESTRE] {character_name} desconectou.")
        if character_name in self.players:
            del self.players[character_name]
        
        # Se o jogador ativo desconectou, limpa a visualização
        if self.selected_player_name == character_name:
            self.selected_player_name = None
            self.sheet = None
            self.build_details_pane()
            
        self.update_sidebar()

    def handle_player_update(self, character_name, updated_sheet):
        # Atualiza a ficha na memória local do Mestre
        if character_name in self.players:
            self.players[character_name]["sheet_data"] = updated_sheet
            
        # Se for o jogador selecionado atualmente, atualiza a UI sem travar o foco
        if self.selected_player_name == character_name:
            self.handle_server_update(updated_sheet)
        else:
            # Apenas atualiza a barra lateral (para refletir mudança de HP, por exemplo)
            self.update_sidebar()

    def handle_server_update(self, new_sheet: dict):
        if not new_sheet or new_sheet == self.sheet:
            return
            
        old_sheet = self.sheet
        self.sheet = new_sheet
        
        # Cor do tema mudou
        if new_sheet.get("cor") != old_sheet.get("cor"):
            self.change_ui_color(new_sheet.get("cor", "#ffffff"))
            
        # Nome e cabeçalho
        self.lbl_nome.configure(text=self.sheet.get("nome", "Sem Nome").upper())
        self.lbl_info.configure(
            text=f"Classe/Nível: {self.sheet.get('classe_nivel', '')}  |  Raça: {self.sheet.get('raca', '')}  |  Antecedente: {self.sheet.get('antecedente', '')}  |  Tendência: {self.sheet.get('tendencia', '')}"
        )
        
        # HP
        old_hp = old_sheet.get("combate", {})
        new_hp = new_sheet.get("combate", {})
        if old_hp.get("hp_atual") != new_hp.get("hp_atual") or old_hp.get("hp_max") != new_hp.get("hp_max"):
            hp_at = new_hp.get("hp_atual", 0)
            hp_mx = new_hp.get("hp_max", 1)
            self.hp_val_lbl.configure(text=f"{hp_at} / {hp_mx}")
            self.hp_bar.set(hp_at / max(1, hp_mx))
            
        # Listas dinâmicas
        if old_sheet.get("inventario") != new_sheet.get("inventario"):
            self.populate_inventory()
            
        if old_sheet.get("ataques") != new_sheet.get("ataques"):
            self.populate_sub_ataques()
            
        if old_sheet.get("magias") != new_sheet.get("magias"):
            self.populate_sub_magias()
            
        old_extra = old_sheet.get("extra", old_sheet.get("custom", {}))
        new_extra = new_sheet.get("extra", new_sheet.get("custom", {}))
        if old_extra != new_extra:
            for key in new_extra.keys():
                self.populate_sub_extra_tab(key)
                
        self.update_sidebar()

    def save_and_sync(self):
        """Salva a ficha no disco local e envia as alterações via rede para o cliente."""
        if not self.selected_player_name:
            return
            
        player_info = self.players.get(self.selected_player_name)
        if player_info and player_info["filepath"]:
            try:
                save_sheet(self.sheet, player_info["filepath"])
                self.server.send_override_to_client(self.selected_player_name, self.sheet)
                self.update_sidebar()
            except Exception as e:
                print(f"[MESTRE] Erro ao salvar/sincronizar: {e}")

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
        
        # === PAINEL ESQUERDO (Barra Lateral de Jogadores) ===
        self.sidebar = ctk.CTkFrame(self.bg_frame, width=280, fg_color="#1e1e1e", corner_radius=0)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        self.sidebar.pack_propagate(False)
        
        lbl_sidebar = ctk.CTkLabel(
            self.sidebar, 
            text="JOGADORES CONECTADOS", 
            font=ctk.CTkFont(family="Cinzel", size=13, weight="bold"),
            text_color="#888888"
        )
        lbl_sidebar.pack(pady=(20, 10))
        
        self.players_list_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.players_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # === PAINEL DIREITO (Ficha Detalhada) ===
        self.detail_container = ctk.CTkFrame(self.bg_frame, fg_color="transparent")
        self.detail_container.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.update_sidebar()
        self.build_details_pane()

    def update_sidebar(self):
        # Limpa os itens da barra lateral
        for child in self.players_list_frame.winfo_children():
            child.destroy()
            
        if not self.players:
            lbl_empty = ctk.CTkLabel(
                self.players_list_frame, 
                text="Nenhum jogador conectado...", 
                font=ctk.CTkFont(size=11, slant="italic"), 
                text_color="#555555"
            )
            lbl_empty.pack(pady=20)
            return

        for name, player_info in self.players.items():
            sheet = player_info["sheet_data"]
            filepath = player_info["filepath"]
            
            is_selected = (self.selected_player_name == name)
            
            if filepath is None:
                # Jogador conectado mas sem ficha vinculada
                color = "#888888"
                border_w = 2 if is_selected else 1
                border_c = "#444444"
                
                card = ctk.CTkFrame(
                    self.players_list_frame, 
                    fg_color="#151515" if not is_selected else "#222222",
                    border_width=border_w,
                    border_color=border_c,
                    corner_radius=8,
                    height=70
                )
                card.pack(fill=tk.X, pady=6)
                card.pack_propagate(False)
                
                self.bind_click_recursive(card, name)
                
                lbl_name = ctk.CTkLabel(card, text=name.upper(), font=ctk.CTkFont(size=12, weight="bold"), text_color=color)
                lbl_name.pack(anchor=tk.W, padx=10, pady=(12, 2))
                self.bind_click_recursive(lbl_name, name)
                
                lbl_status = ctk.CTkLabel(card, text="Sem Ficha (Clique para associar)", font=ctk.CTkFont(size=10, slant="italic"), text_color="#666666")
                lbl_status.pack(anchor=tk.W, padx=10, pady=(1, 4))
                self.bind_click_recursive(lbl_status, name)
            else:
                # Jogador com ficha associada
                color = sheet.get("cor", "#ffffff")
                combat = sheet.get("combate", {})
                hp_at = combat.get("hp_atual", 10)
                hp_mx = combat.get("hp_max", 10)
                
                border_w = 2 if is_selected else 1
                border_c = color if is_selected else "#333333"
                
                card = ctk.CTkFrame(
                    self.players_list_frame, 
                    fg_color="#151515" if not is_selected else "#222222",
                    border_width=border_w,
                    border_color=border_c,
                    corner_radius=8,
                    height=70
                )
                card.pack(fill=tk.X, pady=6)
                card.pack_propagate(False)
                
                self.bind_click_recursive(card, name)
                
                lbl_name = ctk.CTkLabel(card, text=name.upper(), font=ctk.CTkFont(size=12, weight="bold"), text_color=color)
                lbl_name.pack(anchor=tk.W, padx=10, pady=(6, 2))
                self.bind_click_recursive(lbl_name, name)
                
                progress = hp_at / max(1, hp_mx)
                bar_color = "#2ecc71" if progress > 0.3 else "#e74c3c"
                hp_bar = ctk.CTkProgressBar(card, fg_color="#2b2b2b", progress_color=bar_color, height=5)
                hp_bar.pack(fill=tk.X, padx=10, pady=2)
                hp_bar.set(progress)
                self.bind_click_recursive(hp_bar, name)
                
                lbl_hp = ctk.CTkLabel(card, text=f"HP: {hp_at} / {hp_mx}", font=ctk.CTkFont(size=10), text_color="#aaaaaa")
                lbl_hp.pack(anchor=tk.W, padx=10, pady=(1, 4))
                self.bind_click_recursive(lbl_hp, name)

    def bind_click_recursive(self, widget, name):
        widget.bind("<Button-1>", lambda e, n=name: self.select_player(n))

    def select_player(self, name):
        player_info = self.players.get(name)
        if not player_info:
            return
            
        if player_info["filepath"] is None:
            # Abre caixa de diálogo para associar ficha JSON
            filepath = filedialog.askopenfilename(
                title=f"Selecionar Ficha JSON para {name}",
                filetypes=[("JSON Files", "*.json")]
            )
            if not filepath:
                return  # Cancelado
                
            try:
                from src.sheet_parser import load_sheet
                sheet_data = load_sheet(filepath)
                
                # Validação básica
                if "nome" not in sheet_data:
                    messagebox.showerror("Erro de Ficha", "O JSON selecionado não possui a chave 'nome' e parece inválido.")
                    return
                
                # Associa a ficha no servidor para liberar o jogador
                self.server.assign_sheet(name, filepath, sheet_data)
                
                # Atualiza estrutura local
                self.players[name]["filepath"] = filepath
                self.players[name]["sheet_data"] = sheet_data
            except Exception as e:
                messagebox.showerror("Erro ao Carregar", f"Falha ao carregar o arquivo JSON:\n{e}")
                return
                
        # Define jogador como ativo
        self.selected_player_name = name
        self.sheet = self.players[name]["sheet_data"]
        self.current_color = self.sheet.get("cor", "#ffffff")
        
        self.color_framed_widgets = []
        self.main_tab_indicators = {}
        self.sub_tab_indicators = {}
        
        self.build_details_pane()
        self.update_sidebar()

    def build_details_pane(self):
        for child in self.detail_container.winfo_children():
            child.destroy()
            
        if not self.selected_player_name:
            lbl_select = ctk.CTkLabel(
                self.detail_container, 
                text="Selecione um jogador...", 
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color="#555555"
            )
            lbl_select.pack(expand=True)
            return

        # === CABEÇALHO ===
        self.header_frame = ctk.CTkFrame(
            self.detail_container, 
            fg_color="#1e1e1e", 
            border_color=self.current_color, 
            border_width=2,
            corner_radius=10,
            height=60
        )
        self.header_frame.pack(fill=tk.X, padx=10, pady=(5, 10))
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
        self.body_frame = ctk.CTkFrame(self.detail_container, fg_color="transparent")
        self.body_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.left_col = ctk.CTkFrame(self.body_frame, fg_color="transparent", width=380)
        self.left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 10))
        self.left_col.pack_propagate(False)
        
        self.right_col = ctk.CTkFrame(self.body_frame, fg_color="transparent")
        self.right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(10, 0))
        
        # ==========================================
        # COLUNA ESQUERDA (Atributos e Combate)
        # ==========================================
        self.combat_card = ctk.CTkFrame(
            self.left_col, 
            fg_color="#1e1e1e", 
            border_color=self.current_color, 
            border_width=2,
            corner_radius=10
        )
        self.combat_card.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        self.color_framed_widgets.append(self.combat_card)
        
        stats_grid = ctk.CTkFrame(self.combat_card, fg_color="transparent")
        stats_grid.pack(fill=tk.X, padx=15, pady=10)
        
        combat_stats = [
            ("CA", self.sheet.get("combate", {}).get("ca", 10)),
            ("INICIATIVA", f"+{self.sheet.get('combate', {}).get('iniciativa', 0)}"),
            ("DESLOCAMENTO", self.sheet.get("combate", {}).get("deslocamento", "9m"))
        ]
        
        for idx, (label, val) in enumerate(combat_stats):
            box = self.create_stat_widget(stats_grid, label, val)
            box.grid(row=0, column=idx, padx=5, sticky="nsew")
            stats_grid.grid_columnconfigure(idx, weight=1)
            
        self.hp_subframe = ctk.CTkFrame(self.combat_card, fg_color="#151515", corner_radius=8)
        self.hp_subframe.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 12))
        
        ctk.CTkLabel(self.hp_subframe, text="PONTOS DE VIDA", font=ctk.CTkFont(size=10, weight="bold"), text_color="#888888").pack(pady=(6, 0))
        
        hp_atual = self.sheet.get("combate", {}).get("hp_atual", 12)
        hp_max = self.sheet.get("combate", {}).get("hp_max", 12)
        self.hp_val_lbl = ctk.CTkLabel(self.hp_subframe, text=f"{hp_atual} / {hp_max}", font=ctk.CTkFont(size=24, weight="bold"), text_color="#ffffff")
        self.hp_val_lbl.pack(pady=2)
        
        self.hp_bar = ctk.CTkProgressBar(self.hp_subframe, fg_color="#2b2b2b", progress_color="#444444", width=280, height=10)
        self.hp_bar.pack(pady=4)
        self.hp_bar.set(hp_atual / max(1, hp_max))
        
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
            
            mod_lbl = ctk.CTkLabel(card, text=mod_sign, font=ctk.CTkFont(size=20, weight="bold"), text_color="#ffffff")
            mod_lbl.pack(pady=2)
            
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
        
        self.main_tab_header = ctk.CTkFrame(self.right_tab_container, fg_color="#151515", height=40, corner_radius=0)
        self.main_tab_header.pack(fill=tk.X, side=tk.TOP)
        
        self.main_tabs = ["Testes", "Detalhes", "Ações", "Inventário", "Extra"]
        self.active_main_tab = "Testes"
        self.main_tab_views = {}
        
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
        # 1. ABA: TESTES
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

        # 2. ABA: DETALHES
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

        # 3. ABA: AÇÕES
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
        
        # Sub-aba: Ataques (Editáveis)
        self.view_sub_ataques = ctk.CTkFrame(self.sub_content_acoes, fg_color="transparent")
        self.sub_acoes_views["Ataques"] = self.view_sub_ataques
        self.populate_sub_ataques()
            
        # Sub-aba: Magias (Editáveis)
        self.view_sub_magias = ctk.CTkFrame(self.sub_content_acoes, fg_color="transparent")
        self.sub_acoes_views["Magias"] = self.view_sub_magias
        self.populate_sub_magias()

        # 4. ABA: INVENTÁRIO (Editável)
        self.view_inventario = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Inventário"] = self.view_inventario
        
        add_item_frame = ctk.CTkFrame(self.view_inventario, fg_color="transparent")
        add_item_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.item_entry = ctk.CTkEntry(add_item_frame, placeholder_text="Conceder novo item ao inventário...", fg_color="#121212", border_color="#333333")
        self.item_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.item_entry.bind("<Return>", lambda e: (self.add_item(), self.root.focus()))
        
        add_btn = ctk.CTkButton(add_item_frame, text="Adicionar", fg_color="#2b2b2b", hover_color="#3e3e3e", width=80, command=self.add_item)
        add_btn.pack(side=tk.RIGHT)
        
        self.inv_scroll = ctk.CTkScrollableFrame(self.view_inventario, fg_color="#151515")
        self.inv_scroll.pack(fill=tk.BOTH, expand=True)
        self.populate_inventory()

        # 5. ABA: EXTRA (Editável)
        self.view_extra = ctk.CTkFrame(self.main_content_area, fg_color="transparent")
        self.main_tab_views["Extra"] = self.view_extra
        
        self.sub_header_extra = ctk.CTkFrame(self.view_extra, fg_color="#151515", height=32, corner_radius=5)
        self.sub_header_extra.pack(fill=tk.X, pady=(0, 10))
        
        self.sub_extra_views = {}
        self.active_sub_extra = ""
        
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

    # --- SUB-ABAS CONTROLES ---
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
                
    # --- TABS PRINCIPAIS ---
    def switch_main_tab(self, tab_name):
        self.active_main_tab = tab_name
        
        for name, view in self.main_tab_views.items():
            if name == tab_name:
                view.pack(fill=tk.BOTH, expand=True)
                self.main_tab_indicators[name].configure(fg_color=self.current_color)
            else:
                view.pack_forget()
                self.main_tab_indicators[name].configure(fg_color="transparent")
                
        if tab_name == "Testes":
            self.switch_sub_testes(self.active_sub_testes)
        elif tab_name == "Detalhes":
            self.switch_sub_detalhes(self.active_sub_detalhes)
        elif tab_name == "Ações":
            self.switch_sub_acoes(self.active_sub_acoes)
        elif tab_name == "Extra":
            self.switch_sub_extra(self.active_sub_extra)

    # --- INVENTÁRIO POPULATE E SALVAR ---
    def populate_inventory(self):
        for child in self.inv_scroll.winfo_children():
            child.destroy()
            
        items = self.sheet.get("inventario", [])
        for idx, item in enumerate(items):
            row = ctk.CTkFrame(self.inv_scroll, fg_color="#1e1e1e", height=32)
            row.pack(fill=tk.X, pady=2, padx=5)
            
            entry = ctk.CTkEntry(
                row, 
                fg_color="transparent", 
                border_width=0, 
                text_color="#ffffff",
                font=ctk.CTkFont(size=12)
            )
            entry.insert(0, item)
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10, pady=5)
            
            entry.bind("<Return>", lambda e, i=idx, ent=entry: (self.save_inventory_edit(i, ent.get()), self.root.focus()))
            entry.bind("<FocusOut>", lambda e, i=idx, ent=entry: self.save_inventory_edit(i, ent.get()))
            
            del_btn = ctk.CTkButton(
                row, 
                text="X", 
                width=24, 
                height=20, 
                fg_color="#2b2b2b", 
                hover_color="#a83232", 
                command=lambda name=item: self.remove_item(name)
            )
            del_btn.pack(side=tk.RIGHT, padx=5, pady=5)
            
    def save_inventory_edit(self, idx, new_text):
        new_text = new_text.strip()
        if new_text and idx < len(self.sheet["inventario"]):
            self.sheet["inventario"][idx] = new_text
            self.save_and_sync()
            
    def add_item(self):
        item = self.item_entry.get().strip()
        if item:
            self.sheet.setdefault("inventario", []).append(item)
            self.item_entry.delete(0, tk.END)
            self.populate_inventory()
            self.save_and_sync()
            
    def remove_item(self, item):
        if "inventario" in self.sheet and item in self.sheet["inventario"]:
            self.sheet["inventario"].remove(item)
            self.populate_inventory()
            self.save_and_sync()

    # --- EXTRA RECURSOS E CARTAS ---
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
            self.save_and_sync()

    def populate_sub_extra_tab(self, key):
        readable_name = self.custom_keys_mapping.get(key, key.replace("_", " ").title())
        sub_view = self.sub_extra_views[readable_name]
        
        for child in sub_view.winfo_children():
            child.destroy()
            
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        category_data = custom_data.get(key, {})
        
        if key == "cartas_destino":
            max_cards = category_data.get("maximo", 3)
            cards_list = category_data.get("lista", [])
            curr_cards = len(cards_list)
            
            ctrl_frame = ctk.CTkFrame(sub_view, fg_color="transparent")
            ctrl_frame.pack(fill=tk.X, pady=(0, 10))
            
            count_lbl = ctk.CTkLabel(
                ctrl_frame, 
                text=f"CARTAS: {curr_cards} / {max_cards}", 
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color="#ffffff"
            )
            count_lbl.pack(side=tk.LEFT, padx=(5, 15))
            
            name_entry = ctk.CTkEntry(
                ctrl_frame, 
                placeholder_text="Nome da carta...", 
                fg_color="#121212", 
                border_color="#333333",
                height=26,
                font=ctk.CTkFont(size=11)
            )
            name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            effect_entry = ctk.CTkEntry(
                ctrl_frame, 
                placeholder_text="Efeito/detalhes...", 
                fg_color="#121212", 
                border_color="#333333",
                height=26,
                font=ctk.CTkFont(size=11)
            )
            effect_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
            
            add_btn = ctk.CTkButton(
                ctrl_frame, 
                text="Adicionar", 
                fg_color="#2b2b2b", 
                hover_color="#3e3e3e", 
                width=80,
                height=26,
                font=ctk.CTkFont(size=11),
                command=lambda: self.add_card(key, name_entry, effect_entry)
            )
            add_btn.pack(side=tk.RIGHT, padx=(5, 0))
            
            if curr_cards >= max_cards:
                add_btn.configure(state="disabled", fg_color="#1a1a1a", text_color="#555555")
                name_entry.configure(state="disabled")
                effect_entry.configure(state="disabled")
                
            name_entry.bind("<Return>", lambda e: add_btn.invoke() if curr_cards < max_cards else None)
            effect_entry.bind("<Return>", lambda e: add_btn.invoke() if curr_cards < max_cards else None)
            
            scroll_frame = ctk.CTkScrollableFrame(sub_view, fg_color="#151515")
            scroll_frame.pack(fill=tk.BOTH, expand=True)
            
            for item_idx, item_obj in enumerate(cards_list):
                row = ctk.CTkFrame(scroll_frame, fg_color="#1e1e1e")
                row.pack(fill=tk.X, pady=4, padx=5)
                
                nome = item_obj.get("nome", "").upper()
                efeito = item_obj.get("efeito", "")
                
                text_container = ctk.CTkFrame(row, fg_color="transparent")
                text_container.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=12, pady=6)
                
                title = ctk.CTkLabel(text_container, text=nome, font=ctk.CTkFont(size=12, weight="bold"), text_color=self.current_color)
                title.pack(anchor=tk.W)
                self.color_framed_widgets.append(title)
                
                desc = ctk.CTkLabel(text_container, text=efeito, font=ctk.CTkFont(size=11), text_color="#888888", wraplength=400, justify=tk.LEFT)
                desc.pack(anchor=tk.W, pady=(2, 0))
                
                del_btn = ctk.CTkButton(
                    row, 
                    text="X", 
                    width=24, 
                    height=20, 
                    fg_color="#2b2b2b", 
                    hover_color="#a83232", 
                    command=lambda idx=item_idx: self.remove_card(key, idx)
                )
                del_btn.pack(side=tk.RIGHT, padx=10, pady=10)
                
        else:
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

    def add_card(self, key, name_entry, effect_entry):
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
            self.save_and_sync()
            self.populate_sub_extra_tab(key)

    def remove_card(self, key, item_idx):
        custom_data = self.sheet.get("extra", self.sheet.get("custom", {}))
        category_data = custom_data.get(key, {})
        cards_list = category_data.get("lista", [])
        
        if item_idx < len(cards_list):
            cards_list.pop(item_idx)
            self.save_and_sync()
            self.populate_sub_extra_tab(key)

    # --- ATAQUES ---
    def populate_sub_ataques(self):
        sub_view = self.view_sub_ataques
        
        for child in sub_view.winfo_children():
            child.destroy()
            
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        
        ctrl_frame = ctk.CTkFrame(sub_view, fg_color="transparent")
        ctrl_frame.pack(fill=tk.X, pady=(0, 10))
        
        atk_name_entry = ctk.CTkEntry(
            ctrl_frame, 
            placeholder_text="Nome do novo ataque...", 
            fg_color="#121212", 
            border_color="#333333",
            height=26,
            font=ctk.CTkFont(size=11)
        )
        atk_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        atk_desc_entry = ctk.CTkEntry(
            ctrl_frame, 
            placeholder_text="Descrição (ex: Bônus: +5 | Dano: 2d6+3)...", 
            fg_color="#121212", 
            border_color="#333333",
            height=26,
            font=ctk.CTkFont(size=11)
        )
        atk_desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=3)
        
        add_btn = ctk.CTkButton(
            ctrl_frame, 
            text="Adicionar", 
            fg_color="#2b2b2b", 
            hover_color="#3e3e3e", 
            width=80,
            height=26,
            font=ctk.CTkFont(size=11),
            command=lambda: self.add_attack(atk_name_entry, atk_desc_entry)
        )
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        atk_name_entry.bind("<Return>", lambda e: add_btn.invoke())
        atk_desc_entry.bind("<Return>", lambda e: add_btn.invoke())
        
        scroll_frame = ctk.CTkScrollableFrame(sub_view, fg_color="#151515")
        scroll_frame.pack(fill=tk.BOTH, expand=True)
        
        ataques = self.sheet.get("ataques", [])
        for idx, atk in enumerate(ataques):
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
            name_entry.insert(0, atk.get("nome", "Ataque").upper())
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
            desc_entry.insert(0, atk.get("descricao", ""))
            desc_entry.pack(anchor=tk.W, fill=tk.X, expand=True, padx=5, pady=(0, 2))
            
            name_entry.bind("<Return>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: (self.save_attack_edit(i, n_ent.get(), d_ent.get()), self.root.focus()))
            name_entry.bind("<FocusOut>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: self.save_attack_edit(i, n_ent.get(), d_ent.get()))
            
            desc_entry.bind("<Return>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: (self.save_attack_edit(i, n_ent.get(), d_ent.get()), self.root.focus()))
            desc_entry.bind("<FocusOut>", lambda e, i=idx, n_ent=name_entry, d_ent=desc_entry: self.save_attack_edit(i, n_ent.get(), d_ent.get()))
            
            del_btn = ctk.CTkButton(
                row, 
                text="X", 
                width=24, 
                height=20, 
                fg_color="#2b2b2b", 
                hover_color="#a83232", 
                command=lambda i=idx: self.remove_attack(i)
            )
            del_btn.pack(side=tk.RIGHT, padx=10, pady=10)

    def save_attack_edit(self, idx, new_name, new_desc):
        new_name = new_name.strip()
        new_desc = new_desc.strip()
        ataques = self.sheet.setdefault("ataques", [])
        if idx < len(ataques):
            ataques[idx]["nome"] = new_name
            ataques[idx]["descricao"] = new_desc
            self.save_and_sync()
            
    def add_attack(self, name_entry, desc_entry):
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
        self.save_and_sync()
        
    def remove_attack(self, idx):
        ataques = self.sheet.get("ataques", [])
        if idx < len(ataques):
            ataques.pop(idx)
            self.populate_sub_ataques()
            self.save_and_sync()

    # --- MAGIAS E SLOTS ---
    def populate_sub_magias(self):
        sub_view = self.view_sub_magias
        
        for child in sub_view.winfo_children():
            child.destroy()
            
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        mag_data = self.sheet.setdefault("magias", {})
        
        # 1. CD / Bônus
        info_conj = ctk.CTkFrame(sub_view, fg_color="#1e1e1e")
        info_conj.pack(fill=tk.X, pady=(5, 10), padx=5)
        
        info_str = f"CLASSE: {mag_data.get('classe_conjurador', 'Nenhuma').upper()}  |  CD: {mag_data.get('cd_salvamento', 8)}  |  BÔNUS: +{mag_data.get('bonus_ataque', 0)}"
        lbl_info_conj = ctk.CTkLabel(info_conj, text=info_str, font=ctk.CTkFont(size=10, weight="bold"), text_color="#aaaaaa")
        lbl_info_conj.pack(pady=8, padx=10)
        
        # 2. Slots (1-5 em cima, 6-9 embaixo)
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
            
            parent_frame = slots_frame_top if slot_idx <= 5 else slots_frame_bottom
            
            slot_box = ctk.CTkFrame(parent_frame, fg_color="#1e1e1e", width=70, height=52)
            slot_box.pack(side=tk.LEFT, padx=3, expand=True, fill=tk.X)
            slot_box.pack_propagate(False)
            
            ctk.CTkLabel(slot_box, text=f"SLOT {slot_lvl}", font=ctk.CTkFont(size=9, weight="bold"), text_color="#888888").pack(pady=(4, 0))
            
            val_frame = ctk.CTkFrame(slot_box, fg_color="transparent")
            val_frame.pack(pady=(0, 4))
            
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
            
            at_entry.bind("<Return>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: (self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()), self.root.focus()))
            at_entry.bind("<FocusOut>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()))
            
            mx_entry.bind("<Return>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: (self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()), self.root.focus()))
            mx_entry.bind("<FocusOut>", lambda e, lvl=slot_lvl, ent_at=at_entry, ent_mx=mx_entry: self.save_slot_edit(lvl, ent_at.get(), ent_mx.get()))
            
        # 3. Adicionar Nova Magia
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
        
        add_btn = ctk.CTkButton(
            ctrl_frame, 
            text="Adicionar", 
            fg_color="#2b2b2b", 
            hover_color="#3e3e3e", 
            width=80,
            height=26,
            font=ctk.CTkFont(size=11),
            command=lambda: self.add_spell(spell_name_entry, spell_desc_entry)
        )
        add_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        spell_name_entry.bind("<Return>", lambda e: add_btn.invoke())
        spell_desc_entry.bind("<Return>", lambda e: add_btn.invoke())
        
        # 4. Listar Magias
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
            desc_entry.insert(0, spell.get("descricao", ""))
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
                command=lambda i=idx: self.remove_spell(i)
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
            self.save_and_sync()
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
            self.save_and_sync()

    def add_spell(self, name_entry, desc_entry):
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
        self.save_and_sync()

    def remove_spell(self, idx):
        magias_lista = self.sheet.get("magias", {}).get("lista", [])
        if idx < len(magias_lista):
            magias_lista.pop(idx)
            self.populate_sub_magias()
            self.save_and_sync()

    # --- MUDANÇA DE COR DA UI ---
    def change_ui_color(self, new_hex_color):
        self.current_color = new_hex_color
        self.color_framed_widgets = [w for w in self.color_framed_widgets if w.winfo_exists()]
        
        for widget in self.color_framed_widgets:
            if hasattr(widget, "configure"):
                try:
                    if isinstance(widget, (ctk.CTkLabel, ctk.CTkEntry)):
                        widget.configure(text_color=new_hex_color)
                    else:
                        widget.configure(border_color=new_hex_color)
                except Exception:
                    pass
                    
        self.switch_main_tab(self.active_main_tab)

    # --- AJUSTES HP ---
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
        
        self.sheet["combate"]["hp_atual"] = novo_hp
        self.save_and_sync()
        
    def set_hp_fine(self):
        hp_max = self.sheet.get("combate", {}).get("hp_max", 12)
        val_str = self.hp_input.get().strip()
        if not val_str: 
            return
        
        try:
            val = int(val_str)
            novo_hp = max(0, min(val, hp_max))
            self.hp_val_lbl.configure(text=f"{novo_hp} / {hp_max}")
            self.hp_bar.set(novo_hp / max(1, hp_max))
            self.hp_input.delete(0, tk.END)
            
            self.sheet["combate"]["hp_atual"] = novo_hp
            self.save_and_sync()
        except ValueError:
            pass

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = DMGUI()
    app.run()
