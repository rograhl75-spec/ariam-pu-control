HEAD
import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
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

df_base.columns = [str(c).strip() for c in df_base.columns]

df_base['Expositor_Filtro'] = df_base['Expositor'].fillna("GERAL").astype(str).str.strip()
df_base['Componente_Filtro'] = df_base['Componente'].fillna("GERAL").astype(str).str.strip()
df_base['Codigo_Item_Filtro'] = df_base['Codigo_Item'].fillna("0000").astype(str).str.strip()
df_base['Descricao_Filtro'] = df_base['Descricao'].fillna("").astype(str).str.strip()
df_base['Item_Descricao_Completo'] = df_base['Codigo_Item_Filtro'] + " — " + df_base['Descricao_Filtro']
df_base['Maquina_Filtro'] = df_base['Maquina'].fillna("Krauss Maffei 40/40").astype(str).str.strip()

aba_producao, aba_qualidade_pesagem, aba_qualidade_reatividade, aba_inspecao_semanal, aba_anomalias = st.tabs([
    "⚙️ Painel de Produção & Máquinas", 
    "⚖️ Controle de Pesagem (Campo)", 
    "🧪 Controle de Reatividade (DOC 0001/15)",
    "📑 Inspeções Semanais & Relatórios",
    "⚠️ Registro de Anomalias & 5W1H"
])

with aba_producao:
    st.subheader("📦 Pesquisa Avançada")
    
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
        st.write(f"**Volume do Molde:** {dados_p['Volume']} m³")
        st.write(f"**Condição Climática Ativa:** {dados_p['Condicao_Climatica']}")
        
        st.metric("⚖️ MASSA IDEAL NA BALANÇA", f"{dados_p['Massa_Trabalho']:.2f} kg", f"Nominal: {dados_p['Massa_Nominal']} kg")
        st.metric("⏱️ TEMPO NO TIMER", f"{dados_p['Tempo_Injecao_Seg']:.2f} segundos", f"Vazão Calibrada: {dados_p['Vazao_Cabecote_g_s']} g/s")

    with col_info2:
        st.markdown("### 🛠️ Especificações de Processo & Densidades")
        st.markdown(f"""
        * **Injetora:** {dados_p['Maquina_Filtro']}
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
    if "APROVADO" in str(dados_p['Status_Estrutural']):
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

# ABA 4: INSPEÇÕES SEMANAIS & RELATÓRIO TÉCNICO COM UPLOAD FLEXÍVEL DE FOTO (CÂMERA TRASEIRA OU GALERIA)
with aba_inspecao_semanal:
    st.subheader("📑 Gestão de Inspeções Semanais & Relatório Técnico ABNT")
    st.markdown("Realize a inspeção técnica selecionando a máquina específica abaixo, adicione fotos e gere o laudo.")
    
    st.markdown("### 1️⃣ Seleção da Injetora Alvo")
    insp_maquina = st.selectbox("Injetora / Cabeçote Alvo da Inspeção:", [
        "Krauss Maffei 40/40 (Cabeçote 1)", 
        "Krauss Maffei 80/80 (Cabeçote 2)"
    ])
    
    with st.form("form_inspecao_semana"):
        st.markdown("### 2️⃣ Identificação da Auditoria")
        c_insp1, c_insp2 = st.columns(2)
        with c_insp1:
            fuso_br = timezone(timedelta(hours=-3))
            insp_data = st.date_input("Data da Inspeção", datetime.now(fuso_br).date())
            insp_responsavel = st.text_input("Responsável Técnico", "Rogério Grahl — CREA SC 1039223-9")
            
        with c_insp2:
            insp_semana = st.text_input("Semana de Referência / Período", "Semana 35 / 2026")

        st.markdown("---")
        st.markdown(f"### 3️⃣ Avaliação dos Pilares da Produção — {insp_maquina}")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### 🛠️ Manutenção & Equipamentos")
            insp_manut_status = st.selectbox("Status Manutenção do Cabeçote:", ["Conforme", "Parcialmente Conforme", "Não Conforme"])
            insp_manut_obs = st.text_area("Observações de Manutenção:", placeholder="Ex: Vazamentos, calibração de vazão, bicos...")
            
            st.markdown("#### ⚖️ Controle de Pesagem & Reatividade")
            insp_peso_status = st.selectbox("Status Desvios de Pesagem:", ["Dentro da tolerância (±50g)", "Desvio Moderado", "Desvio Crítico (>100g)"])
            insp_peso_obs = st.text_area("Observações de Pesagem:", placeholder="Ex: Análise das taras, médias de injeção...")

        with col_p2:
            st.markdown("#### 🔍 Qualidade de Espuma & Processo")
            insp_qual_status = st.selectbox("Status Conformidade Físico-Estrutural:", ["Aprovado (NBR 8082)", "Alerta de Deformação", "Reprovado"])
            insp_qual_obs = st.text_area("Observações de Qualidade:", placeholder="Ex: Células fechadas, retrabalhos, aderência...")
            
            st.markdown("#### 🦺 Segurança Operacional & Meio Ambiente")
            insp_seg_status = st.selectbox("Status EPIs, Ventilação e Ciclopentano (HC):", ["Conforme", "Advertência", "Paralisação Recomendada"])
            insp_seg_obs = st.text_area("Observações de Segurança:", placeholder="Ex: Exaustão ativa, detectores de gás, EPIs...")

        st.markdown("---")
        st.markdown("### 4️⃣ Anexo de Evidência Fotográfica & Conclusão")
        
        # UPLOADFLEXÍVEL: Permite tirar foto com a câmera traseira do tablet ou escolher da galeria
        foto_enviada = st.file_uploader("📸 Enviar Foto do Local / Equipamento (Usa a câmera traseira ou galeria)", type=["jpg", "jpeg", "png"])
        
        insp_fotos_desc = st.text_area("Registro Descritivo das Evidências Visuais:", placeholder="Descreva os pontos inspecionados visualmente...")
        insp_conclusao = st.text_area("Conclusão Executiva & Recomendações Técnicas:", placeholder="Diretrizes gerais para a gestão desta máquina...")

        btn_gerar_relatorio = st.form_submit_button("Gerar Relatório Técnico Padronizado (ABNT)")

        if btn_gerar_relatorio:
            img_html_tag = ""
            if foto_enviada is not None:
                import base64
                bytes_data = foto_enviada.getvalue()
                base64_str = base64.b64encode(bytes_data).decode("utf-8")
                img_html_tag = f'<div style="text-align: center; margin: 15px 0;"><img src="data:image/jpeg;base64,{base64_str}" style="max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 4px;"/><p style="font-size: 11px; color: #555;">Figura 1 - Evidência Fotográfica em Campo ({insp_maquina})</p></div>'

            html_relatorio = f"""
            <div style="font-family: Arial, sans-serif; padding: 25px; border: 1px solid #ccc; background-color: #fafafa; color: #000;">
                <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #111;">GRAHL CONSULTORIA E TREINAMENTOS</h2>
                    <p style="margin: 5px 0; font-size: 14px; color: #555;">Gestão de Injeção, Reologia e Qualidade em Poliuretano</p>
                    <h3 style="margin-top: 15px; color: #222;">RELATÓRIO TÉCNICO DE INSPEÇÃO SEMANAL</h3>
                    <p style="margin: 5px 0; font-size: 15px; font-weight: bold; color: #0056b3;">{insp_maquina}</p>
                </div>
                
                <table style="width: 100%; font-size: 13px; margin-bottom: 20px; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Período:</strong> {insp_semana}</td>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Data da Emissão:</strong> {insp_data.strftime('%d/%m/%Y')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Injetora Alvo:</strong> {insp_maquina}</td>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Responsável:</strong> {insp_responsavel}</td>
                    </tr>
                </table>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">1. SUMÁRIO EXECUTIVO</h4>
                <p style="font-size: 13px; line-height: 1.5;">O presente relatório consolida a auditoria técnica semanal realizada na linha de injeção <strong>{insp_maquina}</strong>, contemplando verificação de reatividade, desvios de massa/pesagem, integridade mecânica e conformidade regulamentar.</p>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">2. PARECER DOS PILARES OPERACIONAIS</h4>
                <table style="width: 100%; font-size: 13px; border-collapse: collapse; margin-bottom: 20px;">
                    <tr style="background-color: #eaeaea;">
                        <th style="padding: 8px; border: 1px solid #ccc; text-align: left;">Pilar de Avaliação</th>
                        <th style="padding: 8px; border: 1px solid #ccc; text-align: left;">Status</th>
                        <th style="padding: 8px; border: 1px solid #ccc; text-align: left;">Apontamentos de Campo</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Manutenção</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_manut_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_manut_obs}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Pesagem / Reatividade</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_peso_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_peso_obs}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Qualidade Estrutural</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_qual_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_qual_obs}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Segurança & HC</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_seg_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_seg_obs}</td>
                    </tr>
                </table>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">3. EVIDÊNCIAS FOTOGRÁFICAS</h4>
                {img_html_tag}
                <p style="font-size: 13px; line-height: 1.5; background: #fff; padding: 10px; border: 1px dashed #ccc;">{insp_fotos_desc}</p>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">4. CONCLUSÃO E RECOMENDAÇÕES</h4>
                <p style="font-size: 13px; line-height: 1.5; background: #fff; padding: 10px; border: 1px dashed #ccc;">{insp_conclusao}</p>

                <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #ddd; padding-top: 10px;">
                    Documento gerado eletronicamente via <strong>ARIAM PU 4.0</strong> — Grahl Consultoria e Treinamentos.
                </div>
            </div>
            """
            
            st.success(f"Relatório técnico para **{insp_maquina}** gerado com sucesso!")
            st.markdown("---")
            st.markdown("### 📄 Visualização do Laudo Técnico (Padrão ABNT)")
            st.markdown(html_relatorio, unsafe_allow_html=True)
            
            st.download_button(
                label="📥 Baixar Relatório Técnico (.html / Word)",
                data=html_relatorio,
                file_name=f"Relatorio_Inspecao_{insp_semana.replace(' ', '_')}_{'40_40' if '40/40' in insp_maquina else '80_80'}.html",
                mime="text/html"
            )

# ABA 5: REGISTRO DE ANOMALIAS + ID DE PENDÊNCIA + VISUALIZADOR DETALHADO
with aba_anomalias:
    st.subheader("⚠️ Registro de Anomalias & Abertura de Ocorrência")
    st.markdown("Registre a não conformidade. Um número de ID (Pendência) será gerado automaticamente.")
    
    agenda_emails = {
        "Rogério Grahl (Engenheiro Consultor) — Rograhl75@gmail.com": "Rograhl75@gmail.com",
        "Pedro Mantovani (Gerente Slitter) — pedro.mantovani@fastgondolas.com.br": "pedro.mantovani@fastgondolas.com.br",
        "Israel Silva (Gerente Montagem) — israel.silva@ariamequipamentos.com.br": "israel.silva@ariamequipamentos.com.br",
        "Roberto Silva (Supervisor Qualidade) — roberto.silva@fastgondolas.com.br": "roberto.silva@fastgondolas.com.br",
        "André Caseiro (Engenharia Processos) — andre.caseiro@ariamequipamentos.com.br": "andre.caseiro@ariamequipamentos.com.br",
        "Robson Milanez (Gerente Manutenção) — robson.milanez@fastgondolas.com.br": "robson.milanez@fastgondolas.com.br",
        "Gledston Santana (Gerente Qualidade) — gledston.santana@fastgondolas.com.br": "gledston.santana@fastgondolas.com.br"
    }
    
    with st.form("form_anomalia"):
        st.markdown("### 1️⃣ Dados da Ocorrência")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            fuso_br = timezone(timedelta(hours=-3))
            data_atual_br = datetime.now(fuso_br).date()
            a_data = st.date_input("Data da Ocorrência", data_atual_br, key="anom_data")
            a_maquina = st.selectbox("Injetora / Máquina Afetada", df_base['Maquina_Filtro'].unique().tolist())
        with col_a2:
            resp_selecionado = st.selectbox("Direcionar para o Responsável:", list(agenda_emails.keys()))
            a_email_destino = agenda_emails[resp_selecionado]
            a_responsavel_cargo = resp_selecionado.split(" — ")[0]
            
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
                arq_anomalias = "Log_Registro_Anomalias.xlsx"
                
                try:
                    df_temp_id = pd.read_excel(arq_anomalias)
                    proximo_id = f"OC-{len(df_temp_id) + 1:03d}"
                except:
                    proximo_id = "OC-001"

                fuso_br = timezone(timedelta(hours=-3))
                a_hora_sistema = datetime.now(fuso_br).strftime("%H:%M")
                
                novo_reg_anom = {
                    "ID": proximo_id,
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
                    msg['Subject'] = f"[ALERTA PU 4.0 - {proximo_id}] Não Conformidade em {a_maquina}"
                    
                    corpo_email = f"""
                    Prezado(a) {a_responsavel_cargo},
                    
                    Uma nova ocorrência ({proximo_id}) foi aberta no sistema ARIAM PU Control 4.0 e requer sua atenção:
                    
                    - ID da Pendência: {proximo_id}
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
                    
                    st.success(f"Ocorrência **{proximo_id}** salva e e-mail de alerta disparado com sucesso para **{a_email_destino}**!")
                except Exception as ex:
                    st.warning(f"Ocorrência {proximo_id} salva com sucesso na planilha, mas houve falha no envio do e-mail: {ex}")

    if os.path.exists("Log_Registro_Anomalias.xlsx"):
        st.markdown("---")
        st.markdown("### 📊 Histórico Geral de Ocorrências & Pendências")
        df_hist = pd.read_excel("Log_Registro_Anomalias.xlsx")
        
        if 'ID' not in df_hist.columns:
            df_hist.insert(0, 'ID', [f"OC-{i+1:03d}" for i in range(len(df_hist))])
            df_hist.to_excel("Log_Registro_Anomalias.xlsx", index=False)
            
        colunas_resumo = ['ID', 'Data', 'Hora', 'Máquina', 'Responsável', 'Status']
        st.dataframe(df_hist[colunas_resumo], width='stretch')
        
        st.markdown("#### 🔍 Detalhes da Ocorrência & Plano 5W1H")
        lista_ids = df_hist['ID'].tolist()
        id_selecionado = st.selectbox("Selecione o ID da Pendência para ver a descrição completa:", lista_ids)
        
        if id_selecionado:
            registro_detalhe = df_hist[df_hist['ID'] == id_selecionado].iloc[0]
            
            st.info(f"**Pendência:** {registro_detalhe['ID']} | **Data/Hora:** {registro_detalhe['Data']} às {registro_detalhe['Hora']} | **Máquina:** {registro_detalhe['Máquina']}")
            st.markdown(f"**👤 Responsável:** {registro_detalhe['Responsável']} (`{registro_detalhe['E-mail Destino']}`)")
            st.markdown(f"**⚠️ Descrição do Problema:**\n> {registro_detalhe['Problema']}")
            
            with st.expander("📋 Ver Matriz 5W1H Completa desta Ocorrência"):
                c_ex1, c_ex2 = st.columns(2)
                with c_ex1:
                    st.write(f"**What (Ação):** {registro_detalhe['What (Ação)']}")
                    st.write(f"**Why (Justificativa):** {registro_detalhe['Why (Por que)']}")
                    st.write(f"**Where (Local):** {registro_detalhe['Where (Onde)']}")
                with c_ex2:
                    st.write(f"**When (Prazo):** {registro_detalhe['When (Quando)']}")
                    st.write(f"**Who (Quem):** {registro_detalhe['Who (Quem)']}")
                    st.write(f"**How (Método):** {registro_detalhe['How (Como)']}")
                st.write(f"**Status Atual:** {registro_detalhe['Status']}")

st.markdown("---")
=======
import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
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

df_base.columns = [str(c).strip() for c in df_base.columns]

df_base['Expositor_Filtro'] = df_base['Expositor'].fillna("GERAL").astype(str).str.strip()
df_base['Componente_Filtro'] = df_base['Componente'].fillna("GERAL").astype(str).str.strip()
df_base['Codigo_Item_Filtro'] = df_base['Codigo_Item'].fillna("0000").astype(str).str.strip()
df_base['Descricao_Filtro'] = df_base['Descricao'].fillna("").astype(str).str.strip()
df_base['Item_Descricao_Completo'] = df_base['Codigo_Item_Filtro'] + " — " + df_base['Descricao_Filtro']
df_base['Maquina_Filtro'] = df_base['Maquina'].fillna("Krauss Maffei 40/40").astype(str).str.strip()

aba_producao, aba_qualidade_pesagem, aba_qualidade_reatividade, aba_inspecao_semanal, aba_anomalias = st.tabs([
    "⚙️ Painel de Produção & Máquinas", 
    "⚖️ Controle de Pesagem (Campo)", 
    "🧪 Controle de Reatividade (DOC 0001/15)",
    "📑 Inspeções Semanais & Relatórios",
    "⚠️ Registro de Anomalias & 5W1H"
])

with aba_producao:
    st.subheader("📦 Pesquisa Avançada")
    
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
        st.write(f"**Volume do Molde:** {dados_p['Volume']} m³")
        st.write(f"**Condição Climática Ativa:** {dados_p['Condicao_Climatica']}")
        
        st.metric("⚖️ MASSA IDEAL NA BALANÇA", f"{dados_p['Massa_Trabalho']:.2f} kg", f"Nominal: {dados_p['Massa_Nominal']} kg")
        st.metric("⏱️ TEMPO NO TIMER", f"{dados_p['Tempo_Injecao_Seg']:.2f} segundos", f"Vazão Calibrada: {dados_p['Vazao_Cabecote_g_s']} g/s")

    with col_info2:
        st.markdown("### 🛠️ Especificações de Processo & Densidades")
        st.markdown(f"""
        * **Injetora:** {dados_p['Maquina_Filtro']}
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
    if "APROVADO" in str(dados_p['Status_Estrutural']):
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

# ABA 4: INSPEÇÕES SEMANAIS & RELATÓRIO TÉCNICO COM UPLOAD FLEXÍVEL DE FOTO (CÂMERA TRASEIRA OU GALERIA)
with aba_inspecao_semanal:
    st.subheader("📑 Gestão de Inspeções Semanais & Relatório Técnico ABNT")
    st.markdown("Realize a inspeção técnica selecionando a máquina específica abaixo, adicione fotos e gere o laudo.")
    
    st.markdown("### 1️⃣ Seleção da Injetora Alvo")
    insp_maquina = st.selectbox("Injetora / Cabeçote Alvo da Inspeção:", [
        "Krauss Maffei 40/40 (Cabeçote 1)", 
        "Krauss Maffei 80/80 (Cabeçote 2)"
    ])
    
    with st.form("form_inspecao_semana"):
        st.markdown("### 2️⃣ Identificação da Auditoria")
        c_insp1, c_insp2 = st.columns(2)
        with c_insp1:
            fuso_br = timezone(timedelta(hours=-3))
            insp_data = st.date_input("Data da Inspeção", datetime.now(fuso_br).date())
            insp_responsavel = st.text_input("Responsável Técnico", "Rogério Grahl — CREA SC 1039223-9")
            
        with c_insp2:
            insp_semana = st.text_input("Semana de Referência / Período", "Semana 35 / 2026")

        st.markdown("---")
        st.markdown(f"### 3️⃣ Avaliação dos Pilares da Produção — {insp_maquina}")
        
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.markdown("#### 🛠️ Manutenção & Equipamentos")
            insp_manut_status = st.selectbox("Status Manutenção do Cabeçote:", ["Conforme", "Parcialmente Conforme", "Não Conforme"])
            insp_manut_obs = st.text_area("Observações de Manutenção:", placeholder="Ex: Vazamentos, calibração de vazão, bicos...")
            
            st.markdown("#### ⚖️ Controle de Pesagem & Reatividade")
            insp_peso_status = st.selectbox("Status Desvios de Pesagem:", ["Dentro da tolerância (±50g)", "Desvio Moderado", "Desvio Crítico (>100g)"])
            insp_peso_obs = st.text_area("Observações de Pesagem:", placeholder="Ex: Análise das taras, médias de injeção...")

        with col_p2:
            st.markdown("#### 🔍 Qualidade de Espuma & Processo")
            insp_qual_status = st.selectbox("Status Conformidade Físico-Estrutural:", ["Aprovado (NBR 8082)", "Alerta de Deformação", "Reprovado"])
            insp_qual_obs = st.text_area("Observações de Qualidade:", placeholder="Ex: Células fechadas, retrabalhos, aderência...")
            
            st.markdown("#### 🦺 Segurança Operacional & Meio Ambiente")
            insp_seg_status = st.selectbox("Status EPIs, Ventilação e Ciclopentano (HC):", ["Conforme", "Advertência", "Paralisação Recomendada"])
            insp_seg_obs = st.text_area("Observações de Segurança:", placeholder="Ex: Exaustão ativa, detectores de gás, EPIs...")

        st.markdown("---")
        st.markdown("### 4️⃣ Anexo de Evidência Fotográfica & Conclusão")
        
        # UPLOADFLEXÍVEL: Permite tirar foto com a câmera traseira do tablet ou escolher da galeria
        foto_enviada = st.file_uploader("📸 Enviar Foto do Local / Equipamento (Usa a câmera traseira ou galeria)", type=["jpg", "jpeg", "png"])
        
        insp_fotos_desc = st.text_area("Registro Descritivo das Evidências Visuais:", placeholder="Descreva os pontos inspecionados visualmente...")
        insp_conclusao = st.text_area("Conclusão Executiva & Recomendações Técnicas:", placeholder="Diretrizes gerais para a gestão desta máquina...")

        btn_gerar_relatorio = st.form_submit_button("Gerar Relatório Técnico Padronizado (ABNT)")

        if btn_gerar_relatorio:
            img_html_tag = ""
            if foto_enviada is not None:
                import base64
                bytes_data = foto_enviada.getvalue()
                base64_str = base64.b64encode(bytes_data).decode("utf-8")
                img_html_tag = f'<div style="text-align: center; margin: 15px 0;"><img src="data:image/jpeg;base64,{base64_str}" style="max-width: 100%; height: auto; border: 1px solid #ccc; border-radius: 4px;"/><p style="font-size: 11px; color: #555;">Figura 1 - Evidência Fotográfica em Campo ({insp_maquina})</p></div>'

            html_relatorio = f"""
            <div style="font-family: Arial, sans-serif; padding: 25px; border: 1px solid #ccc; background-color: #fafafa; color: #000;">
                <div style="text-align: center; border-bottom: 2px solid #333; padding-bottom: 15px; margin-bottom: 20px;">
                    <h2 style="margin: 0; color: #111;">GRAHL CONSULTORIA E TREINAMENTOS</h2>
                    <p style="margin: 5px 0; font-size: 14px; color: #555;">Gestão de Injeção, Reologia e Qualidade em Poliuretano</p>
                    <h3 style="margin-top: 15px; color: #222;">RELATÓRIO TÉCNICO DE INSPEÇÃO SEMANAL</h3>
                    <p style="margin: 5px 0; font-size: 15px; font-weight: bold; color: #0056b3;">{insp_maquina}</p>
                </div>
                
                <table style="width: 100%; font-size: 13px; margin-bottom: 20px; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Período:</strong> {insp_semana}</td>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Data da Emissão:</strong> {insp_data.strftime('%d/%m/%Y')}</td>
                    </tr>
                    <tr>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Injetora Alvo:</strong> {insp_maquina}</td>
                        <td style="padding: 6px; border: 1px solid #ddd;"><strong>Responsável:</strong> {insp_responsavel}</td>
                    </tr>
                </table>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">1. SUMÁRIO EXECUTIVO</h4>
                <p style="font-size: 13px; line-height: 1.5;">O presente relatório consolida a auditoria técnica semanal realizada na linha de injeção <strong>{insp_maquina}</strong>, contemplando verificação de reatividade, desvios de massa/pesagem, integridade mecânica e conformidade regulamentar.</p>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">2. PARECER DOS PILARES OPERACIONAIS</h4>
                <table style="width: 100%; font-size: 13px; border-collapse: collapse; margin-bottom: 20px;">
                    <tr style="background-color: #eaeaea;">
                        <th style="padding: 8px; border: 1px solid #ccc; text-align: left;">Pilar de Avaliação</th>
                        <th style="padding: 8px; border: 1px solid #ccc; text-align: left;">Status</th>
                        <th style="padding: 8px; border: 1px solid #ccc; text-align: left;">Apontamentos de Campo</th>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Manutenção</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_manut_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_manut_obs}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Pesagem / Reatividade</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_peso_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_peso_obs}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Qualidade Estrutural</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_qual_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_qual_obs}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border: 1px solid #ccc;"><strong>Segurança & HC</strong></td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_seg_status}</td>
                        <td style="padding: 8px; border: 1px solid #ccc;">{insp_seg_obs}</td>
                    </tr>
                </table>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">3. EVIDÊNCIAS FOTOGRÁFICAS</h4>
                {img_html_tag}
                <p style="font-size: 13px; line-height: 1.5; background: #fff; padding: 10px; border: 1px dashed #ccc;">{insp_fotos_desc}</p>

                <h4 style="color: #333; border-left: 4px solid #0056b3; padding-left: 8px;">4. CONCLUSÃO E RECOMENDAÇÕES</h4>
                <p style="font-size: 13px; line-height: 1.5; background: #fff; padding: 10px; border: 1px dashed #ccc;">{insp_conclusao}</p>

                <div style="margin-top: 30px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #ddd; padding-top: 10px;">
                    Documento gerado eletronicamente via <strong>ARIAM PU 4.0</strong> — Grahl Consultoria e Treinamentos.
                </div>
            </div>
            """
            
            st.success(f"Relatório técnico para **{insp_maquina}** gerado com sucesso!")
            st.markdown("---")
            st.markdown("### 📄 Visualização do Laudo Técnico (Padrão ABNT)")
            st.markdown(html_relatorio, unsafe_allow_html=True)
            
            st.download_button(
                label="📥 Baixar Relatório Técnico (.html / Word)",
                data=html_relatorio,
                file_name=f"Relatorio_Inspecao_{insp_semana.replace(' ', '_')}_{'40_40' if '40/40' in insp_maquina else '80_80'}.html",
                mime="text/html"
            )

# ABA 5: REGISTRO DE ANOMALIAS + ID DE PENDÊNCIA + VISUALIZADOR DETALHADO
with aba_anomalias:
    st.subheader("⚠️ Registro de Anomalias & Abertura de Ocorrência")
    st.markdown("Registre a não conformidade. Um número de ID (Pendência) será gerado automaticamente.")
    
    agenda_emails = {
        "Rogério Grahl (Engenheiro Consultor) — Rograhl75@gmail.com": "Rograhl75@gmail.com",
        "Pedro Mantovani (Gerente Slitter) — pedro.mantovani@fastgondolas.com.br": "pedro.mantovani@fastgondolas.com.br",
        "Israel Silva (Gerente Montagem) — israel.silva@ariamequipamentos.com.br": "israel.silva@ariamequipamentos.com.br",
        "Roberto Silva (Supervisor Qualidade) — roberto.silva@fastgondolas.com.br": "roberto.silva@fastgondolas.com.br",
        "André Caseiro (Engenharia Processos) — andre.caseiro@ariamequipamentos.com.br": "andre.caseiro@ariamequipamentos.com.br",
        "Robson Milanez (Gerente Manutenção) — robson.milanez@fastgondolas.com.br": "robson.milanez@fastgondolas.com.br",
        "Gledston Santana (Gerente Qualidade) — gledston.santana@fastgondolas.com.br": "gledston.santana@fastgondolas.com.br"
    }
    
    with st.form("form_anomalia"):
        st.markdown("### 1️⃣ Dados da Ocorrência")
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            fuso_br = timezone(timedelta(hours=-3))
            data_atual_br = datetime.now(fuso_br).date()
            a_data = st.date_input("Data da Ocorrência", data_atual_br, key="anom_data")
            a_maquina = st.selectbox("Injetora / Máquina Afetada", df_base['Maquina_Filtro'].unique().tolist())
        with col_a2:
            resp_selecionado = st.selectbox("Direcionar para o Responsável:", list(agenda_emails.keys()))
            a_email_destino = agenda_emails[resp_selecionado]
            a_responsavel_cargo = resp_selecionado.split(" — ")[0]
            
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
                arq_anomalias = "Log_Registro_Anomalias.xlsx"
                
                try:
                    df_temp_id = pd.read_excel(arq_anomalias)
                    proximo_id = f"OC-{len(df_temp_id) + 1:03d}"
                except:
                    proximo_id = "OC-001"

                fuso_br = timezone(timedelta(hours=-3))
                a_hora_sistema = datetime.now(fuso_br).strftime("%H:%M")
                
                novo_reg_anom = {
                    "ID": proximo_id,
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
                    msg['Subject'] = f"[ALERTA PU 4.0 - {proximo_id}] Não Conformidade em {a_maquina}"
                    
                    corpo_email = f"""
                    Prezado(a) {a_responsavel_cargo},
                    
                    Uma nova ocorrência ({proximo_id}) foi aberta no sistema ARIAM PU Control 4.0 e requer sua atenção:
                    
                    - ID da Pendência: {proximo_id}
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
                    
                    st.success(f"Ocorrência **{proximo_id}** salva e e-mail de alerta disparado com sucesso para **{a_email_destino}**!")
                except Exception as ex:
                    st.warning(f"Ocorrência {proximo_id} salva com sucesso na planilha, mas houve falha no envio do e-mail: {ex}")

    if os.path.exists("Log_Registro_Anomalias.xlsx"):
        st.markdown("---")
        st.markdown("### 📊 Histórico Geral de Ocorrências & Pendências")
        df_hist = pd.read_excel("Log_Registro_Anomalias.xlsx")
        
        if 'ID' not in df_hist.columns:
            df_hist.insert(0, 'ID', [f"OC-{i+1:03d}" for i in range(len(df_hist))])
            df_hist.to_excel("Log_Registro_Anomalias.xlsx", index=False)
            
        colunas_resumo = ['ID', 'Data', 'Hora', 'Máquina', 'Responsável', 'Status']
        st.dataframe(df_hist[colunas_resumo], width='stretch')
        
        st.markdown("#### 🔍 Detalhes da Ocorrência & Plano 5W1H")
        lista_ids = df_hist['ID'].tolist()
        id_selecionado = st.selectbox("Selecione o ID da Pendência para ver a descrição completa:", lista_ids)
        
        if id_selecionado:
            registro_detalhe = df_hist[df_hist['ID'] == id_selecionado].iloc[0]
            
            st.info(f"**Pendência:** {registro_detalhe['ID']} | **Data/Hora:** {registro_detalhe['Data']} às {registro_detalhe['Hora']} | **Máquina:** {registro_detalhe['Máquina']}")
            st.markdown(f"**👤 Responsável:** {registro_detalhe['Responsável']} (`{registro_detalhe['E-mail Destino']}`)")
            st.markdown(f"**⚠️ Descrição do Problema:**\n> {registro_detalhe['Problema']}")
            
            with st.expander("📋 Ver Matriz 5W1H Completa desta Ocorrência"):
                c_ex1, c_ex2 = st.columns(2)
                with c_ex1:
                    st.write(f"**What (Ação):** {registro_detalhe['What (Ação)']}")
                    st.write(f"**Why (Justificativa):** {registro_detalhe['Why (Por que)']}")
                    st.write(f"**Where (Local):** {registro_detalhe['Where (Onde)']}")
                with c_ex2:
                    st.write(f"**When (Prazo):** {registro_detalhe['When (Quando)']}")
                    st.write(f"**Who (Quem):** {registro_detalhe['Who (Quem)']}")
                    st.write(f"**How (Método):** {registro_detalhe['How (Como)']}")
                st.write(f"**Status Atual:** {registro_detalhe['Status']}")

st.markdown("---")
>>>>>>> 458b589ff3dac91b5ee174898462e3bb4591b766
st.caption("Grahl Consultoria e Treinamentos — Tecnologia aplicada ao chão de fábrica.")