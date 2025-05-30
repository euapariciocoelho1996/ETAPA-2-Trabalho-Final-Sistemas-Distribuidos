import os
import sys
import yaml
import logging
import threading
import signal
import time
from datetime import datetime
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
        self.times = {
            'T1': [],  # Tempo do cliente até o servidor
            'T2': [],  # Tempo do servidor até o cliente
            'T3': [],  # Tempo de processamento no servidor
            'T4': [],  # Tempo de rede entre load balancers
            'T5': []   # Tempo total
        }
        
        # Configuração dos serviços
        self.lb1_config = {
            'num_services': int(os.getenv('NUM_SERVICES_LB1', 2)),
            'base_port': int(os.getenv('BASE_PORT_LB1', 8083))
        }
        
        self.lb2_config = {
            'num_services': int(os.getenv('NUM_SERVICES_LB2', 2)),
            'base_port': int(os.getenv('BASE_PORT_LB2', 8085))
        }
    
    def create_service_config(self, port: int, lb_id: int) -> str:
        """Cria um arquivo de configuração temporário para o serviço."""
        config = {
            'service': {
                'host': '0.0.0.0',
                'port': port,
                'lb_id': lb_id
            }
        }
        
        config_path = f"validator_python/config/service_{port}.yaml"
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        
        return config_path
    
    def start_service(self, port: int, lb_id: int):
        """Inicia um serviço em uma porta específica."""
        config_path = self.create_service_config(port, lb_id)
        service = Service(config_path)
        service.start()
    
    def record_time(self, time_type: str, value: float):
        """Registra um tempo específico."""
        self.times[time_type].append(value)
        logger.info(f"Tempo {time_type} registrado: {value}ms")
    
    def calculate_average_times(self):
        """Calcula e retorna os tempos médios."""
        averages = {}
        for time_type, values in self.times.items():
            if values:
                averages[time_type] = sum(values) / len(values)
            else:
                averages[time_type] = 0
        return averages
    
    def signal_handler(self, signum, frame):
        """Manipula sinais para encerrar os serviços graciosamente."""
        logger.info("Recebido sinal para encerrar. Aguardando serviços finalizarem...")
        self.running = False
        
        # Calcula e exibe os tempos médios
        averages = self.calculate_average_times()
        logger.info("\nTempos médios de resposta:")
        for time_type, avg in averages.items():
            logger.info(f"{time_type} = {avg}")
    
    def start(self):
        """Inicia todos os serviços."""
        # Registra o handler de sinais
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Inicia serviços do Load Balancer 1
        for i in range(self.lb1_config['num_services']):
            port = self.lb1_config['base_port'] + i
            thread = threading.Thread(target=self.start_service, args=(port, 1))
            thread.daemon = True
            self.service_threads.append(thread)
            thread.start()
            logger.info(f"Serviço LB1 iniciado na porta {port}")
        
        # Inicia serviços do Load Balancer 2
        for i in range(self.lb2_config['num_services']):
            port = self.lb2_config['base_port'] + i
            thread = threading.Thread(target=self.start_service, args=(port, 2))
            thread.daemon = True
            self.service_threads.append(thread)
            thread.start()
            logger.info(f"Serviço LB2 iniciado na porta {port}")
        
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