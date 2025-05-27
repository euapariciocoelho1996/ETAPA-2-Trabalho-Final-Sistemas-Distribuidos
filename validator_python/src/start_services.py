import os
import sys
import yaml
import logging
import threading
import signal
import time
from domain.service import Service

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ServiceManager:
    def __init__(self):
        self.service_threads = []
        self.running = True
    
    def create_service_config(self, port: int) -> str:
        """Cria um arquivo de configuração temporário para o serviço."""
        config = {
            'service': {
                'host': 'localhost',
                'port': port
            }
        }
        
        config_path = f"validator_python/config/service_{port}.yaml"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        return config_path
    
    def start_service(self, port: int):
        """Inicia um serviço em uma porta específica."""
        config_path = self.create_service_config(port)
        service = Service(config_path)
        service.start()
    
    def signal_handler(self, signum, frame):
        """Manipula sinais para encerrar os serviços graciosamente."""
        logger.info("Recebido sinal para encerrar. Aguardando serviços finalizarem...")
        self.running = False
    
    def start(self):
        """Inicia todos os serviços."""
        # Registra o handler de sinais
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Portas dos serviços
        ports = [8083, 8084, 8085, 8086]
        
        # Inicia cada serviço em uma thread separada
        for port in ports:
            thread = threading.Thread(target=self.start_service, args=(port,))
            thread.daemon = True
            self.service_threads.append(thread)
            thread.start()
            logger.info(f"Serviço iniciado na porta {port}")
        
        try:
            # Mantém o programa rodando
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Encerrando serviços...")
            self.running = False
        
        # Aguarda as threads terminarem
        for thread in self.service_threads:
            thread.join(timeout=5)
        
        logger.info("Todos os serviços encerrados.")

def main():
    """Função principal que inicia o gerenciador de serviços."""
    manager = ServiceManager()
    manager.start()

if __name__ == "__main__":
    main() 