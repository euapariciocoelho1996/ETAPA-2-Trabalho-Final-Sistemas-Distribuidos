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

def run_experiment(num_services_lb1, num_services_lb2):
    print(f"\n{'='*50}")
    print(f"Iniciando experimento com LB1: {num_services_lb1} serviços e LB2: {num_services_lb2} serviços")
    print(f"{'='*50}\n")
    
    # Configura as variáveis de ambiente para o número de serviços
    os.environ['NUM_SERVICES_LB1'] = str(num_services_lb1)
    os.environ['NUM_SERVICES_LB2'] = str(num_services_lb2)
    
    # Inicia os containers
    print("Iniciando containers...")
    # Usamos --build aqui para garantir que as mudanças no source.yaml sejam aplicadas, se necessário.
    # Para o primeiro conjunto de experimentos, o build é apenas na primeira vez.
    # Para o segundo conjunto, será a cada mudança de request_rate.
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
                # print(f"MRT encontrado: {mrt_float}s") # Descomente para ver MRTs individuais
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
    # --- Primeira série de experimentos: Variando a quantidade de serviços ---
    print("\n" + "#"*50)
    print("## Série 1: Variando a quantidade de serviços ##")
    print("#"*50)

    configurations_services = [
        (1, 1),  # LB1: 1 serviço, LB2: 1 serviço (Total 2)
        (2, 1),  # LB1: 2 serviços, LB2: 1 serviço (Total 3)
        (1, 2),  # LB1: 1 serviço, LB2: 2 serviços (Total 3)
        (2, 2),  # LB1: 2 serviços, LB2: 2 serviços (Total 4)
    ]
    
    raw_resultados_services = []
    
    print("\nIniciando série de experimentos com variação de serviços...")
    
    # Executa os experimentos e coleta resultados brutos
    # Garante que a taxa de requisição padrão (10) esteja no config antes da primeira série
    update_source_config(10)
    
    for lb1, lb2 in configurations_services:
        raw_resultado = run_experiment(lb1, lb2)
        if raw_resultado:
            raw_resultados_services.append(raw_resultado)
    
    # --- Processamento dos resultados da Série 1 para garantir o mesmo tamanho de subarrays ---
    processed_resultados_services = []
    min_mrt_list_length_services = float('inf')
    
    # Encontra o tamanho mínimo da lista de MRTs na Série 1
    for _, _, mrt_list in raw_resultados_services:
        if mrt_list and len(mrt_list) < min_mrt_list_length_services:
            min_mrt_list_length_services = len(mrt_list)
            
    if min_mrt_list_length_services == float('inf') or min_mrt_list_length_services == 0:
        print("\nNenhum MRT coletado na Série 1. Não é possível processar os resultados desta série.")
    else:
        print(f"\nTamanho mínimo de MRTs coletados na Série 1: {min_mrt_list_length_services}")
        print("Processando resultados da Série 1 para padronizar o tamanho das listas de MRTs...")
        
        # Processa cada resultado da Série 1
        for total_services, _, mrt_list in raw_resultados_services:
            # Trunca a lista de MRTs para o tamanho mínimo
            truncated_mrt_list = mrt_list[:min_mrt_list_length_services]
            
            # Recalcula a média com base na lista truncada
            processed_avg_mrt = sum(truncated_mrt_list) / len(truncated_mrt_list) if truncated_mrt_list else 0
            
            # Adiciona o resultado processado à nova lista
            processed_resultados_services.append((total_services, processed_avg_mrt, truncated_mrt_list))
            
        # --- Fim do processamento da Série 1 ---

        # Mostra o resumo final dos resultados processados da Série 1
        print("\n" + "="*50)
        print("RESUMO FINAL DOS RESULTADOS PROCESSADOS (Série 1: Variação de Serviços)")
        print("="*50)
        print("resultados_servicos = [")
        for r in processed_resultados_services:
            mrt_list_display = f"[{', '.join([f'{x:.3f}' for x in r[2]])}]" if len(r[2]) <= 20 else f"[{', '.join([f'{x:.3f}' for x in r[2][:10]])}, ..., {len(r[2])} valores]"
            print(f"    ({r[0]}, {r[1]:.3f}, {mrt_list_display}),")
        print("]")
        print("="*50)
        
        # Salva os resultados processados da Série 1 em um arquivo JSON separado
        print("\nSalvando resultados processados da Série 1 em resultados_experimentos_servicos.json...")
        resultados_para_json_services = [(r[0], r[1], r[2]) for r in processed_resultados_services]
        with open('resultados_experimentos_servicos.json', 'w') as f:
            json.dump(resultados_para_json_services, f, indent=4)
        
        # Gera o gráfico da Série 1
        print("\nGerando gráfico de resultados processados (Série 1)...")
        plt.figure(figsize=(10, 6))
        
        x_values_services = [r[0] for r in processed_resultados_services]  # Total de serviços
        y_values_services = [r[1] for r in processed_resultados_services]  # Média dos MRTs processados

        plt.plot(x_values_services, y_values_services, 'bo-', label='Média MRT Processada')
        
        plt.xticks(sorted(list(set(x_values_services)))) # Garante ticks inteiros no eixo x

        plt.xlabel('Total de Serviços')
        plt.ylabel('Tempo Médio de Resposta (s)')
        plt.title('Impacto do Número de Serviços no Tempo de Resposta (Série 1: Variação de Serviços)')
        plt.grid(True)
        plt.legend()
        
        # Salva o gráfico
        plt.savefig('grafico_resultados_processados_servicos.png')
        plt.close()
        
        print("Resultados e gráfico da Série 1 salvos em:")
        print("- resultados_experimentos_servicos.json")
        print("- grafico_resultados_processados_servicos.png")

    # --- Segunda série de experimentos: Variando a taxa de requisição ---
    print("\n" + "#"*50)
    print("## Série 2: Variando a taxa de requisição ##")
    print("#"*50)
    
    request_rates = [100, 200, 500] # Taxas de requisição para testar
    num_services_lb1_fixed = 2 # Quantidade fixa de serviços para LB1
    num_services_lb2_fixed = 2 # Quantidade fixa de serviços para LB2 (Total 4)
    
    raw_resultados_rate = []
    
    print(f"\nIniciando série de experimentos com variação da taxa de requisição (Serviços fixos: LB1={num_services_lb1_fixed}, LB2={num_services_lb2_fixed})...")
    
    # Executa os experimentos para diferentes taxas de requisição
    for rate in request_rates:
        # Atualiza o arquivo de configuração antes de cada experimento
        update_source_config(rate)
        # Executa o experimento com a quantidade fixa de serviços
        raw_resultado = run_experiment(num_services_lb1_fixed, num_services_lb2_fixed)
        if raw_resultado:
            raw_resultados_rate.append((rate, raw_resultado[1], raw_resultado[2])) # Armazena (request_rate, media_mrt, lista_mrts)
            
    # --- Processamento dos resultados da Série 2 para garantir o mesmo tamanho de subarrays ---
    processed_resultados_rate = []
    min_mrt_list_length_rate = float('inf')
    
    # Encontra o tamanho mínimo da lista de MRTs na Série 2
    for _, _, mrt_list in raw_resultados_rate:
        if mrt_list and len(mrt_list) < min_mrt_list_length_rate:
            min_mrt_list_length_rate = len(mrt_list)
            
    if min_mrt_list_length_rate == float('inf') or min_mrt_list_length_rate == 0:
        print("\nNenhum MRT coletado na Série 2. Não é possível processar os resultados desta série.")
    else:
        print(f"\nTamanho mínimo de MRTs coletados na Série 2: {min_mrt_list_length_rate}")
        print("Processando resultados da Série 2 para padronizar o tamanho das listas de MRTs...")
        
        # Processa cada resultado da Série 2
        for rate, _, mrt_list in raw_resultados_rate:
            # Trunca a lista de MRTs para o tamanho mínimo
            truncated_mrt_list = mrt_list[:min_mrt_list_length_rate]
            
            # Recalcula a média com base na lista truncada
            processed_avg_mrt = sum(truncated_mrt_list) / len(truncated_mrt_list) if truncated_mrt_list else 0
            
            # Adiciona o resultado processado à nova lista
            processed_resultados_rate.append((rate, processed_avg_mrt, truncated_mrt_list)) # Armazena (request_rate, nova_media, lista_truncada)
            
        # --- Fim do processamento da Série 2 ---

        # Mostra o resumo final dos resultados processados da Série 2
        print("\n" + "="*50)
        print("RESUMO FINAL DOS RESULTADOS PROCESSADOS (Série 2: Variação da Taxa de Requisição)")
        print("="*50)
        print("resultados_taxa = [")
        for r in processed_resultados_rate:
            mrt_list_display = f"[{', '.join([f'{x:.3f}' for x in r[2]])}]" if len(r[2]) <= 20 else f"[{', '.join([f'{x:.3f}' for x in r[2][:10]])}, ..., {len(r[2])} valores]"
            print(f"    ({r[0]}, {r[1]:.3f}, {mrt_list_display}),") # Formato (request_rate, media, lista)
        print("]")
        print("#"*50)
        
        # Salva os resultados processados da Série 2 em um arquivo JSON separado
        print("\nSalvando resultados processados da Série 2 em resultados_experimentos_taxa.json...")
        resultados_para_json_rate = [(r[0], r[1], r[2]) for r in processed_resultados_rate]
        with open('resultados_experimentos_taxa.json', 'w') as f:
            json.dump(resultados_para_json_rate, f, indent=4)
        
        # Gera o gráfico da Série 2
        print("\nGerando gráfico de resultados processados (Série 2)...")
        plt.figure(figsize=(10, 6))
        
        x_values_rate = [r[0] for r in processed_resultados_rate]  # Taxa de requisição
        y_values_rate = [r[1] for r in processed_resultados_rate]  # Média dos MRTs processados

        plt.plot(x_values_rate, y_values_rate, 'bo-', label='Média MRT Processada')
        
        plt.xticks(sorted(list(set(x_values_rate)))) # Garante ticks inteiros no eixo x (se as taxas forem inteiras)

        plt.xlabel('Taxa de Requisição (req/s)')
        plt.ylabel('Tempo Médio de Resposta (s)')
        plt.title('Impacto da Taxa de Requisição no Tempo de Resposta (Série 2: Variação da Taxa)')
        plt.grid(True)
        plt.legend()
        
        # Salva o gráfico
        plt.savefig('grafico_resultados_processados_taxa.png')
        plt.close()
        
        print("Resultados e gráfico da Série 2 salvos em:")
        print("- resultados_experimentos_taxa.json")
        print("- grafico_resultados_processados_taxa.png")
        
    # --- Fim da Série 2 ---

    print("\n" + "="*50)
    print("TODAS AS SÉRIES DE EXPERIMENTOS CONCLUÍDAS")
    print("="*50)


if __name__ == "__main__":
    main() 