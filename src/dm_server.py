import socket
import threading
import os
from src.network_utils import send_msg, recv_msg
from src.sheet_parser import save_sheet

class DNDServer:
    def __init__(self, host='0.0.0.0', port=5000, sheets_dir='sheets', template_path='sheets/sheet-template.json'):
        self.host = host
        self.port = port
        self.sheets_dir = sheets_dir
        self.template_path = template_path
        self.sock = None
        # Mapeamento: {nome_personagem: {"conn": conn, "addr": addr, "event": Event, "sheet_data": dict, "filepath": str}}
        self.clients = {}
        self.lock = threading.Lock()
        
        # Callbacks a serem acionados para atualizar a GUI do DM
        self.on_connect = None      # callback(nome_personagem, addr)
        self.on_disconnect = None   # callback(nome_personagem)
        self.on_update = None       # callback(nome_personagem, dados_ficha)

    def start(self):
        """Inicializa o socket do servidor e roda a escuta em uma thread separada."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen()
        
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        print(f"[SERVIDOR] Escutando em {self.host}:{self.port}...")

    def _listen_loop(self):
        """Aceita conexões de clientes em loop e spawna uma thread para cada um."""
        try:
            while True:
                conn, addr = self.sock.accept()
                client_thread = threading.Thread(target=self._handle_client, args=(conn, addr), daemon=True)
                client_thread.start()
        except Exception as e:
            print(f"[SERVIDOR] Erro no loop de escuta: {e}")

    def assign_sheet(self, character_name: str, filepath: str, sheet_data: dict):
        """Associa uma ficha carregada pelo DM ao jogador correspondente e destrava seu carregamento."""
        with self.lock:
            client_info = self.clients.get(character_name)
            if client_info:
                client_info["sheet_data"] = sheet_data
                client_info["filepath"] = filepath
                client_info["event"].set()

    def _handle_client(self, conn, addr):
        """Processa a conexão de um jogador."""
        character_name = None
        try:
            # 1. Recebe a mensagem de Login
            msg = recv_msg(conn)
            if not msg or "login" not in msg:
                conn.close()
                return
            
            character_name = msg["login"]
            print(f"[SERVIDOR] {character_name} conectando-se a partir de {addr}...")
            
            # 2. Registra o cliente como conectado, porém sem ficha associada inicialmente
            with self.lock:
                self.clients[character_name] = {
                    "conn": conn,
                    "addr": addr,
                    "event": threading.Event(),
                    "sheet_data": None,
                    "filepath": None
                }
            
            # Avisa a GUI do DM que o jogador conectou (para aparecer na barra lateral)
            if self.on_connect:
                self.on_connect(character_name, addr)
            
            # 3. Aguarda o DM selecionar e carregar a ficha correspondente
            client_info = self.clients[character_name]
            client_info["event"].wait()
            
            sheet_data = client_info["sheet_data"]
            filepath = client_info["filepath"]
            
            if not sheet_data or not filepath:
                print(f"[SERVIDOR] Conexão cancelada para {character_name} (sem ficha atribuída).")
                conn.close()
                return
            
            # 4. Envia a ficha inicial selecionada para o jogador
            send_msg(conn, sheet_data)
            print(f"[SERVIDOR] Ficha inicial enviada para {character_name}.")
            
            # 5. Loop de recebimento de atualizações da ficha vindas do jogador
            while True:
                updated_sheet = recv_msg(conn)
                if updated_sheet is None:  # Desconexão voluntária/limpa
                    break
                
                # Salva o arquivo atualizado no disco do DM (caminho dinâmico escolhido pelo DM)
                save_sheet(updated_sheet, filepath)
                print(f"[SERVIDOR] Ficha de {character_name} atualizada por ele e salva em {filepath}.")
                
                # Atualiza a ficha na memória do servidor
                with self.lock:
                    if character_name in self.clients:
                        self.clients[character_name]["sheet_data"] = updated_sheet
                
                # Executa o callback de atualização para a GUI do DM
                if self.on_update:
                    self.on_update(character_name, updated_sheet)
                    
        except ConnectionResetError:
            print(f"[SERVIDOR] Conexão forçadamente fechada por {character_name}.")
        except Exception as e:
            print(f"[SERVIDOR] Erro ao tratar {character_name or 'desconhecido'}: {e}")
        finally:
            if character_name:
                with self.lock:
                    if character_name in self.clients:
                        del self.clients[character_name]
                print(f"[SERVIDOR] {character_name} desconectado.")
                if self.on_disconnect:
                    self.on_disconnect(character_name)
            conn.close()

    def send_override_to_client(self, character_name: str, sheet_data: dict):
        """Permite que o DM envie alterações forçadas para a ficha do jogador em tempo real."""
        with self.lock:
            client_info = self.clients.get(character_name)
            if client_info and client_info["event"].is_set():
                conn = client_info["conn"]
                try:
                    send_msg(conn, sheet_data)
                except Exception as e:
                    print(f"[SERVIDOR] Erro ao enviar override para {character_name}: {e}")
