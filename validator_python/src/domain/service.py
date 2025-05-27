import numpy as np
from sklearn.neighbors import KNeighborsClassifier
from sklearn.preprocessing import StandardScaler
import cv2
import pickle
import os
import logging
import time
from typing import Dict, Any, Tuple
import json
import socket
import threading
import yaml

logger = logging.getLogger(__name__)

class ImageClassifierService:
    def __init__(self, model_path: str = None):
        self.model = None
        self.scaler = StandardScaler()
        self.is_training = False
        self.model_path = model_path or 'vehicle_classifier.pkl'
        
        # Carrega o modelo se existir
        if os.path.exists(self.model_path):
            self._load_model()
        else:
            self._train_model()
    
    def _load_model(self):
        """Carrega o modelo treinado."""
        try:
            with open(self.model_path, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.scaler = data['scaler']
            logger.info("Modelo carregado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao carregar modelo: {str(e)}")
            self._train_model()
    
    def _save_model(self):
        """Salva o modelo treinado."""
        try:
            with open(self.model_path, 'wb') as f:
                pickle.dump({
                    'model': self.model,
                    'scaler': self.scaler
                }, f)
            logger.info("Modelo salvo com sucesso")
        except Exception as e:
            logger.error(f"Erro ao salvar modelo: {str(e)}")
    
    def _train_model(self):
        """Treina o modelo KNN com imagens de carros e motos."""
        logger.info("Iniciando treinamento do modelo...")
        self.is_training = True
        
        # Diretórios com as imagens de treinamento
        car_dir = "data/train/cars"
        bike_dir = "data/train/bikes"
        
        # Carrega e processa as imagens
        X = []  # Features
        y = []  # Labels (0 para carros, 1 para motos)
        
        # Processa imagens de carros
        for img_name in os.listdir(car_dir):
            if img_name.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                img_path = os.path.join(car_dir, img_name)
                try:
                    img = cv2.imread(img_path)
                    if img is not None:
                        # Redimensiona para 64x64 e converte para escala de cinza
                        img = cv2.resize(img, (64, 64))
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        # Aplana a imagem
                        features = img.flatten()
                        X.append(features)
                        y.append(0)  # 0 para carros
                        logger.info(f"Imagem processada: {img_path}")
                except Exception as e:
                    logger.error(f"Erro ao processar imagem {img_path}: {str(e)}")
        
        # Processa imagens de motos
        for img_name in os.listdir(bike_dir):
            if img_name.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                img_path = os.path.join(bike_dir, img_name)
                try:
                    img = cv2.imread(img_path)
                    if img is not None:
                        img = cv2.resize(img, (64, 64))
                        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        features = img.flatten()
                        X.append(features)
                        y.append(1)  # 1 para motos
                        logger.info(f"Imagem processada: {img_path}")
                except Exception as e:
                    logger.error(f"Erro ao processar imagem {img_path}: {str(e)}")
        
        if not X:
            raise ValueError("Nenhuma imagem válida encontrada para treinamento")
        
        # Converte para arrays numpy
        X = np.array(X)
        y = np.array(y)
        
        # Normaliza os dados
        X = self.scaler.fit_transform(X)
        
        # Treina o modelo KNN
        self.model = KNeighborsClassifier(n_neighbors=5)
        self.model.fit(X, y)
        
        # Salva o modelo
        self._save_model()
        self.is_training = False
        logger.info("Treinamento concluído com sucesso")
    
    def classify_image(self, image_data: bytes) -> Tuple[str, float]:
        """Classifica uma imagem e retorna a classe e a confiança."""
        try:
            # Converte os bytes da imagem para array numpy
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                raise ValueError("Imagem inválida")
            
            # Processa a imagem
            img = cv2.resize(img, (64, 64))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            features = img.flatten().reshape(1, -1)
            
            # Normaliza os dados
            features = self.scaler.transform(features)
            
            # Faz a predição
            prediction = self.model.predict(features)[0]
            probabilities = self.model.predict_proba(features)[0]
            confidence = probabilities[prediction]
            
            # Retorna a classe e a confiança
            class_name = "Carro" if prediction == 0 else "Moto"
            return class_name, confidence
            
        except Exception as e:
            logger.error(f"Erro ao classificar imagem: {str(e)}")
            raise

class Service:
    def __init__(self, config_path: str):
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.classifier = ImageClassifierService()
        self.running = False
        self.server_socket = None
        
        # Configuração do servidor
        self.host = self.config['service'].get('host', 'localhost')
        self.port = self.config['service'].get('port', 0)
        
        logger.info(f"Serviço inicializado em {self.host}:{self.port}")
    
    def start(self):
        """Inicia o servidor."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.port = self.server_socket.getsockname()[1]  # Obtém a porta real se foi especificado 0
            logger.info(f"Servidor iniciado em {self.host}:{self.port}")
            
            # Inicia o treinamento do modelo em uma thread separada
            training_thread = threading.Thread(target=self.classifier._train_model)
            training_thread.daemon = True
            training_thread.start()
            
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
            
            # Recebe o tamanho da imagem
            size_data = client_socket.recv(8)
            if not size_data:
                logger.error("Nenhum dado recebido do cliente")
                return
            
            size = int.from_bytes(size_data, 'big')
            logger.info(f"Tamanho da imagem recebida: {size} bytes")
            
            # Recebe a imagem
            image_data = b''
            bytes_received = 0
            while bytes_received < size:
                chunk = client_socket.recv(min(size - bytes_received, 8192))
                if not chunk:
                    break
                image_data += chunk
                bytes_received += len(chunk)
            
            logger.info(f"Imagem recebida completamente: {len(image_data)} bytes")
            
            # Classifica a imagem
            start_time = time.time()
            class_name, confidence = self.classifier.classify_image(image_data)
            processing_time = time.time() - start_time
            
            logger.info(f"Classificação: {class_name} (Confiança: {confidence:.2f})")
            logger.info(f"Tempo de processamento: {processing_time:.3f}s")
            
            # Prepara a resposta
            response = {
                "status": "success",
                "class": class_name,
                "confidence": float(confidence),
                "processing_time": processing_time
            }
            
            # Envia a resposta
            response_data = json.dumps(response).encode()
            response_size = len(response_data)
            logger.info(f"Enviando resposta de {response_size} bytes")
            
            # Envia o tamanho da resposta primeiro
            size_bytes = response_size.to_bytes(8, 'big')
            client_socket.sendall(size_bytes)
            
            # Envia a resposta
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
                error_size = len(error_data)
                size_bytes = error_size.to_bytes(8, 'big')
                client_socket.sendall(size_bytes)
                client_socket.sendall(error_data)
            except:
                pass
        finally:
            client_socket.close()
            logger.info(f"Conexão com {address} fechada")
    
    def stop(self):
        """Para o servidor do serviço."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        logger.info("Serviço finalizado") 