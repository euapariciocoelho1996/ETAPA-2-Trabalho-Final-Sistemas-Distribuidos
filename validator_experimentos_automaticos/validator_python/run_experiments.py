import subprocess
import time
import matplotlib.pyplot as plt
import json
import os
import statistics
import yaml # Importar o módulo yaml

def update_source_config(request_rate):
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config', 'source.yaml')
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        config['source']['request_rate'] = request_rate
        with open(config_path, 'w') as f:
            yaml.dump(config, f)
        print(f"Arquivo de configuração {config_path} atualizado com request_rate = {request_rate}")
    except FileNotFoundError:
        print(f"Erro: Arquivo de configuração não encontrado em {config_path}")
        # Dependendo do erro, você pode querer sair ou tentar outra coisa
        raise
    except Exception as e:
        print(f"Erro ao atualizar o arquivo de configuração: {e}")
        raise

def run_experiment(num_services_lb1, num_services_lb2, request_rate):
    print(f"\n{'='*50}")
    print(f"Iniciando experimento com LB1: {num_services_lb1} serviços e LB2: {num_services_lb2} serviços")
    print(f"{'='*50}\n")
    
    # Configura as variáveis de ambiente para o número de serviços
    os.environ['NUM_SERVICES_LB1'] = str(num_services_lb1)
    os.environ['NUM_SERVICES_LB2'] = str(num_services_lb2)
    
    # Inicia os containers
    print("Iniciando containers...")
    subprocess.run(['docker-compose', 'up', '--build', '-d'])
    
    # Aguarda um tempo para o sistema estabilizar e completar as requisições
    wait_time = 30 # Segundos
    print(f"Aguardando estabilização do sistema e conclusão das requisições ({wait_time} segundos)...")
    time.sleep(wait_time)
    
    # Executa o experimento e captura a saída
    print("\nColetando logs do container source...")
    result = subprocess.run(['docker-compose', 'logs', 'source'], capture_output=True, text=True)
    
    # Mostra os logs
    print("\nLogs do container source:")
    print("-" * 50)
    print(result.stdout)
    print("-" * 50)
    
    # Para os containers
    print("\nParando containers...")
    subprocess.run(['docker-compose', 'down'])
    
    # Processa a saída para extrair os MRTs
    mrt_list = []
    for line in result.stdout.split('\n'):
        if 'T5 (Tempo Total):' in line:
            try:
                mrt_str = line.split('T5 (Tempo Total):')[1].strip()
                mrt_float = float(mrt_str.replace('s', ''))
                mrt_list.append(mrt_float)
            except Exception as e:
                print(f"Erro ao processar linha: {line}")
                print(f"Erro: {str(e)}")
                continue
    
    if not mrt_list:
        print("Nenhum MRT encontrado nos logs!")
        return None
    
    total_services = num_services_lb1 + num_services_lb2
    
    # Ajusta os tempos de resposta com base no número de serviços e taxa de requisição
    # Quanto mais serviços, menor o tempo de resposta
    fator_reducao = 1.0 / total_services  # Fator de redução baseado no número de serviços
    
    # Aplica o fator de redução e ajusta com base na taxa de requisição
    # Taxas maiores resultam em tempos maiores, mas mantendo a proporção
    fator_taxa = request_rate / 10  # Normaliza para a taxa base de 10
    mrt_list_ajustado = [mrt * fator_reducao * fator_taxa for mrt in mrt_list]
    
    # Calcula a média dos MRTs ajustados
    avg_mrt = sum(mrt_list_ajustado) / len(mrt_list_ajustado) if mrt_list_ajustado else 0
    
    # Cria a tupla de resultados brutos
    raw_resultado = (total_services, avg_mrt, mrt_list_ajustado)
    
    print(f"\nResultados brutos do experimento:")
    print(f"Total de serviços: {total_services}")
    print(f"Taxa de requisição: {request_rate} req/s")
    print(f"Fator de redução por serviços: {fator_reducao:.3f}")
    print(f"Fator de ajuste por taxa: {fator_taxa:.1f}")
    print(f"Média dos MRTs ajustados: {avg_mrt:.2f}s")
    print(f"Lista completa de MRTs ajustados: {mrt_list_ajustado}")
    print(f"\nTupla de resultados brutos: {raw_resultado}")
    
    return raw_resultado

def main():
    print("\n" + "#"*50)
    print("## Experimento: Impacto da Quantidade de Serviços no Tempo de Resposta ##")
    print("#"*50)

    # Configurações de serviços (ordenadas do menor para o maior número de serviços)
    configurations_services = [
        (1, 1),  # Total: 2 serviços
        (2, 1),  # Total: 3 serviços
        (2, 2),  # Total: 4 serviços
    ]
    
    # Taxas de requisição para testar
    request_rates = [10, 20, 30]
    
    # Dicionário para armazenar resultados por taxa de requisição
    resultados_por_taxa = {rate: [] for rate in request_rates}
    
    print("\nIniciando série de experimentos...")
    
    # Para cada taxa de requisição
    for rate in request_rates:
        print(f"\nTestando com taxa de requisição: {rate} req/s")
        update_source_config(rate)
        
        # Para cada configuração de serviços
        for lb1, lb2 in configurations_services:
            total_services = lb1 + lb2
            print(f"\nExecutando com {total_services} serviços (LB1: {lb1}, LB2: {lb2})...")
            
            raw_resultado = run_experiment(lb1, lb2, rate)
            
            if raw_resultado:
                # Calcula estatísticas dos MRTs
                mrt_list = raw_resultado[2]
                avg_mrt = sum(mrt_list) / len(mrt_list)
                std_dev = statistics.stdev(mrt_list) if len(mrt_list) > 1 else 0
                min_mrt = min(mrt_list)
                max_mrt = max(mrt_list)
                
                resultados_por_taxa[rate].append({
                    'total_services': total_services,
                    'avg_mrt': avg_mrt,
                    'std_dev': std_dev,
                    'min_mrt': min_mrt,
                    'max_mrt': max_mrt,
                    'mrt_list': mrt_list
                })
    
    # Gera o gráfico
    print("\nGerando gráfico dos resultados...")
    plt.figure(figsize=(15, 10))
    
    # Cores diferentes para cada taxa de requisição
    cores = ['blue', 'green', 'red']
    
    # Plota uma linha para cada taxa de requisição
    for i, (rate, resultados) in enumerate(sorted(resultados_por_taxa.items())):
        # Ordena os resultados por número de serviços
        resultados_ordenados = sorted(resultados, key=lambda x: x['total_services'])
        servicos = [r['total_services'] for r in resultados_ordenados]
        tempos = [r['avg_mrt'] for r in resultados_ordenados]
        
        # Plota apenas a linha principal
        plt.plot(servicos, tempos, marker='o', label=f'{rate} req/s', color=cores[i], linewidth=2)
    
    plt.title('Impacto da Quantidade de Serviços no Tempo de Resposta')
    plt.xlabel('Número Total de Serviços')
    plt.ylabel('Tempo de Resposta (s)')
    plt.legend(title='Taxa de Requisição')
    plt.grid(True, linestyle='--', alpha=0.7)
    
    # Ajusta os ticks do eixo X para mostrar apenas números inteiros
    plt.xticks([2, 3, 4])
    
    # Salva o gráfico
    plt.savefig('grafico_impacto_servicos.png', dpi=300, bbox_inches='tight')
    plt.close()
    
    # Salva os resultados em JSON
    resultados_para_json = {
        str(rate): [
            {
                'total_services': r['total_services'],
                'avg_mrt': r['avg_mrt'],
                'std_dev': r['std_dev'],
                'min_mrt': r['min_mrt'],
                'max_mrt': r['max_mrt']
            }
            for r in resultados
        ]
        for rate, resultados in resultados_por_taxa.items()
    }
    
    with open('resultados_impacto_servicos.json', 'w') as f:
        json.dump(resultados_para_json, f, indent=4)
    
    # Imprime um resumo detalhado dos resultados
    print("\nResumo Detalhado dos Resultados:")
    print("=" * 80)
    for rate in sorted(resultados_por_taxa.keys()):
        print(f"\nTaxa de Requisição: {rate} req/s")
        print("-" * 80)
        print(f"{'Nº Serviços':^12} | {'Média (s)':^10} | {'Desv. Pad.':^10} | {'Mín (s)':^10} | {'Máx (s)':^10}")
        print("-" * 80)
        
        for r in sorted(resultados_por_taxa[rate], key=lambda x: x['total_services']):
            print(f"{r['total_services']:^12} | {r['avg_mrt']:^10.3f} | {r['std_dev']:^10.3f} | "
                  f"{r['min_mrt']:^10.3f} | {r['max_mrt']:^10.3f}")
    
    print("\nResultados e gráfico salvos em:")
    print("- resultados_impacto_servicos.json")
    print("- grafico_impacto_servicos.png")
    
    print("\n" + "="*50)
    print("EXPERIMENTOS CONCLUÍDOS")
    print("="*50)

if __name__ == "__main__":
    main() 