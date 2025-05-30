# PASID-VALIDATOR - ETAPA 1 - Sistema de Validação de Desempenho em Sistemas Distribuídos

Este projeto é o trabalho final da disciplina de Sistemas Distribuídos, implementando uma versão em Python do PASID-VALIDATOR, uma ferramenta para validação de desempenho em sistemas distribuídos.

## Estrutura do Projeto

```
validator_python/
│
├── src/
│   ├── domain/                    # Componentes principais do sistema
│   │   ├── service.py            # Implementação do serviço de classificação
│   │   ├── load_balancer_proxy.py # Balanceador de carga
│   │   ├── network_manager.py    # Gerenciamento de rede
│   │   ├── service_proxy.py      # Proxy para serviços
│   │   ├── abstract_proxy.py     # Classe base para proxies
│   │   └── source.py             # Implementação do classificador
│   │
│   ├── main.py                   # Ponto de entrada do sistema
│   └── start_services.py         # Inicializador de serviços
│
├── data/
│   ├── train/
│   │   ├── cars/                # Imagens de treinamento - carros
│   │   └── bikes/               # Imagens de treinamento - motos
│
├── config/                       # Configurações do sistema
│
├── vehicle_classifier.pkl        # Modelo treinado (225KB)
└── requirements.txt              # Dependências do projeto
```

## Componentes Principais

### 1. Serviço de Classificação (`service.py`)
- **Funcionalidades**:
  - Classificação de imagens de veículos
  - Treinamento do modelo KNN
  - Servidor TCP para requisições
  - Processamento assíncrono de imagens

- **Características**:
  - Suporte a múltiplas conexões simultâneas
  - Logging detalhado
  - Tratamento de erros robusto
  - Carregamento/salvamento de modelo

### 2. Balanceador de Carga (`load_balancer_proxy.py`)
- **Funcionalidades**:
  - Distribuição de requisições entre serviços
  - Monitoramento de saúde dos serviços
  - Algoritmo round-robin
  - Detecção de falhas

- **Características**:
  - Timeout configurável
  - Contagem de erros
  - Métricas de tempo de resposta
  - Recuperação automática

### 3. Gerenciador de Rede (`network_manager.py`)
- Gerencia comunicação entre serviços
- Implementa protocolos de rede
- Tratamento de conexões

### 4. Proxies (`service_proxy.py`, `abstract_proxy.py`)
- Implementação do padrão Proxy
- Interface comum para serviços
- Encapsulamento de comunicação

## Requisitos Técnicos

### Dependências Principais
- OpenCV (cv2)
- NumPy
- scikit-learn
- PyYAML
- Socket

### Configurações
- Portas padrão: 8083-8086
- Host: localhost
- Timeout: 1 segundo
- Threshold de erros: 3 tentativas

## Funcionalidades do Sistema

1. **Classificação de Imagens**
   - Redimensionamento para 64x64
   - Conversão para escala de cinza
   - Extração de features
   - Classificação KNN

2. **Balanceamento de Carga**
   - Distribuição round-robin
   - Monitoramento de saúde
   - Failover automático
   - Métricas de desempenho

3. **Processamento Distribuído**
   - Múltiplos serviços
   - Comunicação TCP
   - Threads para conexões
   - Processamento assíncrono

## Métricas e Monitoramento

- Tempo de resposta
- Taxa de erros
- Disponibilidade dos serviços
- Contagem de requisições
- Logs detalhados

## Observações de Implementação

1. **Segurança**
   - Validação de entrada
   - Timeout em conexões
   - Tratamento de exceções

2. **Performance**
   - Processamento assíncrono
   - Balanceamento de carga
   - Cache de modelo

3. **Manutenibilidade**
   - Logging estruturado
   - Código modular
   - Configurações externas

## Como Executar

1. Instale as dependências:
```bash
pip install -r requirements.txt
```

2. Inicie os serviços:
```bash
python src/start_services.py
```



