from typing import Dict, Any
from .abstract_proxy import AbstractProxy
import requests

class ServiceProxy(AbstractProxy):
    def __init__(self, target_address: str):
        super().__init__(target_address)

    def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processa a requisição e encaminha para o serviço alvo.
        """
        self.increment_request_count()
        
        try:
            # Simula uma chamada HTTP para o serviço alvo
            # Em um ambiente real, você usaria requests.post() ou requests.get()
            response = {
                "status": "success",
                "target": self.target_address,
                "request_count": self.request_count,
                "data": request_data
            }
            
            return response
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "target": self.target_address,
                "request_count": self.request_count
            } 