import matplotlib.pyplot as plt
import numpy as np
import json
import os
from typing import List, Dict
import seaborn as sns

def load_performance_data(file_path: str) -> Dict:
    """Carrega os dados de performance de um arquivo JSON."""
    with open(file_path, 'r') as f:
        return json.load(f)

def plot_mrt_vs_generation_rate(data: Dict, output_file: str):
    """Plota o gráfico de MRT vs Taxa de Geração."""
    plt.figure(figsize=(10, 6))
    
    # Configuração do estilo
    sns.set_style("whitegrid")
    
    # Dados para o eixo X (taxa de geração)
    generation_rates = np.array(data['generation_rates'])
    
    # Plota cada configuração de serviço
    for service_config in data['service_configs']:
        mrt_values = np.array(service_config['mrt_values'])
        plt.plot(generation_rates, mrt_values, 
                label=f"{service_config['num_services']} serviços",
                marker='o')
    
    plt.xlabel('Taxa de Geração (requisições/segundo)')
    plt.ylabel('MRT (ms)')
    plt.title('MRT vs Taxa de Geração')
    plt.legend()
    plt.grid(True)
    
    # Salva o gráfico
    plt.savefig(output_file)
    plt.close()

def plot_service_comparison(data: Dict, output_file: str):
    """Plota o gráfico comparando diferentes configurações de serviço."""
    plt.figure(figsize=(10, 6))
    
    # Configuração do estilo
    sns.set_style("whitegrid")
    
    # Dados para o eixo X (número de serviços)
    num_services = np.array(data['num_services'])
    
    # Plota cada taxa de geração
    for rate in data['generation_rates']:
        mrt_values = np.array(data['mrt_by_rate'][str(rate)])
        plt.plot(num_services, mrt_values,
                label=f"Taxa: {rate} req/s",
                marker='o')
    
    plt.xlabel('Número de Serviços')
    plt.ylabel('MRT (ms)')
    plt.title('MRT vs Número de Serviços')
    plt.legend()
    plt.grid(True)
    
    # Salva o gráfico
    plt.savefig(output_file)
    plt.close()

def main():
    # Carrega os dados de performance
    performance_data = load_performance_data('performance_data.json')
    
    # Gera os gráficos
    plot_mrt_vs_generation_rate(performance_data, 'mrt_vs_generation_rate.png')
    plot_service_comparison(performance_data, 'service_comparison.png')

if __name__ == '__main__':
    main() 