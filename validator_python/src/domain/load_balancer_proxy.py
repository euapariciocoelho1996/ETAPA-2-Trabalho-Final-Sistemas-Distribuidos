from typing import Dict, Any, List, Optional
from .abstract_proxy import AbstractProxy
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