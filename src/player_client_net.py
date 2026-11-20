import socket
import threading
from src.network_utils import send_msg, recv_msg

class DNDClient:
    def __init__(self, host='127.0.0.1', port=5000):
        self.host = host
        self.port = port
        self.sock = None
        
        # Callbacks a serem acionados para atualizar a futura GUI do jogador
        self.on_update = None       # callback(dados_ficha)
        self.on_disconnect = None   # callback()

    def connect(self, character_name: str) -> dict:
        """Conecta ao servidor do DM, faz login e retorna a ficha inicial recebida."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((self.host, self.port))
        
        # 1. Envia credencial/login
        send_msg(self.sock, {"login": character_name})
        
        # 2. Recebe a ficha inicial do DM
        initial_sheet = recv_msg(self.sock)
        if not initial_sheet:
            raise ConnectionError("Falha ao receber a ficha inicial do servidor.")
            
        # 3. Spawna thread secundária de escuta para receber dados/overrides do DM
        self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self.listen_thread.start()
        
        return initial_sheet

    def _listen_loop(self):
        """Escuta modificações vindas do servidor do DM em tempo real."""
        try:
            while True:
                sheet_data = recv_msg(self.sock)
                if sheet_data is None:
                    break
                
                # Aciona o callback para que a GUI atualize seus widgets
                if self.on_update:
                    self.on_update(sheet_data)
        except Exception as e:
            print(f"[CLIENTE] Erro na escuta em segundo plano: {e}")
        finally:
            print("[CLIENTE] Desconectado do servidor.")
            if self.on_disconnect:
                self.on_disconnect()
            self.close()

    def send_update(self, sheet_data: dict):
        """Envia a ficha atualizada para o servidor (geralmente disparado ao dar Enter na GUI)."""
        if self.sock:
            try:
                send_msg(self.sock, sheet_data)
            except Exception as e:
                print(f"[CLIENTE] Falha ao enviar atualização: {e}")

    def close(self):
        """Fecha a conexão do socket de forma limpa."""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None
