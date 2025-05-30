import subprocess
import time
import matplotlib.pyplot as plt
import json
import os

def run_experiment(num_services_lb1, num_services_lb2):
    print(f"\n{'='*50}")
    print(f"Iniciando experimento com LB1: {num_services_lb1} serviços e LB2: {num_services_lb2} serviços")
    print(f"{'='*50}\n")
    
    # Configura as variáveis de ambiente
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
                print(f"MRT encontrado: {mrt_float}s")
            except Exception as e:
                print(f"Erro ao processar linha: {line}")
                print(f"Erro: {str(e)}")
                continue
    
    if not mrt_list:
        print("Nenhum MRT encontrado nos logs!")
        return None
    
    total_services = num_services_lb1 + num_services_lb2
    # A média inicial não será usada diretamente no resumo final, mas pode ser útil para debug
    initial_avg_mrt = sum(mrt_list) / len(mrt_list) if mrt_list else 0
    
    # Cria a tupla de resultados brutos
    raw_resultado = (total_services, initial_avg_mrt, mrt_list)
    
    print(f"\nResultados brutos do experimento:")
    print(f"Total de serviços: {total_services}")
    print(f"Média inicial dos MRTs: {initial_avg_mrt:.2f}s")
    print(f"Lista completa de MRTs: {mrt_list}")
    print(f"\nTupla de resultados brutos: {raw_resultado}")
    
    return raw_resultado

def main():
    # Configurações de experimento
    configurations = [
        (1, 1),  # LB1: 1 serviço, LB2: 1 serviço
        (2, 1),  # LB1: 2 serviços, LB2: 1 serviço
        (1, 2),  # LB1: 1 serviço, LB2: 2 serviços
        (2, 2),  # LB1: 2 serviços, LB2: 2 serviços
    ]
    
    raw_resultados = []
    
    print("\nIniciando série de experimentos...")
    
    # Executa os experimentos e coleta resultados brutos
    for lb1, lb2 in configurations:
        raw_resultado = run_experiment(lb1, lb2)
        if raw_resultado:
            raw_resultados.append(raw_resultado)
    
    # --- Processamento dos resultados para garantir o mesmo tamanho de subarrays ---
    processed_resultados = []
    min_mrt_list_length = float('inf')
    
    # Encontra o tamanho mínimo da lista de MRTs
    for _, _, mrt_list in raw_resultados:
        if mrt_list and len(mrt_list) < min_mrt_list_length:
            min_mrt_list_length = len(mrt_list)
            
    if min_mrt_list_length == float('inf') or min_mrt_list_length == 0:
        print("\nNenhum MRT coletado em nenhum experimento. Não é possível processar os resultados.")
        return # Sai da função main se não houver dados

    print(f"\nTamanho mínimo de MRTs coletados em um experimento: {min_mrt_list_length}")
    print("Processando resultados para padronizar o tamanho das listas de MRTs...")
    
    # Processa cada resultado
    for total_services, _, mrt_list in raw_resultados:
        # Trunca a lista de MRTs para o tamanho mínimo
        truncated_mrt_list = mrt_list[:min_mrt_list_length]
        
        # Recalcula a média com base na lista truncada
        processed_avg_mrt = sum(truncated_mrt_list) / len(truncated_mrt_list) if truncated_mrt_list else 0
        
        # Adiciona o resultado processado à nova lista
        processed_resultados.append((total_services, processed_avg_mrt, truncated_mrt_list))
        
    # Agora, use processed_resultados para o resumo final, JSON e gráfico
    resultados = processed_resultados
    # --- Fim do processamento ---

    # Mostra o resumo final dos resultados processados
    print("\n" + "="*50)
    print("RESUMO FINAL DOS RESULTADOS PROCESSADOS")
    print("="*50)
    print("resultados = [")
    for r in resultados:
        # Exibe a tupla formatada
        # Formatando a lista de MRTs para exibição mais limpa se for muito longa
        mrt_list_display = f"[{', '.join([f'{x:.3f}' for x in r[2]])}]" if len(r[2]) <= 20 else f"[{', '.join([f'{x:.3f}' for x in r[2][:10]])}, ..., {len(r[2])} valores]"
        print(f"    ({r[0]}, {r[1]:.3f}, {mrt_list_display}),") # Formatando média para 3 casas decimais e lista formatada
    print("]")
    print("="*50)
    
    # Salva os resultados processados em um arquivo JSON
    print("\nSalvando resultados processados em resultados_experimentos.json...")
    # Para salvar no JSON, usamos a lista original de MRTs (não a string formatada para display)
    resultados_para_json = [(r[0], r[1], r[2]) for r in processed_resultados]
    with open('resultados_experimentos.json', 'w') as f:
        json.dump(resultados_para_json, f, indent=4)
    
    # Gera o gráfico com os resultados processados
    print("\nGerando gráfico de resultados processados...")
    plt.figure(figsize=(10, 6))
    
    x_values = [r[0] for r in resultados]  # Total de serviços
    y_values = [r[1] for r in resultados]  # Média dos MRTs processados

    plt.plot(x_values, y_values, 'bo-', label='Média MRT Processada')
    
    # Define os ticks do eixo x para serem apenas os valores inteiros de total_services
    plt.xticks(sorted(list(set(x_values))))

    plt.xlabel('Total de Serviços')
    plt.ylabel('Tempo Médio de Resposta (s)')
    plt.title('Impacto do Número de Serviços no Tempo de Resposta (MRTs Padronizados)')
    plt.grid(True)
    plt.legend()
    
    # Salva o gráfico
    plt.savefig('grafico_resultados_processados.png')
    plt.close()
    
    print("\nExperimentos concluídos e resultados processados salvos!")
    print("Resultados processados salvos em:")
    print("- resultados_experimentos.json")
    print("- grafico_resultados_processados.png")

if __name__ == "__main__":
    main() 