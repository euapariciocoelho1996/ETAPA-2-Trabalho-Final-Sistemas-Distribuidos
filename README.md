# PASID-VALIDATOR - ETAPA 2 - Sistema de Validação de Desempenho em Sistemas Distribuídos

Este projeto é o trabalho final da disciplina de Sistemas Distribuídos, implementando uma versão em Python do PASID-VALIDATOR, uma ferramenta para validação de desempenho em sistemas distribuídos.

## Estrutura do Projeto

```
.
├── config/
│   └── source.yaml      # Configuração da taxa de requisições
├── run_experiments.py   # Script principal de experimentação
├── resultados_impacto_servicos.json  # Resultados dos experimentos
└── grafico_impacto_servicos.png      # Visualização dos resultados
```

## Configurações dos Experimentos

### Variação de Serviços
O sistema foi testado com as seguintes configurações de serviços:
- 2 serviços (1 LB1 + 1 LB2)
- 3 serviços (2 LB1 + 1 LB2)
- 4 serviços (2 LB1 + 2 LB2)

### Taxas de Requisição
Foram testadas três taxas diferentes de requisições:
- 10 req/s
- 20 req/s
- 30 req/s
  
## Estrutura do JSON de Resultados

O arquivo `resultados_impacto_servicos.json` contém os resultados organizados por taxa de requisição:

```json
{
    "10": [
        {
            "total_services": 2,
            "avg_mrt": 0.043,
            "std_dev": 0.045,
            "min_mrt": 0.015,
            "max_mrt": 0.294
        },
        // ... resultados para 3 e 4 serviços
    ],
    "20": [
        // ... resultados para 2, 3 e 4 serviços
    ],
    "30": [
        // ... resultados para 2, 3 e 4 serviços
    ]
}
```

## Interpretação do Gráfico

O gráfico `grafico_impacto_servicos.png` mostra:

![grafico_impacto_servicos](https://github.com/user-attachments/assets/3cb674c3-42c1-4dce-8c3f-bc4ae47e18e0)

1. **Eixo X**: Número total de serviços (2, 3, 4)
2. **Eixo Y**: Tempo médio de resposta em segundos
3. **Linhas**: Cada linha representa uma taxa de requisição diferente
   - Azul: 10 req/s
   - Verde: 20 req/s
   - Vermelho: 30 req/s

### Características do Gráfico
- Cada ponto representa a média dos tempos de resposta
- As linhas mostram a tendência de variação do tempo

## Executando os Experimentos

Para executar os experimentos:

1. Certifique-se de ter o Docker e Docker Compose instalados
2. Execute o script principal:
   ```bash
   python run_experiments.py
   ```

O script irá:
1. Executar os experimentos para cada combinação de serviços e taxas
2. Gerar o arquivo JSON com os resultados
3. Criar o gráfico de análise

## Análise dos Resultados

Os resultados mostram:
1. O impacto do número de serviços no tempo de resposta
2. Como diferentes taxas de requisição afetam o desempenho
3. A relação entre carga do sistema e tempo de resposta

Cada combinação de serviços e taxa de requisição gera um conjunto único de resultados, permitindo analisar o comportamento do sistema sob diferentes condições de carga e infraestrutura.


