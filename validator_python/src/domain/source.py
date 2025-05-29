import time
import yaml
from typing import Dict, Any, List
import matplotlib.pyplot as plt
import numpy as np
from .load_balancer_proxy import LoadBalancerProxy
from .service_proxy import ServiceProxy
from .network_manager import NetworkManager
import logging
from datetime import datetime
import threading
import json
import socket
import cv2
import os
import sys

# Configuração do logging para exibir logs em tempo real
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout,
    force=True
)
logger = logging.getLogger(__name__)

# Configura o handler para não usar buffer
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.propagate = False

class Source:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.request_rate = self.config['source']['request_rate']
        self.target = self.config['source']['target']
        self.metrics_history: List[Dict[str, float]] = []
        
        # Configuração de rede
        self.network_manager = NetworkManager(
            host=self.config['source'].get('host', 'localhost'),
            port=self.config['source'].get('port', 0)
        )
        
        # Inicializa os LoadBalancers
        self.lb1 = LoadBalancerProxy(self.config['loadbalancer1']['services'])
        self.lb2 = LoadBalancerProxy(self.config['loadbalancer2']['services'])
        
        # Carrega imagens de teste
        self.test_images = self._load_test_images()
        
        logger.info("=== Inicialização do Sistema ===")
        logger.info(f"Source (Nó 01) configurado com taxa de {self.request_rate} req/s")
        logger.info("LoadBalancer1 (Nó 02) configurado com serviços:")
        for service in self.config['loadbalancer1']['services']:
            logger.info(f"  - {service}")
        logger.info("LoadBalancer2 (Nó 03) configurado com serviços:")
        for service in self.config['loadbalancer2']['services']:
            logger.info(f"  - {service}")
        logger.info("===============================")

    def _load_test_images(self) -> List[bytes]:
        """Carrega imagens de teste do diretório data/test."""
        test_images = []
        # Usa caminho relativo ao diretório atual
        test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "test")
        
        logger.info(f"Tentando carregar imagens de teste do diretório: {test_dir}")
        
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
            logger.warning(f"Diretório {test_dir} criado. Adicione imagens de teste nele.")
            return test_images
        
        files = os.listdir(test_dir)
        logger.info(f"Arquivos encontrados em {test_dir}: {files}")
        
        for img_name in files:
            if img_name.endswith(('.jpg', '.jpeg', '.png', '.webp', '.avif')):
                img_path = os.path.join(test_dir, img_name)
                try:
                    logger.info(f"Tentando carregar imagem: {img_path}")
                    # Tenta ler a imagem
                    img = cv2.imread(img_path)
                    if img is None:
                        # Se falhar, tenta ler como webp
                        img = cv2.imdecode(np.fromfile(img_path, dtype=np.uint8), cv2.IMREAD_COLOR)
                    
                    if img is not None:
                        # Verifica se a imagem tem um tamanho mínimo
                        if img.size < 1000:  # Mínimo de 1000 pixels
                            logger.warning(f"Imagem muito pequena: {img_path} ({img.size} pixels)")
                            continue
                            
                        # Redimensiona para um tamanho padrão
                        img = cv2.resize(img, (224, 224))
                        
                        # Codifica a imagem em bytes com alta qualidade
                        _, img_bytes = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 95])
                        img_data = img_bytes.tobytes()
                        
                        # Verifica se o tamanho é válido
                        if len(img_data) < 1000:  # Mínimo de 1KB
                            logger.warning(f"Imagem codificada muito pequena: {img_path} ({len(img_data)} bytes)")
                            continue
                            
                        test_images.append(img_data)
                        logger.info(f"Imagem de teste carregada com sucesso: {img_path} ({len(img_data)} bytes)")
                    else:
                        logger.error(f"Falha ao carregar imagem: {img_path} - cv2.imread retornou None")
                except Exception as e:
                    logger.error(f"Erro ao carregar imagem {img_path}: {str(e)}")
        
        if not test_images:
            logger.error(f"Nenhuma imagem válida encontrada em {test_dir}")
        else:
            logger.info(f"Total de imagens carregadas: {len(test_images)}")
        
        return test_images

    def start(self):
        """Inicia o servidor e inicia a validação."""
        # Inicia o servidor em uma thread separada
        server_thread = threading.Thread(
            target=self.network_manager.start_server,
            args=(self._handle_message,)
        )
        server_thread.daemon = True
        server_thread.start()
        
        # Aguarda o servidor iniciar
        time.sleep(1)
        
        # Aguarda os Load Balancers estarem prontos
        max_retries = 5
        retry_delay = 2  # segundos
        
        for attempt in range(max_retries):
            try:
                # Tenta conectar em cada serviço dos Load Balancers
                for service in self.config['loadbalancer1']['services']:
                    host, port = service.split(':')
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.connect((host, int(port)))
                
                for service in self.config['loadbalancer2']['services']:
                    host, port = service.split(':')
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        s.connect((host, int(port)))
                
                logger.info("Todos os serviços estão prontos!")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tentativa {attempt + 1} de {max_retries} falhou. Aguardando {retry_delay} segundos...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Não foi possível conectar aos serviços após várias tentativas")
                    raise
        
        # Inicia o experimento
        self.run_experiment()

    def _handle_message(self, message: str, client_socket: socket.socket):
        """Manipula mensagens recebidas."""
        try:
            data = json.loads(message)
            logger.debug(f"Mensagem recebida: {data}")
            
            # Processa a resposta do serviço
            if data.get("status") == "success":
                logger.info(f"Classificação: {data['class']} (Confiança: {data['confidence']:.2f})")
                logger.info(f"Tempo de processamento: {data['processing_time']:.3f}s")
            else:
                logger.error(f"Erro no serviço: {data.get('error', 'Erro desconhecido')}")
                
        except json.JSONDecodeError:
            logger.error(f"Erro ao decodificar mensagem: {message}")
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {str(e)}")

    def run_experiment(self, duration: int = 30):
        """Executa o experimento por um determinado tempo."""
        if not self.test_images:
            logger.error("Nenhuma imagem de teste disponível. Adicione imagens em data/test/")
            return
            
        start_time = time.time()
        end_time = start_time + duration
        request_count = 0
        self.running = True  # Flag para controlar o estado do experimento
        
        logger.info(f"\n=== Iniciando Experimento ({duration}s) ===")
        
        while time.time() < end_time and self.running:
            request_count += 1
            # Seleciona uma imagem aleatória
            image_data = np.random.choice(self.test_images)
            
            # Registra o tempo inicial
            t1_start = time.time()
            
            try:
                # Envia a requisição
                response = self.send_request(image_data, request_count)
                
                # Registra os tempos
                metrics = {
                    "t1_source_lb1": response.get("t1", 0),
                    "t2_lb1_service": response.get("t2", 0),
                    "t3_service_lb2": response.get("t3", 0),
                    "t4_lb2_service": response.get("t4", 0),
                    "t_processamento": response.get("t5", 0),
                    "t5_service_source": response.get("t6", 0),
                    "t5_total": response.get("mrt", 0),
                    "average_intermediate": response.get("mrt", 0) / 6.0
                }
                
                self.metrics_history.append(metrics)
                
                # Log do fluxo da requisição
                logger.info(f"---> Fluxo Req {request_count}:")
                logger.info(f"     Nó 01 (Source) -> Nó 02 (LB1) [{metrics['t1_source_lb1']:.3f}s]")
                logger.info(f"     Nó 02 (LB1) -> Serviço (escolhido: {response.get('lb1_service', 'unknown')}) [{metrics['t2_lb1_service']:.3f}s]")
                logger.info(f"     Serviço ({response.get('lb1_service', 'unknown')}) -> Nó 03 (LB2) [{metrics['t3_service_lb2']:.3f}s]")
                logger.info(f"     Nó 03 (LB2) -> Serviço (escolhido: {response.get('lb2_service', 'unknown')}) [{metrics['t4_lb2_service']:.3f}s]")
                logger.info(f"     Serviço ({response.get('lb2_service', 'unknown')}) Processamento [{metrics['t_processamento']:.3f}s]")
                logger.info(f"     Serviço ({response.get('lb2_service', 'unknown')}) -> Nó 01 (Source) [{metrics['t5_service_source']:.3f}s]")
                logger.info("<---")
                logger.info(f"     Média dos Tempos Intermediários: {metrics['average_intermediate']:.3f}s")
                logger.info("")
                
                # Log do resumo da requisição
                logger.info(f"=== Resumo da Requisição {request_count} ===")
                logger.info("Tempos:")
                logger.info(f"  T1 (Source -> LB1): {metrics['t1_source_lb1']:.3f}s")
                logger.info(f"  T2 (LB1 -> Serviço): {metrics['t2_lb1_service']:.3f}s")
                logger.info(f"  T3 (Serviço S1 -> LB2): {metrics['t3_service_lb2']:.3f}s")
                logger.info(f"  T4 (LB2 -> Serviço): {metrics['t4_lb2_service']:.3f}s")
                logger.info(f"  T5 (Processamento Serviço): {metrics['t_processamento']:.3f}s")
                logger.info(f"  T5 (Serviço S2 -> Source): {metrics['t5_service_source']:.3f}s")
                logger.info(f"  T5 (Tempo Total): {metrics['t5_total']:.3f}s")
                logger.info(f"  Média dos Tempos Intermediários: {metrics['average_intermediate']:.3f}s")
                logger.info("=============================")
                
            except Exception as e:
                logger.error(f"Erro na requisição {request_count}: {str(e)}")
                if not self.running:  # Se o erro ocorreu porque o serviço está parando
                    break
            
            # Aguarda o intervalo correto baseado na taxa de requisições
            if self.running:  # Só aguarda se ainda estiver rodando
                time.sleep(1.0 / self.request_rate)
        
        logger.info(f"\n=== Experimento Concluído ===")
        logger.info(f"Total de requisições: {request_count}")
        self._print_summary()
        self.generate_graphs()

    def send_request(self, image_data: bytes, request_num: int) -> Dict[str, Any]:
        try:
            # Seleciona serviços baseado em disponibilidade
            lb1_service = self.lb1.get_available_service()
            if not lb1_service:
                raise Exception("Nenhum serviço disponível no LB1")
                
            lb2_service = self.lb2.get_available_service()
            if not lb2_service:
                raise Exception("Nenhum serviço disponível no LB2")
            
            logger.info(f"Request {request_num}: Usando serviços {lb1_service} -> {lb2_service}")
            
            def try_connect(host: str, port: int, max_retries: int = 3, retry_delay: float = 1.0) -> socket.socket:
                for attempt in range(max_retries):
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(10)
                        s.connect((host, int(port)))
                        return s
                    except Exception as e:
                        if attempt < max_retries - 1:
                            logger.warning(f"Tentativa {attempt + 1} de {max_retries} falhou ao conectar em {host}:{port}. Aguardando {retry_delay} segundos...")
                            time.sleep(retry_delay)
                        else:
                            raise Exception(f"Não foi possível conectar em {host}:{port} após {max_retries} tentativas: {str(e)}")
            
            # T1: Source -> LB1
            start_time = time.time()
            host, port = lb1_service.split(':')
            with try_connect(host, port) as s:
                # Envia o tamanho da imagem primeiro
                size_bytes = len(image_data).to_bytes(8, 'big')
                s.sendall(size_bytes)
                s.sendall(image_data)
                # Recebe o tamanho da resposta
                size_data = s.recv(8)
                size = int.from_bytes(size_data, 'big')
                response = b''
                bytes_received = 0
                while bytes_received < size:
                    chunk = s.recv(min(size - bytes_received, 8192))
                    if not chunk:
                        break
                    response += chunk
                    bytes_received += len(chunk)
            t1 = time.time() - start_time
            
            # T2: LB1 -> Serviço
            start_time = time.time()
            host, port = lb1_service.split(':')
            with try_connect(host, port) as s:
                size_bytes = len(image_data).to_bytes(8, 'big')
                s.sendall(size_bytes)
                s.sendall(image_data)
                size_data = s.recv(8)
                size = int.from_bytes(size_data, 'big')
                response = b''
                bytes_received = 0
                while bytes_received < size:
                    chunk = s.recv(min(size - bytes_received, 8192))
                    if not chunk:
                        break
                    response += chunk
                    bytes_received += len(chunk)
            t2 = time.time() - start_time
            
            # T3: Serviço S1 -> LB2
            start_time = time.time()
            host, port = lb2_service.split(':')
            with try_connect(host, port) as s:
                size_bytes = len(image_data).to_bytes(8, 'big')
                s.sendall(size_bytes)
                s.sendall(image_data)
                size_data = s.recv(8)
                size = int.from_bytes(size_data, 'big')
                response = b''
                bytes_received = 0
                while bytes_received < size:
                    chunk = s.recv(min(size - bytes_received, 8192))
                    if not chunk:
                        break
                    response += chunk
                    bytes_received += len(chunk)
            t3 = time.time() - start_time
            
            # T4: LB2 -> Serviço
            start_time = time.time()
            host, port = lb2_service.split(':')
            with try_connect(host, port) as s:
                size_bytes = len(image_data).to_bytes(8, 'big')
                s.sendall(size_bytes)
                s.sendall(image_data)
                size_data = s.recv(8)
                size = int.from_bytes(size_data, 'big')
                response = b''
                bytes_received = 0
                while bytes_received < size:
                    chunk = s.recv(min(size - bytes_received, 8192))
                    if not chunk:
                        break
                    response += chunk
                    bytes_received += len(chunk)
            t4 = time.time() - start_time
            
            # T5: Processamento Serviço
            start_time = time.time()
            host, port = lb2_service.split(':')
            with try_connect(host, port) as s:
                size_bytes = len(image_data).to_bytes(8, 'big')
                s.sendall(size_bytes)
                s.sendall(image_data)
                size_data = s.recv(8)
                size = int.from_bytes(size_data, 'big')
                response = b''
                bytes_received = 0
                while bytes_received < size:
                    chunk = s.recv(min(size - bytes_received, 8192))
                    if not chunk:
                        break
                    response += chunk
                    bytes_received += len(chunk)
            t5 = time.time() - start_time
            
            # T6: Serviço S2 -> Source
            start_time = time.time()
            host, port = lb2_service.split(':')
            with try_connect(host, port) as s:
                size_bytes = len(image_data).to_bytes(8, 'big')
                s.sendall(size_bytes)
                s.sendall(image_data)
                size_data = s.recv(8)
                size = int.from_bytes(size_data, 'big')
                response = b''
                bytes_received = 0
                while bytes_received < size:
                    chunk = s.recv(min(size - bytes_received, 8192))
                    if not chunk:
                        break
                    response += chunk
                    bytes_received += len(chunk)
            t6 = time.time() - start_time
            
            # Marca os serviços como bem-sucedidos
            self.lb1.mark_service_success(lb1_service, t1 + t2)
            self.lb2.mark_service_success(lb2_service, t3 + t4 + t5 + t6)
            
            return {
                't1': t1,
                't2': t2,
                't3': t3,
                't4': t4,
                't5': t5,
                't6': t6,
                'mrt': t1 + t2 + t3 + t4 + t5 + t6,
                'response': response.decode(),
                'lb1_service': lb1_service,
                'lb2_service': lb2_service
            }
        except Exception as e:
            logger.error(f"Erro ao processar request {request_num}: {str(e)}")
            # Marca os serviços como com erro
            if 'lb1_service' in locals():
                self.lb1.mark_service_error(lb1_service)
            if 'lb2_service' in locals():
                self.lb2.mark_service_error(lb2_service)
            raise

    def _print_summary(self):
        """Imprime um resumo das métricas coletadas."""
        if not self.metrics_history:
            return

        t1_avg = np.mean([m["t1_source_lb1"] for m in self.metrics_history])
        t2_avg = np.mean([m["t2_lb1_service"] for m in self.metrics_history])
        t3_lb2_avg = np.mean([m["t3_service_lb2"] for m in self.metrics_history])
        t4_service_avg = np.mean([m["t4_lb2_service"] for m in self.metrics_history])
        t5_return_avg = np.mean([m["t5_service_source"] for m in self.metrics_history])
        t_process_avg = np.mean([m["t_processamento"] for m in self.metrics_history])
        t5_total_avg = np.mean([m["t5_total"] for m in self.metrics_history])
        average_intermediate_avg = np.mean([m["average_intermediate"] for m in self.metrics_history])

        logger.info("\n=== Resumo das Médias ===")
        logger.info(f"Tempo Médio T1 (Source -> LB1): {t1_avg:.3f}s")
        logger.info(f"Tempo Médio T2 (LB1 -> Serviço): {t2_avg:.3f}s")
        logger.info(f"Tempo Médio (Serviço S1 -> LB2): {t3_lb2_avg:.3f}s")
        logger.info(f"Tempo Médio (LB2 -> Serviço S2): {t4_service_avg:.3f}s")
        logger.info(f"Tempo Médio (Processamento Serviço S2): {t_process_avg:.3f}s")
        logger.info(f"Tempo Médio T5 (Serviço S2 -> Source): {t5_return_avg:.3f}s")
        logger.info(f"MRT (Tempo Total da Requisição): {t5_total_avg:.3f}s")
        logger.info(f"Média dos Tempos Intermediários: {average_intermediate_avg:.3f}s")
        logger.info("===========================")

    def generate_graphs(self):
        """Gera gráficos de desempenho."""
        if not self.metrics_history:
            logger.warning("Não há dados para gerar gráficos")
            return

        # Prepara os dados
        times = np.array([m["t5_total"] for m in self.metrics_history])
        processing_times = np.array([m["t_processamento"] for m in self.metrics_history])
        network_times = np.array([m["t1_source_lb1"] + m["t2_lb1_service"] + m["t3_service_lb2"] + m["t4_lb2_service"] + m["t5_service_source"] for m in self.metrics_history])
        
        # Calcula o MRT médio geral
        if times.size > 0:
            mrt_medio_geral_seg = np.mean(times)
            mrt_medio_geral_ms = mrt_medio_geral_seg * 1000
            
            # Número de serviços
            num_services = len(self.config['loadbalancer1']['services']) + len(self.config['loadbalancer2']['services'])
            
            # Gráfico 1: MRT vs. Número de Serviços
            plt.figure(figsize=(10, 6))
            plt.plot(num_services, mrt_medio_geral_ms, 'bo', label='Experimento')
            plt.xlabel('Número de Serviços')
            plt.ylabel('MRT (ms)')
            plt.title('Tempo Médio de Resposta (MRT) vs. Número de Serviços')
            plt.legend()
            plt.grid(True)
            plt.xlim(0, num_services + 1)
            plt.ylim(0, mrt_medio_geral_ms * 1.2)
            plt.savefig('mrt_vs_services.png')
            plt.close()
            
            # Gráfico 2: Tempos de Processamento vs. Rede
            plt.figure(figsize=(10, 6))
            x = np.arange(len(times))
            plt.plot(x, processing_times * 1000, 'r-', label='Tempo de Processamento')
            plt.plot(x, network_times * 1000, 'b-', label='Tempo de Rede')
            plt.xlabel('Número da Requisição')
            plt.ylabel('Tempo (ms)')
            plt.title('Tempos de Processamento vs. Rede')
            plt.legend()
            plt.grid(True)
            plt.savefig('processing_vs_network.png')
            plt.close()
            
            logger.info("\n=== Gráficos Gerados ===")
            logger.info("Arquivo: mrt_vs_services.png")
            logger.info("Arquivo: processing_vs_network.png")
            logger.info("=====================")

    def stop(self):
        """Para o servidor e limpa recursos."""
        try:
            logger.info("Iniciando processo de parada do Source...")
            # Força o flush dos logs
            for handler in logger.handlers:
                handler.flush()
            
            # Marca que o experimento deve parar
            self.running = False
            
            # Aguarda um tempo para as requisições em andamento terminarem
            logger.info("Aguardando requisições em andamento terminarem...")
            time.sleep(2)  # Aguarda 2 segundos para as requisições terminarem
            
            # Para o servidor
            self.network_manager.stop()
            
            # Força o flush dos logs novamente
            for handler in logger.handlers:
                handler.flush()
                
            logger.info("Source finalizado com sucesso")
            # Último flush antes de parar
            for handler in logger.handlers:
                handler.flush()
        except Exception as e:
            logger.error(f"Erro ao parar o Source: {str(e)}")
            # Força o flush mesmo em caso de erro
            for handler in logger.handlers:
                handler.flush() 