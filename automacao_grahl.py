import os
import pandas as pd
import requests

print("==================================================")
print("   GRAHL CONSULTORIA - AUTOMAÇÃO DE INJEÇÃO DE PU ")
print("==================================================")

arquivo_produtos = "59001000100 - ISOLAMENTO ESPUMADO POLIOL SHPOL SO SH RIG - 26-06-2026.xlsx"

try:
    print("[1/4] Lendo planilhas de processo (CAB 1 e CAB 2)...")
    xls = pd.ExcelFile(arquivo_produtos)
    
    cab1_sheet = [s for s in xls.sheet_names if 'CAB 1' in s][-1]
    cab2_sheet = [s for s in xls.sheet_names if 'CAB 2' in s][-1]
    
    df_c1 = pd.read_excel(arquivo_produtos, sheet_name=cab1_sheet, header=None)
    df_c1_clean = df_c1.iloc[2:].copy()
    df_c1_clean['Maquina'] = "Krauss Maffei 40/40"
    df_c1_clean['Cabecote_Ref'] = 1
    df_c1_clean['Vazao_Cabecote_g_s'] = 650
    df_c1_clean['Pressao_Injecao'] = "130 ± 10 bar"
    
    df_c2 = pd.read_excel(arquivo_produtos, sheet_name=cab2_sheet, header=None)
    df_c2_clean = df_c2.iloc[2:].copy()
    df_c2_clean['Maquina'] = "Krauss Maffei 80/80"
    df_c2_clean['Cabecote_Ref'] = 2
    df_c2_clean['Vazao_Cabecote_g_s'] = 3000
    df_c2_clean['Pressao_Injecao'] = "140 ± 10 bar (Rim)"

    # Mapeamento exato das colunas da planilha original:
    # Índice 1 ou 2: Componente (ex: CAIXA, TAMPA)
    # Índice 2 ou 3: Código do Item
    # Índice 4: Descrição
    # Índice 6: Volume (m3)
    # Índice 7: Massa Nominal (Kg)
    # Índice 8: Massa Frio (Kg)
    # Índice 9: Massa Calor (Kg)
    for df_item in [df_c1_clean, df_c2_clean]:
        df_item.rename(columns={
            1: 'Componente',
            2: 'Codigo_Item',
            4: 'Descricao',
            6: 'Volume',
            7: 'Massa_Nominal',
            8: 'Massa_Frio',
            9: 'Massa_Calor'
        }, inplace=True)

    colunas_interesse = ['Componente', 'Codigo_Item', 'Descricao', 'Volume', 'Massa_Nominal', 'Massa_Frio', 'Massa_Calor', 'Maquina', 'Cabecote_Ref', 'Vazao_Cabecote_g_s', 'Pressao_Injecao']
    
    df_produtos = pd.concat([df_c1_clean[colunas_interesse], df_c2_clean[colunas_interesse]], ignore_index=True)
    df_produtos = df_produtos.dropna(subset=['Codigo_Item', 'Volume'])
    
    print("      -> Abas CAB 1 e CAB 2 unificadas com sucesso!")

except Exception as e:
    print(f"      -> Erro ao ler abas: {e}")
    exit()

df_produtos['Volume'] = pd.to_numeric(df_produtos['Volume'], errors='coerce')
df_produtos['Massa_Nominal'] = pd.to_numeric(df_produtos['Massa_Nominal'], errors='coerce')
df_produtos['Massa_Frio'] = pd.to_numeric(df_produtos['Massa_Frio'], errors='coerce')
df_produtos['Massa_Calor'] = pd.to_numeric(df_produtos['Massa_Calor'], errors='coerce')

df_produtos['Massa_Frio'] = df_produtos['Massa_Frio'].fillna(df_produtos['Massa_Nominal'])
df_produtos['Massa_Calor'] = df_produtos['Massa_Calor'].fillna(df_produtos['Massa_Nominal'])

# 2. CAPTURA AUTOMÁTICA DA METEOROLOGIA EM LONDRINA - PR
print("[2/4] Conectando à API de Meteorologia para Londrina-PR...")
lat, lon = -23.31028, -51.16278
try:
    url_meteo = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
    resposta = requests.get(url_meteo, timeout=5)
    temp_atual = float(resposta.json()['current_weather']['temperature'])
    print(f"      -> Temperatura capturada com sucesso via satélite: {temp_atual} °C")
except Exception:
    temp_atual = 24.0
    print(f"      -> Modo offline ativado. Temperatura padrão: {temp_atual} °C")

# 3. AVALIAÇÃO SAZONAL E CÁLCULO DE DENSIDADES
print("[3/4] Reavaliando parâmetros de máquina, massas e densidades...")
if temp_atual < 22.0:
    df_produtos['Massa_Trabalho'] = df_produtos['Massa_Frio']
    df_produtos['Condicao_Climatica'] = "FRIO (<22°C) - Overpacking"
    df_produtos['Setpoint_Material_C'] = 24.0
elif temp_atual > 28.0:
    df_produtos['Massa_Trabalho'] = df_produtos['Massa_Calor']
    df_produtos['Condicao_Climatica'] = "CALOR (>28°C) - Underpacking"
    df_produtos['Setpoint_Material_C'] = 22.0
else:
    df_produtos['Massa_Trabalho'] = df_produtos['Massa_Nominal']
    df_produtos['Condicao_Climatica'] = "NOMINAL (Estável)"
    df_produtos['Setpoint_Material_C'] = 23.0

df_produtos['Relacao_Iso_Pol'] = "1,34 ± 0,03 pbw"
df_produtos['Temp_Moldes_C'] = "45 ± 5 °C (Mínimo: 40 °C)"

df_produtos['Tempo_Injecao_Seg'] = (df_produtos['Massa_Trabalho'] * 1000) / df_produtos['Vazao_Cabecote_g_s']

df_produtos['Densidade_Nominal'] = df_produtos['Massa_Nominal'] / df_produtos['Volume']
df_produtos['Densidade_Frio'] = df_produtos['Massa_Frio'] / df_produtos['Volume']
df_produtos['Densidade_Calor'] = df_produtos['Massa_Calor'] / df_produtos['Volume']
df_produtos['Densidade_Real_Calculada'] = df_produtos['Massa_Trabalho'] / df_produtos['Volume']

df_produtos['Resistencia_Compressao_Est_kPa'] = (df_produtos['Densidade_Real_Calculada'] * 8.8) - 160
df_produtos['Status_Estrutural'] = df_produtos['Resistencia_Compressao_Est_kPa'].apply(lambda x: "APROVADO" if x >= 110 else "ALERTA: RISCO DE DEFORMAÇÃO")

arquivo_saida = "Relatorio_Processo_Injecao_Atualizado.xlsx"
df_produtos.to_excel(arquivo_saida, index=False)
print(f"[4/4] Planilha avançada gerada com sucesso: '{arquivo_saida}'")