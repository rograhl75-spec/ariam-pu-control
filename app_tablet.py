import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Grahl PU Control 4.0", page_icon="🏭", layout="wide")

col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    logo_path = "logo.jpg" if os.path.exists("logo.jpg") else ("logo.png" if os.path.exists("logo.png") else None)
    if logo_path:
        st.image(logo_path, width=180)
with col_titulo:
    st.title("ARIAM PU 4.0 - Assistente Técnico de Campo")
    st.markdown("**Grahl Consultoria e Treinamentos** | Gestão de Injeção, Reologia e Qualidade")

st.markdown("---")

# GARANTIR QUE O RELATÓRIO EXCEL EXISTA
if not os.path.exists("Relatorio_Processo_Injecao_Atualizado.xlsx"):
    try:
        import automacao_grahl
    except Exception as e:
        st.error(f"Erro crítico ao gerar base de dados automática: {e}")
        st.stop()

@st.cache_data(ttl=600)
def obter_temp():
    try:
        r = requests.get("https://api.open-meteo.com/v1/forecast?latitude=-23.31028&longitude=-51.16278&current_weather=true", timeout=4)
        return float(r.json()['current_weather']['temperature'])
    except:
        return 24.0

temp_externa = obter_temp()

if temp_externa < 22.0:
    cond_clima = "❄️ MODO FRIO (<22°C)"
elif temp_externa > 28.0:
    cond_clima = "🔥 MODO CALOR (>28°C)"
else:
    cond_clima = "✅ MODO NOMINAL (Estável)"

st.sidebar.header(f"🌡️ Clima Externo: {temp_externa} °C")
st.sidebar.markdown(f"**Status Térmico:** {cond_clima}")

try:
    df_base = pd.read_excel("Relatorio_Processo_Injecao_Atualizado.xlsx")
except Exception as e:
    st.error(f"Erro ao ler a planilha de dados: {e}")
    st.stop()

# MAPEAMENTO FÍSICO EXATO PELAS COLUNAS DO EXCEL:
# Coluna B = Índice 1 (Expositor)
# Coluna C = Índice 2 (Componente)
# Coluna D = Índice 3 (Item)
# Coluna E = Índice 4 (Descrição)
# Coluna F = Índice 5 (Cabeçote)

# Garantimos que o DataFrame tenha pelo menos 6 colunas para evitar erros de índice
while df_base.shape[1] < 6:
    df_base[f'Col_{df_base.shape[1]}'] = ""

df_base['Expositor_Filtro'] = df_base.iloc[:, 1].fillna("").astype(str).str.strip()
df_base['Componente_Filtro'] = df_base.iloc[:, 2].fillna("").astype(str).str.strip()
df_base['Item_Filtro'] = df_base.iloc[:, 3].fillna("").astype(str).str.strip()
df_base['Descricao_Filtro'] = df_base.iloc[:, 4].fillna("").astype(str).str.strip()

# Tradução da Coluna F (Cabeçote) para Injetora
def traduzir_cabecote(val):
    val_str = str(val).strip()
    if "1" in val_str:
        return "Krauss Maffei 40/40"
    elif "2" in val_str:
        return "Krauss Maffei 80/80"
    else:
        return val_str if val_str and val_str != "nan" else "Krauss Maffei 40/40"

df_base['Maquina_Filtro'] = df_base.iloc[:, 5].apply(traduzir_cabecote)

# Concatenado de Item e Descrição (Colunas D e E)
df_base['Item_Descricao_Completo'] = df_base['Item_Filtro'] + " — " + df_base['Descricao_Filtro']

aba_producao, aba_qualidade_pesagem, aba_qualidade_reatividade, aba_anomalias = st.tabs([
    "⚙️ Painel de Produção & Máquinas", 
    "⚖️ Controle de Pesagem (Campo)", 
    "🧪 Controle de Reatividade (DOC 0001/15)",
    "⚠️ Registro de Anomalias & 5W1H"
])

with aba_producao:
    st.subheader("📦 Pesquisa Avançada")
    
    # Linha 1: Injetora e Expositor (Coluna B)
    col_l1_c1, col_l1_c2 = st.columns(2)
    with col_l1_c1:
        maq_opcoes = ["Todas"] + df_base['Maquina_Filtro'].unique().tolist()
        filtro_maq = st.selectbox("Injetora:", maq_opcoes)
        
    df_f = df_base.copy()
    if filtro_maq != "Todas":
        df_f = df_f[df_f['Maquina_Filtro'] == filtro_maq]
        
    with col_l1_c2:
        exp_opcoes = ["Todos"] + df_f['Expositor_Filtro'].unique().tolist()
        filtro_exp = st.selectbox("Expositor:", exp_opcoes)
        
    if filtro_exp != "Todos":
        df_f = df_f[df_f['Expositor_Filtro'] == filtro_exp]

    # Linha 2: Componente (Coluna C) e Item/Descrição (Colunas D e E)
    col_l2_c1, col_l2_c2 = st.columns(2)
    with col_l2_c1:
        comp_opcoes = ["Todos"] + df_f['Componente_Filtro'].unique().tolist()
        filtro_comp = st.selectbox("Componente:", comp_opcoes)
        
    if filtro_comp != "Todos":
        df_f = df_f[df_f['Componente_Filtro'] == filtro_comp]
        
    with col_l2_c2:
        item_desc_opcoes = ["Todos"] + df_f['Item_Descricao_Completo'].unique().tolist()
        filtro_item_desc = st.selectbox("Item / Descrição:", item_desc_opcoes)
        
    if filtro_item_desc != "Todos":
        df_f = df_f[df_f['Item_Descricao_Completo'] == filtro_item_desc]
        
    if len(df_f) == 0:
        st.warning("Nenhum item encontrado com os filtros selecionados.")
        st.stop()
        
    dados_p = df_f.iloc[0]
    
    st.markdown("---")

    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown(f"### ⚙️ Alvo no CLP — {dados_p['Maquina_Filtro']}")
        st.info(f"**Expositor:** {dados_p['Expositor_Filtro']} | **Componente:** {dados_p['Componente_Filtro']}\n\n**Item / Descrição:** {dados_p['Item_Descricao_Completo']}")
        st.write(f"**Volume do Molde:** {dados_p.get('Volume', 0)} m³")
        st.write(f"**Condição Climática Ativa:** {dados_p.get('Condicao_Climatica', 'Nominal')}")
        
        st.metric("⚖️ MASSA IDEAL NA BALANÇA", f"{dados_p.get('Massa_Trabalho', 0):.2f} kg", f"Nominal: {dados_p.get('Massa_Nominal', 0)} kg")
        st.metric("⏱️ TEMPO NO TIMER", f"{dados_p.get('Tempo_Injecao_Seg', 0):.2f} segundos", f"Vazão Calibrada: {dados_p.get('Vazao_Cabecote_g_s', 0)} g/s")

    with col_info2:
        st.markdown("### 🛠️ Especificações de Processo & Densidades")
        st.markdown(f"""
        * **Injetora:** {dados_p['Maquina_Filtro']}
        * **Vazão Calibrada:** {dados_p.get('Vazao_Cabecote_g_s', 0)} g/s
        * **Pressão de Injeção Alvo:** {dados_p.get('Pressao_Injecao', 0)}
        * **Relação I/P (Iso/Poliol):** {dados_p.get('Relacao_Iso_Pol', 0)}
        * **Densidade Mínima (Calor / Underpacking):** `{dados_p.get('Densidade_Calor', 0):.2f} kg/m³`
        * **Densidade Nominal (Estável):** `{dados_p.get('Densidade_Nominal', 0):.2f} kg/m³`
        * **Densidade Máxima (Frio / Overpacking):** `{dados_p.get('Densidade_Frio', 0):.2f} kg/m³`
        * **🎯 Densidade Real Injetada (Ativa):** **`{dados_p.get('Densidade_Real_Calculada', 0):.2f} kg/m³`**
        * **Temperatura dos Moldes:** {dados_p.get('Temp_Moldes_C', 0)}
        * **Setpoint dos Tanques:** {dados_p.get('Setpoint_Material_C', 0)} °C
        * **Teor de Ciclopentano (HC):** 9,71 % em peso
        """)

    st.markdown("---")
    st.subheader("🔬 Validação Estrutural (Resistência à Compressão NBR 8082)")
    res1, res2 = st.columns(2)
    res1.metric("Resistência Estimada", f"{dados_p.get('Resistencia_Compressao_Est_kPa', 0):.1f} kPa", "Mínimo regulamentar: 110 kPa")
    status_mec = str(dados_p.get('Status_Estrutural', 'APROVADO'))
    if "APROVADO" in status_mec:
        res2.success(f"Status Mecânico: {status_mec}")
    else:
        res2.error(f"Status Mecânico: {status_mec}")

with aba_qualidade_pesagem:
    st.subheader("⚖️ Controle de Pesagem em Campo")
    with st.form("form_pesagem"):
        f_data = st.date_input("Data da Inspeção", datetime.now())
        f_modelo = st.text_input("Modelo / Expositor", "ILHA 2100")
        f_pesagem_antes = st.number_input("Pesagem da Peça Antes (kg)", value=38.0)
        f_pesagem_depois = st.number_input("Pesagem da Peça Depois (kg)", value=51.4)
        f_massa_prog = st.number_input("Massa Programada no CLP (g)", value=13110)
        
        btn_salvar_peso = st.form_submit_button("Salvar Registro de Pesagem")
        if btn_salvar_peso:
            massa_real_calculada = (f_pesagem_depois - f_pesagem_antes) * 1000
            dif_gramas = massa_real_calculada - f_massa_prog
            novo_registro = {
                "Data": f_data.strftime("%d/%m/%Y"),
                "Modelo": f_modelo,
                "Pesagem Antes (kg)": f_pesagem_antes,
                "Pesagem Depois (kg)": f_pesagem_depois,
                "Massa Programada (g)": f_massa_prog,
                "Massa Real Medida (g)": massa_real_calculada,
                "Diferença (g)": f"+{dif_gramas:.1f} g" if dif_gramas >= 0 else f"{dif_gramas:.1f} g"
            }
            arquivo_log_peso = "Log_Controle_Pesagem_Campo.xlsx"
            try:
                df_log_p = pd.read_excel(arquivo_log_peso)
                df_log_p = pd.concat([df_log_p, pd.DataFrame([novo_registro])], ignore_index=True)
            except:
                df_log_p = pd.DataFrame([novo_registro])
            df_log_p.to_excel(arquivo_log_peso, index=False)
            st.success(f"Pesagem registrada com sucesso! Desvio: {dif_gramas:+.1f} g.")

    if os.path.exists("Log_Controle_Pesagem_Campo.xlsx"):
        st.markdown("### 📊 Histórico de Pesagens")
        st.dataframe(pd.read_excel("Log_Controle_Pesagem_Campo.xlsx"))

with aba_qualidade_reatividade:
    st.subheader("🧪 Controle de Reatividade de Copo (DOC 0001/15)")
    with st.form("form_reatividade"):
        r_data = st.date_input("Data do Ensaio", datetime.now(), key="r_data")
        r_hora = st.text_input("Hora do Ensaio", "08:30")
        r_cabecote = st.selectbox("Cabeçote de Injeção", [1, 2])
        r_temp_poliol = st.number_input("Temperatura Poliol Tanque (°C)", value=24.5)
        r_temp_iso = st.number_input("Temperatura Isocianato Tanque (°C)", value=23.0)
        r_dens_livre = st.number_input("Densidade Livre de Copo (kg/m³)", value=25.2)
        r_creme = st.number_input("Tempo de Creme (s)", value=5.0)
        r_gel = st.number_input("Tempo de Gel (s)", value=49.0)
        r_pega = st.text_input("Tempo de Pega Livre", "1:12")
        r_resp = st.text_input("Responsável Técnico / Inspetor", "Rogério / Carlos")
        
        btn_salvar_reat = st.form_submit_button("Salvar Ensaio de Reatividade")
        if btn_salvar_reat:
            novo_reat = {
                "Data": r_data.strftime("%d/%m/%Y"),
                "Hora": r_hora,
                "Cabeçote": r_cabecote,
                "Temp Poliol (°C)": r_temp_poliol,
                "Temp Iso (°C)": r_temp_iso,
                "Densidade Livre (kg/m³)": r_dens_livre,
                "Tempo Creme (s)": r_creme,
                "Tempo Gel (s)": r_gel,
                "Tempo Pega": r_pega,
                "Responsável": r_resp
            }
            arquivo_log_reat = "Log_Controle_Reatividade_DOC0001.xlsx"
            try:
                df_log_r = pd.read_excel(arquivo_log_reat)
                df_log_r = pd.concat([df_log_r, pd.DataFrame([novo_reat])], ignore_index=True)
            except:
                df_log_r = pd.DataFrame([novo_reat])
            df_log_r.to_excel(arquivo_log_reat, index=False)
            st.success("Ensaio de reatividade salvo com sucesso!")

    if os.path.exists("Log_Controle_Reatividade_DOC0001.xlsx"):
        st.markdown("### 📊 Histórico de Reatividade")
        st.dataframe(pd.read_excel("Log_Controle_Reatividade_DOC0001.xlsx"))

# ABA 4: REGISTRO DE ANOMALIAS + HORÁRIO AUTOMÁTICO + 5W1H OPCIONAL + SMTP CONFIGURADO
with aba_anomalias:
    st.subheader("⚠️ Registro de Anomalias & Abertura de Ocorrência")
    st.markdown("Registre a não conformidade. O horário será capturado automaticamente pelo sistema.")
    
    agenda_emails = {
        "Rogério Grahl — Engenheiro Consultor": "Rograhl75@gmail.com",
        "Pedro Mantovani — Gerente Slitter": "pedro.mantovani@fastgondolas.com.br",
        "Israel Silva — Gerente Montagem": "israel.silva@ariamequipamentos.com.br",
        "Roberto Silva — Supervisor Qualidade": "roberto.silva@fastgondolas.com.br",
        "André Caseiro — Engenharia Processos": "andre.caseiro@ariamequipamentos.com.br",
        "Robson Milanez — Gerente Manutenção": "robson.milanez@fastgondolas.com.br",
        "Gledston Santana — Gerente Qualidade": "gledston.santana@fastgondolas.com.br"
    }
    
    with st.form("form_anomalia"):
        st.markdown("### 1️⃣ Dados da Ocorrência")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            a_data = st.date_input("Data da Ocorrência", datetime.now())
            a_maquina = st.selectbox("Injetora / Máquina Afetada", df_base['Maquina_Filtro'].unique().tolist())
        with col_a2:
            a_responsavel_cargo = st.selectbox("Direcionar para o Responsável:", list(agenda_emails.keys()))
            a_email_destino = agenda_emails[a_responsavel_cargo]
            st.text_input("E-mail de Destino:", value=a_email_destino, disabled=True)
            
        a_problema = st.text_area("Descrição do Problema Detectado (Ocorrência):", placeholder="Ex: Desvio de densidade acima do limite superior...")
        
        st.markdown("---")
        st.markdown("### 2️⃣ Matriz de Tratativa Corretiva — 5W1H (Opcional na Abertura)")
        
        col_5w1, col_5w2 = st.columns(2)
        with col_5w1:
            w_what = st.text_input("1. What (Ação Corretiva):", placeholder="Pode ser preenchido posteriormente")
            w_why = st.text_input("2. Why (Justificativa):", placeholder="Pode ser preenchido posteriormente")
            w_where = st.text_input("3. Where (Local):", placeholder="Pode ser preenchido posteriormente")
        with col_5w2:
            w_when = st.text_input("4. When (Prazo limite):", placeholder="Pode ser preenchido posteriormente")
            w_who = st.text_input("5. Who (Quem executará):", placeholder="Pode ser preenchido posteriormente")
            w_how = st.text_input("6. How (Método):", placeholder="Pode ser preenchido posteriormente")

        status_tratativa = st.selectbox("Status da Tratativa:", ["Pendente Ação Corretiva", "Em Andamento (5W1H)", "Concluído & Validado"])
        
        btn_enviar_anomalia = st.form_submit_button("Salvar Ocorrência e Disparar E-mail Imediato")
        
        if btn_enviar_anomalia:
            if not a_problema.strip():
                st.warning("Por favor, descreva o problema antes de salvar a ocorrência.")
            else:
                a_hora_sistema = datetime.now().strftime("%H:%M:%S")
                
                novo_reg_anom = {
                    "Data": a_data.strftime("%d/%m/%Y"),
                    "Hora": a_hora_sistema,
                    "Máquina": a_maquina,
                    "Responsável": a_responsavel_cargo,
                    "E-mail Destino": a_email_destino,
                    "Problema": a_problema,
                    "What (Ação)": w_what if w_what.strip() else "Não informado na abertura",
                    "Why (Por que)": w_why if w_why.strip() else "Não informado na abertura",
                    "Where (Onde)": w_where if w_where.strip() else "Não informado na abertura",
                    "When (Quando)": w_when if w_when.strip() else "Não informado na abertura",
                    "Who (Quem)": w_who if w_who.strip() else "Não informado na abertura",
                    "How (Como)": w_how if w_how.strip() else "Não informado na abertura",
                    "Status": status_tratativa
                }
                arq_anomalias = "Log_Registro_Anomalias.xlsx"
                try:
                    df_anom = pd.read_excel(arq_anomalias)
                    df_anom = pd.concat([df_anom, pd.DataFrame([novo_reg_anom])], ignore_index=True)
                except:
                    df_anom = pd.DataFrame([novo_reg_anom])
                df_anom.to_excel(arq_anomalias, index=False)
                
                try:
                    smtp_server = "smtp.gmail.com"
                    smtp_port = 587
                    remetente_email = "Rograhl75@gmail.com"
                    senha_app = "wrbf oqou loik cwkb"
                    
                    msg = MIMEMultipart()
                    msg['From'] = remetente_email
                    msg['To'] = a_email_destino
                    msg['Subject'] = f"[ALERTA PU 4.0 - OCORRÊNCIA] Não Conformidade em {a_maquina}"
                    
                    corpo_email = f"""
                    Prezado(a) {a_responsavel_cargo},
                    
                    Uma nova ocorrência foi aberta no sistema ARIAM PU Control 4.0 e requer sua atenção:
                    
                    - Data/Hora: {a_data.strftime('%d/%m/%Y')} às {a_hora_sistema}
                    - Máquina Afetada: {a_maquina}
                    - Descrição do Problema: {a_problema}
                    
                    PLANO DE AÇÃO 5W1H (Parcial / Acompanhamento):
                    - What (Ação): {novo_reg_anom['What (Ação)']}
                    - Why (Motivo): {novo_reg_anom['Why (Por que)']}
                    - Where (Local): {novo_reg_anom['Where (Onde)']}
                    - When (Prazo): {novo_reg_anom['When (Quando)']}
                    - Who (Responsável): {novo_reg_anom['Who (Quem)']}
                    - How (Método): {novo_reg_anom['How (Como)']}
                    - Status Atual: {status_tratativa}
                    
                    Atenciosamente,
                    Sistema Automatizado - Grahl Consultoria e Treinamentos
                    """
                    msg.attach(MIMEText(corpo_email, 'plain', 'utf-8'))
                    
                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.starttls()
                    server.login(remetente_email, senha_app)
                    server.sendmail(remetente_email, a_email_destino, msg.as_string())
                    server.quit()
                    
                    st.success(f"Ocorrência salva e e-mail de alerta disparado com sucesso para **{a_email_destino}**!")
                except Exception as ex:
                    st.warning(f"Ocorrência salva com sucesso na planilha (Horário: {a_hora_sistema}), mas houve falha no envio do e-mail: {ex}")

    if os.path.exists("Log_Registro_Anomalias.xlsx"):
        st.markdown("---")
        st.markdown("### 📊 Histórico Geral de Ocorrências & Planos 5W1H")
        st.dataframe(pd.read_excel("Log_Registro_Anomalias.xlsx"))

st.markdown("---")
st.caption("Grahl Consultoria e Treinamentos — Tecnologia aplicada ao chão de fábrica.")