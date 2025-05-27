import os
from domain.source import Source
import logging
from datetime import datetime
import signal
import sys

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S,%f'[:-3]
)
logger = logging.getLogger(__name__)

def signal_handler(sig, frame):
    """Manipula o sinal de interrupção (Ctrl+C)."""
    logger.info("\nRecebido sinal de interrupção. Finalizando...")
    if 'source' in globals():
        source.stop()
    sys.exit(0)

def main():
    try:
        # Registra o manipulador de sinal
        signal.signal(signal.SIGINT, signal_handler)
        
        # Obtém o caminho do diretório atual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(current_dir, '..', 'config', 'source.yaml')
        
        # Inicializa o Source
        logger.info("Inicializando o Source...")
        global source
        source = Source(config_path)
        
        # Inicia o Source
        logger.info("Iniciando o Source...")
        source.start()
        
    except Exception as e:
        logger.error(f"Erro durante a execução: {str(e)}")
        if 'source' in globals():
            source.stop()
        raise

if __name__ == "__main__":
    main() 