from typing import Dict, Any, List, Optional, Tuple
import os
import sys
import json
import threading

# Adiciona o diretório raiz ao PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(parent_dir)
sys.path.insert(0, root_dir)

from src.domain.abstract_proxy import AbstractProxy
import random
import socket
import logging
import time

logger = logging.getLogger(__name__)

class LoadBalancerProxy(AbstractProxy):
    def __init__(self, services: List[str]):
        super().__init__(services[0])  # Endereço principal
        self.services = services
        self.service_status: Dict[str, Dict] = {}
        self.initialize_services()
        self.current_index = 0

    def initialize_services(self):
        """Inicializa o status dos serviços."""
        for service in self.services:
            self.service_status[service] = {
                'available': True,
                'last_check': 0,
                'response_time': float('inf'),
                'error_count': 0
            }

    def check_service_availability(self, service: str) -> bool:
        """Verifica se um serviço está disponível."""
        host, port = service.split(':')
        try:
            # Tenta estabelecer uma conexão
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)  # Timeout de 1 segundo
            start_time = time.time()
            sock.connect((host, int(port)))
            response_time = time.time() - start_time
            sock.close()
            
            # Atualiza o status do serviço
            self.service_status[service].update({
                'available': True,
                'last_check': time.time(),
                'response_time': response_time,
                'error_count': 0
            })
            return True
        except Exception as e:
            logger.warning(f"Serviço {service} indisponível: {str(e)}")
            self.service_status[service]['error_count'] += 1
            if self.service_status[service]['error_count'] >= 3:
                self.service_status[service]['available'] = False
            return False

    def get_available_service(self) -> Optional[str]:
        """Retorna o serviço mais disponível e com menor tempo de resposta."""
        current_time = time.time()
        available_services = []
        
        # Verifica disponibilidade dos serviços
        for service in self.services:
            # Verifica a cada 5 segundos
            if current_time - self.service_status[service]['last_check'] > 5:
                self.check_service_availability(service)
            
            if self.service_status[service]['available']:
                available_services.append(service)
        
        if not available_services:
            logger.error("Nenhum serviço disponível")
            return None
        
        # Retorna o serviço com menor tempo de resposta
        return min(available_services, 
                  key=lambda s: self.service_status[s]['response_time'])

    def mark_service_error(self, service: str):
        """Marca um serviço como tendo erro."""
        if service in self.service_status:
            self.service_status[service]['error_count'] += 1
            if self.service_status[service]['error_count'] >= 3:
                self.service_status[service]['available'] = False
                logger.warning(f"Serviço {service} marcado como indisponível após múltiplos erros")

    def mark_service_success(self, service: str, response_time: float):
        """Marca um serviço como tendo sucesso."""
        if service in self.service_status:
            self.service_status[service].update({
                'available': True,
                'error_count': 0,
                'response_time': response_time,
                'last_check': time.time()
            })

    def get_next_target(self) -> str:
        """
        Implementa o algoritmo round-robin para seleção do próximo servidor.
        """
        target = self.services[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.services)
        return target

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa a requisição usando o algoritmo de balanceamento de carga.
        """
        self.increment_request_count()
        target = self.get_next_target()
        
        # Simula o processamento da requisição
        response = {
            "status": "success",
            "target": target,
            "request_count": self.request_count,
            "data": request_data
        }
        
        return response 

    def start(self):
        """Inicia o servidor do load balancer."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind(('0.0.0.0', 8001))
            self.server_socket.listen(5)
            logger.info("Load Balancer iniciado na porta 8001")
            
            while True:
                try:
                    client_socket, address = self.server_socket.accept()
                    logger.info(f"Conexão aceita de {address}")
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except Exception as e:
                    if not self.running:
                        break
                    logger.error(f"Erro ao aceitar conexão: {str(e)}")
                    continue
                
        except Exception as e:
            logger.error(f"Erro ao iniciar servidor: {str(e)}")
            raise
        finally:
            if hasattr(self, 'server_socket'):
                self.server_socket.close()
                logger.info("Servidor encerrado")

    def _handle_client(self, client_socket: socket.socket, address: Tuple[str, int]):
        """Manipula a conexão com um cliente."""
        try:
            logger.info(f"Processando requisição de {address}")
            
            # Recebe os dados da requisição
            data = client_socket.recv(4096)
            if not data:
                logger.error("Nenhum dado recebido do cliente")
                return
            
            # Processa a requisição
            request_data = json.loads(data.decode())
            response = self.handle_request(request_data)
            
            # Envia a resposta
            response_data = json.dumps(response).encode()
            client_socket.sendall(response_data)
            logger.info("Resposta enviada com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao processar requisição: {str(e)}")
            try:
                # Tenta enviar uma mensagem de erro
                error_response = {
                    "status": "error",
                    "error": str(e)
                }
                error_data = json.dumps(error_response).encode()
                client_socket.sendall(error_data)
            except:
                pass
        finally:
            client_socket.close()
            logger.info(f"Conexão com {address} fechada")

if __name__ == '__main__':
    # Configuração de logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Lista de serviços disponíveis
        services = [
            'service-1:8000',
            'service-2:8000',
            'service-3:8000'
        ]
        
        # Inicia o load balancer
        load_balancer = LoadBalancerProxy(services)
        load_balancer.start()
    except Exception as e:
        logging.error(f"Erro ao iniciar load balancer: {str(e)}")
        raise 