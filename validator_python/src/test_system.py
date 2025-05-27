import requests
import time
import json
import cv2
import numpy as np
from typing import List, Dict
import matplotlib.pyplot as plt

def load_test_image(image_path: str) -> bytes:
    """Carrega uma imagem de teste."""
    with open(image_path, 'rb') as f:
        return f.read()

def test_system(image_path: str, num_requests: int = 100) -> Dict:
    """Testa o sistema com múltiplas requisições."""
    results = {
        'response_times': [],
        'success_count': 0,
        'error_count': 0
    }
    
    # Carrega a imagem de teste
    image_data = load_test_image(image_path)
    
    # Faz as requisições
    for i in range(num_requests):
        start_time = time.time()
        try:
            response = requests.post(
                'http://localhost:8001/classify',
                data=image_data,
                headers={'Content-Type': 'application/octet-stream'}
            )
            
            if response.status_code == 200:
                results['success_count'] += 1
                results['response_times'].append((time.time() - start_time) * 1000)  # ms
            else:
                results['error_count'] += 1
                
        except Exception as e:
            print(f"Erro na requisição {i}: {str(e)}")
            results['error_count'] += 1
            
        # Pequena pausa entre requisições
        time.sleep(0.1)
    
    return results

def plot_results(results: Dict):
    """Plota os resultados do teste."""
    plt.figure(figsize=(10, 6))
    
    # Histograma dos tempos de resposta
    plt.hist(results['response_times'], bins=20)
    plt.xlabel('Tempo de Resposta (ms)')
    plt.ylabel('Frequência')
    plt.title('Distribuição dos Tempos de Resposta')
    
    # Adiciona informações de sucesso/erro
    plt.text(0.95, 0.95, 
             f'Sucessos: {results["success_count"]}\nErros: {results["error_count"]}',
             transform=plt.gca().transAxes,
             verticalalignment='top',
             horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    plt.savefig('test_results.png')
    plt.close()

def main():
    # Testa o sistema com uma imagem
    results = test_system('data/test/test_image.jpg', num_requests=100)
    
    # Plota os resultados
    plot_results(results)
    
    # Calcula e exibe estatísticas
    if results['response_times']:
        avg_time = sum(results['response_times']) / len(results['response_times'])
        print(f"\nEstatísticas do Teste:")
        print(f"Requisições bem-sucedidas: {results['success_count']}")
        print(f"Requisições com erro: {results['error_count']}")
        print(f"Tempo médio de resposta: {avg_time:.2f} ms")
        print(f"Tempo mínimo: {min(results['response_times']):.2f} ms")
        print(f"Tempo máximo: {max(results['response_times']):.2f} ms")

if __name__ == '__main__':
    main() 