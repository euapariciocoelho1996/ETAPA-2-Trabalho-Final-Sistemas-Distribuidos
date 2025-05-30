import socket
import threading
import logging
import json
from typing import Dict, Any, Callable

logger = logging.getLogger(__name__)

class NetworkManager:
    def __init__(self, host: str = 'localhost', port: int = 0):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.is_running = False
        self.message_handler = None
        self.connections = []

    def start_server(self, message_handler: Callable[[str, socket.socket], None]):
        """Inicia o servidor e aguarda conexões."""
        self.message_handler = message_handler
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.port = self.server_socket.getsockname()[1]
        self.is_running = True
        
        logger.info(f"Servidor iniciado em {self.host}:{self.port}")
        
        while self.is_running:
            try:
                client_socket, address = self.server_socket.accept()
                logger.info(f"Conexão aceita de {address}")
                self.connections.append(client_socket)
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket,)
                )
                client_thread.start()
            except Exception as e:
                if self.is_running:
                    logger.error(f"Erro ao aceitar conexão: {str(e)}")

    def _handle_client(self, client_socket: socket.socket):
        """Gerencia a comunicação com um cliente específico."""
        try:
            while self.is_running:
                data = client_socket.recv(4096)
                if not data:
                    break
                message = data.decode('utf-8')
                if self.message_handler:
                    self.message_handler(message, client_socket)
        except Exception as e:
            logger.error(f"Erro na comunicação com cliente: {str(e)}")
        finally:
            client_socket.close()
            if client_socket in self.connections:
                self.connections.remove(client_socket)

    def connect_to_server(self, host: str, port: int) -> socket.socket:
        """Conecta a um servidor remoto."""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((host, port))
            logger.info(f"Conectado ao servidor {host}:{port}")
            return self.client_socket
        except Exception as e:
            logger.error(f"Erro ao conectar ao servidor: {str(e)}")
            raise

    def send_message(self, message: str, target_socket: socket.socket = None):
        """Envia uma mensagem para um socket específico ou para todos os clientes conectados."""
        try:
            if target_socket:
                target_socket.sendall(message.encode('utf-8'))
            else:
                for conn in self.connections:
                    conn.sendall(message.encode('utf-8'))
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {str(e)}")
            raise

    def stop(self):
        """Para o servidor e fecha todas as conexões."""
        self.is_running = False
        if self.server_socket:
            self.server_socket.close()
        for conn in self.connections:
            conn.close()
        self.connections.clear()
        logger.info("Servidor parado e conexões fechadas") 