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

# GARANTIR QUE O RELATÓRIO EXCEL EXISTA (Se não estiver na nuvem, roda o ETL integrado)
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

df_base['Componente'] = df_base['Componente'].fillna("GERAL").astype(str)
df_base['Codigo_Item'] = df_base['Codigo_Item'].astype(str)
df_base['Descricao'] = df_base['Descricao'].astype(str)

aba_producao, aba_qualidade_pesagem, aba_qualidade_reatividade, aba_anomalias = st.tabs([
    "⚙️ Painel de Produção & Máquinas", 
    "⚖️ Controle de Pesagem (Campo)", 
    "🧪 Controle de Reatividade (DOC 0001/15)",
    "⚠️ Registro de Anomalias & 5W1H"
])

with aba_producao:
    st.subheader("📦 Pesquisa Avançada (4 Critérios: Injetora, Componente, Item e Descrição)")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    
    with col_f1:
        maq_opcoes = ["Todas"] + df_base['Maquina'].unique().tolist()
        filtro_maq = st.selectbox("1️⃣ Injetora:", maq_opcoes)
        
    df_f = df_base.copy()
    if filtro_maq != "Todas":
        df_f = df_f[df_f['Maquina'] == filtro_maq]
        
    with col_f2:
        comp_opcoes = ["Todos"] + df_f['Componente'].unique().tolist()
        filtro_comp = st.selectbox("2️⃣ Componente:", comp_opcoes)
        
    if filtro_comp != "Todos":
        df_f = df_f[df_f['Componente'] == filtro_comp]
        
    with col_f3:
        item_opcoes = ["Todos"] + df_f['Codigo_Item'].unique().tolist()
        filtro_item = st.selectbox("3️⃣ Código do Item:", item_opcoes)
        
    if filtro_item != "Todos":
        df_f = df_f[df_f['Codigo_Item'] == filtro_item]
        
    with col_f4:
        desc_opcoes = ["Todas"] + df_f['Descricao'].unique().tolist()
        filtro_desc = st.selectbox("4️⃣ Descrição:", desc_opcoes)
        
    if filtro_desc != "Todas":
        df_f = df_f[df_f['Descricao'] == filtro_desc]
        
    if len(df_f) == 0:
        st.warning("Nenhum item encontrado com os filtros selecionados.")
        st.stop()
        
    opcoes_finais = df_f.apply(lambda row: f"[{row['Componente']}] Item {row['Codigo_Item']} — {row['Descricao']} ({row['Maquina']})", axis=1).tolist()
    escolha_final = st.selectbox("🎯 Selecione o item correspondente na lista filtrada:", opcoes_finais)
    
    idx_sel = opcoes_finais.index(escolha_final)
    dados_p = df_f.iloc[idx_sel]
    
    st.markdown("---")

    col_info1, col_info2 = st.columns(2)
    
    with col_info1:
        st.markdown(f"### ⚙️ Alvo no CLP — {dados_p['Maquina']}")
        st.info(f"**Componente:** {dados_p['Componente']} | **Item:** {dados_p['Codigo_Item']}\n\n**Descrição:** {dados_p['Descricao']}")
        st.write(f"**Volume do Molde:** {dados_p['Volume']} m³")
        st.write(f"**Condição Climática Ativa:** {dados_p['Condicao_Climatica']}")
        
        st.metric("⚖️ MASSA IDEAL NA BALANÇA", f"{dados_p['Massa_Trabalho']:.2f} kg", f"Nominal: {dados_p['Massa_Nominal']} kg")
        st.metric("⏱️ TEMPO NO TIMER", f"{dados_p['Tempo_Injecao_Seg']:.2f} segundos", f"Vazão Calibrada: {dados_p['Vazao_Cabecote_g_s']} g/s")

    with col_info2:
        st.markdown("### 🛠️ Especificações de Processo & Densidades")
        st.markdown(f"""
        * **Injetora:** {dados_p['Maquina']}
        * **Vazão Calibrada:** {dados_p['Vazao_Cabecote_g_s']} g/s
        * **Pressão de Injeção Alvo:** {dados_p['Pressao_Injecao']}
        * **Relação I/P (Iso/Poliol):** {dados_p['Relacao_Iso_Pol']}
        * **Densidade Mínima (Calor / Underpacking):** `{dados_p['Densidade_Calor']:.2f} kg/m³`
        * **Densidade Nominal (Estável):** `{dados_p['Densidade_Nominal']:.2f} kg/m³`
        * **Densidade Máxima (Frio / Overpacking):** `{dados_p['Densidade_Frio']:.2f} kg/m³`
        * **🎯 Densidade Real Injetada (Ativa):** **`{dados_p['Densidade_Real_Calculada']:.2f} kg/m³`**
        * **Temperatura dos Moldes:** {dados_p['Temp_Moldes_C']}
        * **Setpoint dos Tanques:** {dados_p['Setpoint_Material_C']} °C
        * **Teor de Ciclopentano (HC):** 9,71 % em peso
        """)

    st.markdown("---")
    st.subheader("🔬 Validação Estrutural (Resistência à Compressão NBR 8082)")
    res1, res2 = st.columns(2)
    res1.metric("Resistência Estimada", f"{dados_p['Resistencia_Compressao_Est_kPa']:.1f} kPa", "Mínimo regulamentar: 110 kPa")
    if "APROVADO" in dados_p['Status_Estrutural']:
        res2.success(f"Status Mecânico: {dados_p['Status_Estrutural']}")
    else:
        res2.error(f"Status Mecânico: {dados_p['Status_Estrutural']}")

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

# ABA 4: REGISTRO DE ANOMALIAS + ENVIO IMEDIATO DE E-MAIL SMTP (5W1H OPCIONAL)
with aba_anomalias:
    st.subheader("⚠️ Registro de Anomalias & Abertura de Ocorrência")
    st.markdown("Registre a não conformidade para envio imediato do alerta por e-mail ao responsável.")
    
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
            a_hora = st.text_input("Horário da Ocorrência", datetime.now().strftime("%H:%M"))
            a_maquina = st.selectbox("Injetora / Máquina Afetada", df_base['Maquina'].unique().tolist())
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
                novo_reg_anom = {
                    "Data": a_data.strftime("%d/%m/%Y"),
                    "Hora": a_hora,
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
                    
                    - Data/Hora: {a_data.strftime('%d/%m/%Y')} às {a_hora}
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
                    st.warning(f"Ocorrência salva com sucesso na planilha, mas houve falha no envio do e-mail: {ex}")

    if os.path.exists("Log_Registro_Anomalias.xlsx"):
        st.markdown("---")
        st.markdown("### 📊 Histórico Geral de Ocorrências & Planos 5W1H")
        st.dataframe(pd.read_excel("Log_Registro_Anomalias.xlsx"))

st.markdown("---")
st.caption("Grahl Consultoria e Treinamentos — Tecnologia aplicada ao chão de fábrica.")