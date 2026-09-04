import os
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, timezone
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import io

# Importação para geração profissional de Word (ABNT / Abadi / Espaçamento 1.5)
try:
    from docx import Document
    from docx.shared import Inches, Pt, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement, parse_xml
    from docx.oxml.ns import qn, nsdecls
    DOCX_DISPONIVEL = True
except ImportError:
    DOCX_DISPONIVEL = False

st.set_page_config(page_title="Grahl PU Control 4.0", page_icon="🏭", layout="wide")

# SISTEMA DE CONTROLE DE ACESSO SEGURO VIA SECRETS
def verificar_senha():
    def senha_correta():
        usuario = st.session_state["username"].strip()
        senha = st.session_state["password"]
        
        usuarios_cadastrados = st.secrets.get("passwords", {})
        
        if usuario in usuarios_cadastrados and usuarios_cadastrados[usuario] == senha:
            st.session_state["senha_correta"] = True
            st.session_state["usuario_atual"] = usuario
            del st.session_state["password"]
        else:
            st.session_state["senha_correta"] = False

    if "senha_correta" not in st.session_state:
        st.markdown("<h2 style='text-align: center; color: #1F4E78;'>🔒 Acesso Restrito — ARIAM PU 4.0</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #555;'>Insira suas credenciais corporativas para acessar o sistema.</p>", unsafe_allow_html=True)
        
        col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
        with col_l2:
            st.text_input("Usuário", key="username")
            st.text_input("Senha", type="password", key="password")
            st.button("Entrar no Sistema", on_click=senha_correta, use_container_width=True)
        return False
    
    elif not st.session_state["senha_correta"]:
        st.error("😕 Usuário ou senha incorretos. Tente novamente.")
        st.text_input("Usuário", key="username")
        st.text_input("Senha", type="password", key="password")
        st.button("Entrar no Sistema", on_click=senha_correta, use_container_width=True)
        return False
        
    return True

if not verificar_senha():
    st.stop()

# CSS PERSONALIZADO PARA REDUZIR A LARGURA DA BARRA LATERAL
st.markdown("""
    <style>
        [data-testid="stSidebar"] {
            min-width: 230px !important;
            max-width: 230px !important;
        }
    </style>
""", unsafe_allow_html=True)

col_logo, col_titulo = st.columns([1, 4])
with col_logo:
    logo_path = "logo.jpg" if os.path.exists("logo.jpg") else ("logo.png" if os.path.exists("logo.png") else None)
    if logo_path:
        st.image(logo_path, width=180)
with col_titulo:
    st.title("ARIAM PU 4.0 - Assistente Técnico de Campo")
    st.markdown("**Grahl Consultoria e Treinamentos** | Gestão de Injeção, Reologia e Qualidade")

st.sidebar.markdown("---")
st.sidebar.write(f"👤 **Conectado como:** `{st.session_state.get('usuario_atual', 'Usuário')}`")
if st.sidebar.button("🚪 Sair do Sistema", use_container_width=True):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

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
    cond_clima = "❄️ Massa Frio (<22°C)"
elif temp_externa > 28.0:
    cond_clima = "🔥 Massa Calor (>28°C)"
else:
    cond_clima = "✅ Massa Nominal (Estável)"

st.sidebar.header(f"🌡️ Clima Externo: {temp_externa} °C")
st.sidebar.markdown(f"**Status Térmico:** {cond_clima}")
st.sidebar.caption("💡 **Utilidade:** Monitora a variação térmica ambiente para orientar o operador sobre os ajustes de reatividade e correções de massa (Frio/Calor) no cabeçote.")

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

# Funções auxiliares para formatação padrão ABNT / Abadi / 1.5 (Fonte 10 pt)
def aplicar_estilo_abadi_e_espacamento(doc):
    if logo_path and os.path.exists(logo_path):
        try:
            doc.add_picture(logo_path, width=Inches(1.8))
            doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        except:
            pass

    style_normal = doc.styles['Normal']
    style_normal.font.name = 'Abadi'
    style_normal.font.size = Pt(10)
    style_normal.font.color.rgb = RGBColor(51, 51, 51)
    style_normal.paragraph_format.line_spacing = 1.5
    style_normal.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.LEFT
    style_normal.paragraph_format.space_after = Pt(6)

def adicionar_assinatura_padrao(doc, responsavel="Rogério Grahl — CREA SC 1039223-9"):
    p_esp = doc.add_paragraph()
    p_esp.paragraph_format.space_before = Pt(20)
    p_esp.paragraph_format.keep_with_next = True
    
    p_linha = doc.add_paragraph()
    p_linha.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_linha.paragraph_format.keep_with_next = True
    p_linha.add_run("__________________________________________________")
    
    p_ass = doc.add_paragraph()
    p_ass.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ass.paragraph_format.keep_with_next = True
    p_ass.paragraph_format.line_spacing = 1.5
    
    run_nome = p_ass.add_run(f"{responsavel}\n")
    run_nome.bold = True
    run_nome.font.name = 'Abadi'
    run_nome.font.size = Pt(10)
    
    run_emp = p_ass.add_run("Grahl Consultoria e Treinamentos")
    run_emp.font.name = 'Abadi'
    run_emp.font.size = Pt(9)
    run_emp.font.color.rgb = RGBColor(100, 100, 100)

def formatar_tabela_profissional(tabela, com_cabecalho=True):
    tabela.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabela.style = 'Table Grid'
    
    cor_cabecalho = "1F4E78"
    
    inicio_dados = 1
    if com_cabecalho:
        for cell in tabela.rows[0].cells:
            shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{cor_cabecalho}"/>')
            cell._tc.get_or_add_tcPr().append(shading)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
                paragraph.paragraph_format.line_spacing = 1.15
                paragraph.paragraph_format.space_after = Pt(2)
                for run in paragraph.runs:
                    run.font.name = 'Abadi'
                    run.font.size = Pt(8.5)
                    run.font.bold = True
                    run.font.color.rgb = RGBColor(255, 255, 255)
    else:
        inicio_dados = 0

    for r_idx, row in enumerate(tabela.rows[inicio_dados:], start=inicio_dados):
        fundo_linha = "F8F9FA" if r_idx % 2 == 1 else "FFFFFF"
        for cell in row.cells:
            if fundo_linha != "FFFFFF":
                shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fundo_linha}"/>')
                cell._tc.get_or_add_tcPr().append(shading)
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                paragraph.paragraph_format.line_spacing = 1.25
                paragraph.paragraph_format.space_after = Pt(2)
                for run in paragraph.runs:
                    run.font.name = 'Abadi'
                    run.font.size = Pt(8.5)
                    run.font.color.rgb = RGBColor(51, 51, 51)

def limpar_valor(val):
    if pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']:
        return "Não informado"
    return str(val).strip()

# GERENCIAMENTO DE TELA ÚNICA VIA ESTADO (SESSION STATE)
if "menu_ativo" not in st.session_state:
    st.session_state["menu_ativo"] = "home"

def voltar_ao_menu():
    st.session_state["menu_ativo"] = "home"

# MENU PRINCIPAL COM CARTÕES COMPACTOS, ALTURA FIXA E ALINHAMENTO PERFEITO
if st.session_state["menu_ativo"] == "home":
    st.markdown("<h2 style='text-align: center; color: #1F4E78;'>Painel Executivo de Controle de Processos</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #555; margin-bottom: 25px;'>Selecione o módulo operacional desejado abaixo:</p>", unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3 = st.columns(3)
    
    with col_c1:
        st.markdown("""
        <div style="background-color: #f8f9fa; border: 2px solid #1F4E78; border-radius: 10px; padding: 18px; text-align: center; height: 175px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 3px 5px rgba(0,0,0,0.04); margin-bottom: 10px;">
            <div>
                <div style="font-size: 32px; margin-bottom: 6px;">⚙️</div>
                <h3 style="color: #1F4E78; margin: 0 0 6px 0; font-size: 16px;">Produção & Máquinas</h3>
                <p style="font-size: 12px; color: #666; margin: 0; line-height: 1.3;">Painel CLP, massas ideais, tempos, pressões e validação NBR 8082.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Acessar Produção", use_container_width=True):
            st.session_state["menu_ativo"] = "producao"
            st.rerun()
            
    with col_c2:
        st.markdown("""
        <div style="background-color: #f8f9fa; border: 2px solid #1F4E78; border-radius: 10px; padding: 18px; text-align: center; height: 175px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 3px 5px rgba(0,0,0,0.04); margin-bottom: 10px;">
            <div>
                <div style="font-size: 32px; margin-bottom: 6px;">⚖️</div>
                <h3 style="color: #1F4E78; margin: 0 0 6px 0; font-size: 16px;">Controle de Pesagem</h3>
                <p style="font-size: 12px; color: #666; margin: 0; line-height: 1.3;">Registro de massas em campo, desvios e emissão de laudo Word.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Acessar Pesagem", use_container_width=True):
            st.session_state["menu_ativo"] = "pesagem"
            st.rerun()
            
    with col_c3:
        st.markdown("""
        <div style="background-color: #f8f9fa; border: 2px solid #1F4E78; border-radius: 10px; padding: 18px; text-align: center; height: 175px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 3px 5px rgba(0,0,0,0.04); margin-bottom: 10px;">
            <div>
                <div style="font-size: 32px; margin-bottom: 6px;">🧪</div>
                <h3 style="color: #1F4E78; margin: 0 0 6px 0; font-size: 16px;">Controle de Reatividade</h3>
                <p style="font-size: 12px; color: #666; margin: 0; line-height: 1.3;">Ensaios DOC 0001/15, tempos de creme/gel e laudos executivos.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Acessar Reatividade", use_container_width=True):
            st.session_state["menu_ativo"] = "reatividade"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    col_c4, col_c5 = st.columns(2)
    
    with col_c4:
        st.markdown("""
        <div style="background-color: #f8f9fa; border: 2px solid #1F4E78; border-radius: 10px; padding: 18px; text-align: center; height: 175px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 3px 5px rgba(0,0,0,0.04); margin-bottom: 10px;">
            <div>
                <div style="font-size: 32px; margin-bottom: 6px;">📑</div>
                <h3 style="color: #1F4E78; margin: 0 0 6px 0; font-size: 16px;">Inspeções Semanais</h3>
                <p style="font-size: 12px; color: #666; margin: 0; line-height: 1.3;">Auditorias técnicas, pilares operacionais e banco de dados de laudos.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Acessar Inspeções", use_container_width=True):
            st.session_state["menu_ativo"] = "inspecoes"
            st.rerun()
            
    with col_c5:
        st.markdown("""
        <div style="background-color: #f8f9fa; border: 2px solid #1F4E78; border-radius: 10px; padding: 18px; text-align: center; height: 175px; display: flex; flex-direction: column; justify-content: space-between; box-shadow: 0 3px 5px rgba(0,0,0,0.04); margin-bottom: 10px;">
            <div>
                <div style="font-size: 32px; margin-bottom: 6px;">⚠️</div>
                <h3 style="color: #1F4E78; margin: 0 0 6px 0; font-size: 16px;">Registro de Anomalias</h3>
                <p style="font-size: 12px; color: #666; margin: 0; line-height: 1.3;">Abertura de ocorrências, disparos de e-mail e Matriz 5W1H.</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Acessar Anomalias", use_container_width=True):
            st.session_state["menu_ativo"] = "anomalias"
            st.rerun()

# CONTEÚDO DOS MÓDULOS INDIVIDUAIS COM BOTÃO DE RETORNO AO MENU
else:
    if st.button("⬅️ Voltar ao Painel Principal", type="primary"):
        voltar_ao_menu()
        st.rerun()
    st.markdown("---")

    if st.session_state["menu_ativo"] == "producao":
        st.subheader("⚙️ Painel de Produção & Máquinas")
        col_l1_c1, col_l1_c2 = st.columns(2)
        with col_l1_c1:
            maq_opcoes = ["Todas"] + df_base['Maquina_Filtro'].unique().tolist()
            filtro_maq = st.selectbox("Injetora:", maq_opcoes, key="filtro_injetora_pesquisa")
            
        df_f = df_base.copy()
        if filtro_maq != "Todas":
            df_f = df_f[df_f['Maquina_Filtro'] == filtro_maq]
            
        with col_l1_c2:
            exp_opcoes = ["Todos"] + df_f['Expositor_Filtro'].unique().tolist()
            filtro_exp = st.selectbox("Expositor:", exp_opcoes, key="filtro_expositor_pesquisa")
            
        if filtro_exp != "Todos":
            df_f = df_f[df_f['Expositor_Filtro'] == filtro_exp]

        col_l2_c1, col_l2_c2 = st.columns(2)
        with col_l2_c1:
            comp_opcoes = ["Todos"] + df_f['Componente_Filtro'].unique().tolist()
            filtro_comp = st.selectbox("Componente:", comp_opcoes, key="filtro_componente_pesquisa")
            
        if filtro_comp != "Todos":
            df_f = df_f[df_f['Componente_Filtro'] == filtro_comp]
            
        with col_l2_c2:
            item_desc_opcoes = ["Todos"] + df_f['Item_Descricao_Completo'].unique().tolist()
            filtro_item_desc = st.selectbox("Item / Descrição:", item_desc_opcoes, key="filtro_item_pesquisa")
            
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

    elif st.session_state["menu_ativo"] == "pesagem":
        st.subheader("⚖️ Controle de Pesagem em Campo")
        with st.form("form_pesagem"):
            f_data = st.date_input("Data da Inspeção", datetime.now(), key="pesagem_data_input")
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
            st.markdown("---")
            st.markdown("### 📊 Histórico de Pesagens")
            df_pesagem_hist = pd.read_excel("Log_Controle_Pesagem_Campo.xlsx")
            st.dataframe(df_pesagem_hist)
            
            if DOCX_DISPONIVEL:
                doc_pesagem = Document()
                aplicar_estilo_abadi_e_espacamento(doc_pesagem)
                
                p_h = doc_pesagem.add_paragraph()
                p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_h = p_h.add_run("GRAHL CONSULTORIA E TREINAMENTOS\n")
                run_h.bold = True
                run_h.font.size = Pt(14)
                run_h.font.color.rgb = RGBColor(31, 78, 120)
                run_sub = p_h.add_run("Relatório Executivo de Controle de Pesagem em Campo")
                run_sub.font.size = Pt(11)
                
                doc_pesagem.add_paragraph()
                
                t_p = doc_pesagem.add_table(rows=len(df_pesagem_hist) + 1, cols=len(df_pesagem_hist.columns))
                for i, col_name in enumerate(df_pesagem_hist.columns):
                    t_p.cell(0, i).text = str(col_name)
                for r_idx, row in df_pesagem_hist.iterrows():
                    for c_idx, val in enumerate(row):
                        t_p.cell(r_idx + 1, c_idx).text = limpar_valor(val)
                        
                formatar_tabela_profissional(t_p, com_cabecalho=True)
                adicionar_assinatura_padrao(doc_pesagem)
                
                bio_p = io.BytesIO()
                doc_pesagem.save(bio_p)
                bio_p.seek(0)
                st.download_button(
                    label="📥 Baixar Laudo de Pesagem em Word (.docx)",
                    data=bio_p.getvalue(),
                    file_name="Relatorio_Pesagem_Campo.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="btn_down_pesagem"
                )

    elif st.session_state["menu_ativo"] == "reatividade":
        st.subheader("🧪 Controle de Reatividade de Copo (DOC 0001/15)")
        with st.form("form_reatividade"):
            r_data = st.date_input("Data do Ensaio", datetime.now(), key="r_data")
            r_hora = st.text_input("Hora do Ensaio", "08:30")
            r_cabecote = st.selectbox("Cabeçote de Injeção", [1, 2], key="reat_cabecote_select")
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
            st.markdown("---")
            st.markdown("### 📊 Histórico de Reatividade")
            df_reat_hist = pd.read_excel("Log_Controle_Reatividade_DOC0001.xlsx")
            st.dataframe(df_reat_hist)
            
            if DOCX_DISPONIVEL:
                doc_reat = Document()
                aplicar_estilo_abadi_e_espacamento(doc_reat)
                
                p_h = doc_reat.add_paragraph()
                p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_h = p_h.add_run("GRAHL CONSULTORIA E TREINAMENTOS\n")
                run_h.bold = True
                run_h.font.size = Pt(14)
                run_h.font.color.rgb = RGBColor(31, 78, 120)
                run_sub = p_h.add_run("Laudo Executivo e Histórico de Reatividade de Copo (DOC 0001/15)")
                run_sub.font.size = Pt(11)
                
                doc_reat.add_paragraph()
                
                t_r = doc_reat.add_table(rows=len(df_reat_hist) + 1, cols=len(df_reat_hist.columns))
                
                larguras_reat = [Inches(0.8), Inches(0.6), Inches(0.7), Inches(0.8), Inches(0.8), Inches(0.9), Inches(0.8), Inches(0.8), Inches(0.7), Inches(1.2)]
                for i, col_name in enumerate(df_reat_hist.columns):
                    cell = t_r.cell(0, i)
                    cell.text = str(col_name)
                    if i < len(larguras_reat):
                        cell.width = larguras_reat[i]
                        
                for r_idx, row in df_reat_hist.iterrows():
                    for c_idx, val in enumerate(row):
                        cell = t_r.cell(r_idx + 1, c_idx)
                        cell.text = limpar_valor(val)
                        if c_idx < len(larguras_reat):
                            cell.width = larguras_reat[c_idx]
                        
                formatar_tabela_profissional(t_r, com_cabecalho=True)
                adicionar_assinatura_padrao(doc_reat)
                
                bio_r = io.BytesIO()
                doc_reat.save(bio_r)
                bio_r.seek(0)
                st.download_button(
                    label="📥 Baixar Laudo de Reatividade em Word (.docx)",
                    data=bio_r.getvalue(),
                    file_name="Relatorio_Reatividade_DOC0001.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="btn_down_reat"
                )

    elif st.session_state["menu_ativo"] == "inspecoes":
        st.subheader("📑 Gestão de Inspeções Semanais & Banco de Dados")
        st.markdown("Realize a inspeção técnica. Cada laudo gerado recebe um ID único e é armazenado no banco de dados.")
        
        st.markdown("### 1️⃣ Seleção da Injetora Alvo")
        insp_maquina = st.selectbox("Injetora / Cabeçote Alvo da Inspeção:", [
            "Krauss Maffei 40/40 (Cabeçote 1)", 
            "Krauss Maffei 80/80 (Cabeçote 2)"
        ], key="insp_maquina_select")
        
        with st.form("form_inspecao_semana"):
            st.markdown("### 2️⃣ Identificação da Auditoria")
            c_insp1, c_insp2 = st.columns(2)
            with c_insp1:
                fuso_br = timezone(timedelta(hours=-3))
                insp_data = st.date_input("Data da Inspeção", datetime.now(fuso_br).date(), key="insp_data_input")
                insp_responsavel = st.text_input("Responsável Técnico", "Rogério Grahl — CREA SC 1039223-9")
                
            with c_insp2:
                insp_semana = st.text_input("Semana de Referência / Período", "Semana 35 / 2026")

            st.markdown("---")
            st.markdown(f"### 3️⃣ Avaliação dos Pilares da Produção — {insp_maquina}")
            
            col_p1, col_p2 = st.columns(2)
            with col_p1:
                st.markdown("#### 🛠️ Manutenção & Equipamentos")
                insp_manut_status = st.selectbox("Status Manutenção do Cabeçote:", ["Conforme", "Parcialmente Conforme", "Não Conforme"], key="insp_manut_status_key")
                insp_manut_obs = st.text_area("Observações de Manutenção:", placeholder="Ex: Vazamentos, calibração de vazão, bicos...")
                
                st.markdown("#### ⚖️ Controle de Pesagem & Reatividade")
                insp_peso_status = st.selectbox("Status Desvios de Pesagem:", ["Dentro da tolerância (±50g)", "Desvio Moderado", "Desvio Crítico (>100g)"], key="insp_peso_status_key")
                insp_peso_obs = st.text_area("Observações de Pesagem:", placeholder="Ex: Análise das taras, médias de injeção...")

            with col_p2:
                st.markdown("#### 🔍 Qualidade de Espuma & Processo")
                insp_qual_status = st.selectbox("Status Conformidade Físico-Estrutural:", ["Aprovado (NBR 8082)", "Alerta de Deformação", "Reprovado"], key="insp_qual_status_key")
                insp_qual_obs = st.text_area("Observações de Qualidade:", placeholder="Ex: Células fechadas, retrabalhos, aderência...")
                
                st.markdown("#### 🦺 Segurança Operacional & Meio Ambiente")
                insp_seg_status = st.selectbox("Status EPIs, Ventilação e Ciclopentano (HC):", ["Conforme", "Advertência", "Paralisação Recomendada"], key="insp_seg_status_key")
                insp_seg_obs = st.text_area("Observações de Segurança:", placeholder="Ex: Exaustão ativa, detectores de gás, EPIs...")

            st.markdown("---")
            st.markdown("### 4️⃣ Anexo de Evidência Fotográfica & Conclusão")
            
            foto_enviada = st.file_uploader("📸 Enviar Foto do Local / Equipamento", type=["jpg", "jpeg", "png"], key="foto_insp_up")
            
            insp_fotos_desc = st.text_area("Registro Descritivo das Evidências Visuais:", placeholder="Descreva os pontos inspecionados visualmente...")
            insp_conclusao = st.text_area("Conclusão Executiva & Recomendações Técnicas:", placeholder="Diretrizes gerais para a gestão desta máquina...")

            btn_gerar_relatorio = st.form_submit_button("Salvar Inspeção e Gerar Laudo Técnico")

        if btn_gerar_relatorio:
            arq_db_insp = "Log_Inspecoes_Semanais.xlsx"
            try:
                df_db_insp = pd.read_excel(arq_db_insp)
                proximo_id_insp = f"INS-{len(df_db_insp) + 1:03d}"
            except:
                df_db_insp = pd.DataFrame()
                proximo_id_insp = "INS-001"

            novo_reg_insp = {
                "ID": proximo_id_insp,
                "Data": insp_data.strftime("%d/%m/%Y"),
                "Semana": insp_semana,
                "Máquina": insp_maquina,
                "Responsável": insp_responsavel,
                "Manutenção Status": insp_manut_status,
                "Manutenção Obs": limpar_valor(insp_manut_obs),
                "Pesagem Status": insp_peso_status,
                "Pesagem Obs": limpar_valor(insp_peso_obs),
                "Qualidade Status": insp_qual_status,
                "Qualidade Obs": limpar_valor(insp_qual_obs),
                "Segurança Status": insp_seg_status,
                "Segurança Obs": limpar_valor(insp_seg_obs),
                "Evidências Desc": limpar_valor(insp_fotos_desc),
                "Conclusão": limpar_valor(insp_conclusao)
            }

            df_db_insp = pd.concat([df_db_insp, pd.DataFrame([novo_reg_insp])], ignore_index=True)
            df_db_insp.to_excel(arq_db_insp, index=False)
            st.success(f"Inspeção **{proximo_id_insp}** salva com sucesso no banco de dados!")
            st.session_state["ultimo_insp_id"] = proximo_id_insp

        if os.path.exists("Log_Inspecoes_Semanais.xlsx"):
            st.markdown("---")
            st.markdown("### 🗄️ Banco de Dados & Histórico de Inspeções")
            df_insp_hist = pd.read_excel("Log_Inspecoes_Semanais.xlsx")
            st.dataframe(df_insp_hist[['ID', 'Data', 'Semana', 'Máquina', 'Responsável']], width='stretch')
            
            id_insp_escolhido = st.selectbox("Selecione o ID da Inspeção para gerar o Laudo Word:", df_insp_hist['ID'].tolist(), key="select_id_insp_banco")
            
            if id_insp_escolhido and DOCX_DISPONIVEL:
                reg_i = df_insp_hist[df_insp_hist['ID'] == id_insp_escolhido].iloc[0]
                
                doc_i = Document()
                aplicar_estilo_abadi_e_espacamento(doc_i)
                
                for section in doc_i.sections:
                    section.top_margin = Inches(1.18)
                    section.bottom_margin = Inches(0.78)
                    section.left_margin = Inches(1.18)
                    section.right_margin = Inches(0.78)
                        
                p_emp = doc_i.add_paragraph()
                p_emp.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_emp = p_emp.add_run("GRAHL CONSULTORIA E TREINAMENTOS\n")
                run_emp.bold = True
                run_emp.font.size = Pt(14)
                run_emp.font.color.rgb = RGBColor(31, 78, 120)
                
                run_sub = p_emp.add_run("Gestão de Injeção, Reologia e Qualidade em Poliuretano\n")
                run_sub.font.size = Pt(10)
                
                p_tit = doc_i.add_paragraph()
                p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_tit = p_tit.add_run(f"\nRELATÓRIO TÉCNICO DE INSPEÇÃO — {reg_i['ID']}\n")
                run_tit.bold = True
                run_tit.font.size = Pt(12)
                
                run_maq = p_tit.add_run(f"Máquina Alvo: {reg_i['Máquina']}")
                run_maq.bold = True
                run_maq.font.size = Pt(11)
                
                doc_i.add_paragraph()
                
                t_meta_i = doc_i.add_table(rows=2, cols=2)
                t_meta_i.cell(0, 0).text = f"Período: {limpar_valor(reg_i['Semana'])}"
                t_meta_i.cell(0, 1).text = f"Data da Emissão: {limpar_valor(reg_i['Data'])}"
                t_meta_i.cell(1, 0).text = f"Injetora: {limpar_valor(reg_i['Máquina'])}"
                t_meta_i.cell(1, 1).text = f"Responsável: {limpar_valor(reg_i['Responsável'])}"
                formatar_tabela_profissional(t_meta_i, com_cabecalho=False)
                
                doc_i.add_paragraph()
                
                h1 = doc_i.add_heading("1. Sumário Executivo", level=2)
                h1.runs[0].font.color.rgb = RGBColor(31, 78, 120)
                doc_i.add_paragraph(f"O presente relatório consolida a auditoria técnica semanal ({limpar_valor(reg_i['ID'])}) realizada na linha de injeção {limpar_valor(reg_i['Máquina'])}, contemplando verificação de reatividade, desvios de massa/pesagem, integridade mecânica e conformidade regulamentar sob diretrizes da Grahl Consultoria.")
                
                h2 = doc_i.add_heading("2. Parecer dos Pilares Operacionais", level=2)
                h2.runs[0].font.color.rgb = RGBColor(31, 78, 120)
                
                t_pilares_i = doc_i.add_table(rows=5, cols=3)
                hdr_c = t_pilares_i.rows[0].cells
                hdr_c[0].text = "Pilar de Avaliação"
                hdr_c[1].text = "Status"
                hdr_c[2].text = "Apontamentos de Campo"
                            
                dados_tb_i = [
                    ("Manutenção", limpar_valor(reg_i['Manutenção Status']), limpar_valor(reg_i['Manutenção Obs'])),
                    ("Pesagem / Reatividade", limpar_valor(reg_i['Pesagem Status']), limpar_valor(reg_i['Pesagem Obs'])),
                    ("Qualidade Estrutural", limpar_valor(reg_i['Qualidade Status']), limpar_valor(reg_i['Qualidade Obs'])),
                    ("Segurança & HC", limpar_valor(reg_i['Segurança Status']), limpar_valor(reg_i['Segurança Obs']))
                ]
                
                for idx, (pilar, st_v, obs_v) in enumerate(dados_tb_i):
                    r_c = t_pilares_i.rows[idx + 1].cells
                    r_c[0].text = pilar
                    r_c[1].text = st_v
                    r_c[2].text = obs_v
                    
                formatar_tabela_profissional(t_pilares_i, com_cabecalho=True)
                doc_i.add_paragraph()
                
                h3 = doc_i.add_heading("3. Evidências Fotográficas e Descritivas", level=2)
                h3.runs[0].font.color.rgb = RGBColor(31, 78, 120)
                doc_i.add_paragraph(f"Descrição das Evidências: {limpar_valor(reg_i['Evidências Desc'])}")
                
                h4 = doc_i.add_heading("4. Conclusão e Recomendações Técnicas", level=2)
                h4.runs[0].font.color.rgb = RGBColor(31, 78, 120)
                doc_i.add_paragraph(limpar_valor(reg_i['Conclusão']))
                
                adicionar_assinatura_padrao(doc_i, responsavel=limpar_valor(reg_i['Responsável']))
                
                bio_i = io.BytesIO()
                doc_i.save(bio_i)
                bio_i.seek(0)
                
                st.download_button(
                    label=f"📥 Baixar Laudo da Inspeção {reg_i['ID']} em Word (.docx)",
                    data=bio_i.getvalue(),
                    file_name=f"Laudo_Inspecao_{reg_i['ID']}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key=f"btn_dl_insp_{reg_i['ID']}"
                )

    elif st.session_state["menu_ativo"] == "anomalias":
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
                a_maquina = st.selectbox("Injetora / Máquina Afetada", df_base['Maquina_Filtro'].unique().tolist(), key="anom_maquina_select")
            with col_a2:
                resp_selecionado = st.selectbox("Direcionar para o Responsável:", list(agenda_emails.keys()), key="anom_resp_select")
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

            status_tratativa = st.selectbox("Status da Tratativa:", ["Pendente Ação Corretiva", "Em Andamento (5W1H)", "Concluído & Validado"], key="anom_status_select")
            
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
            st.markdown("### 📊 Histórico Geral de Ocorrências & Pendências (5W1H)")
            df_hist = pd.read_excel("Log_Registro_Anomalias.xlsx")
            
            if 'ID' not in df_hist.columns:
                df_hist.insert(0, 'ID', [f"OC-{i+1:03d}" for i in range(len(df_hist))])
                df_hist.to_excel("Log_Registro_Anomalias.xlsx", index=False)
                
            colunas_resumo = ['ID', 'Data', 'Hora', 'Máquina', 'Responsável', 'Status']
            st.dataframe(df_hist[colunas_resumo], width='stretch')
            
            if DOCX_DISPONIVEL:
                doc_anom = Document()
                aplicar_estilo_abadi_e_espacamento(doc_anom)
                
                p_h = doc_anom.add_paragraph()
                p_h.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run_h = p_h.add_run("GRAHL CONSULTORIA E TREINAMENTOS\n")
                run_h.bold = True
                run_h.font.size = Pt(14)
                run_h.font.color.rgb = RGBColor(31, 78, 120)
                run_sub = p_h.add_run("Relatório Executivo Consolidado de Ocorrências e Matriz 5W1H")
                run_sub.font.size = Pt(11)
                
                doc_anom.add_paragraph()
                
                t_anom = doc_anom.add_table(rows=len(df_hist) + 1, cols=len(colunas_resumo))
                for i, c_name in enumerate(colunas_resumo):
                    t_anom.cell(0, i).text = str(c_name)
                for r_idx, row in df_hist[colunas_resumo].iterrows():
                    for c_idx, val in enumerate(row):
                        t_anom.cell(r_idx + 1, c_idx).text = limpar_valor(val)
                        
                formatar_tabela_profissional(t_anom, com_cabecalho=True)
                adicionar_assinatura_padrao(doc_anom)
                
                bio_a = io.BytesIO()
                doc_anom.save(bio_a)
                bio_a.seek(0)
                st.download_button(
                    label="📥 Baixar Relatório Consolidado de Anomalias em Word (.docx)",
                    data=bio_a.getvalue(),
                    file_name="Relatorio_Consolidado_Anomalias.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    key="btn_down_anom_geral"
                )
                
            st.markdown("#### 🔍 Detalhes da Ocorrência & Laudo Individual")
            lista_ids = df_hist['ID'].tolist()
            id_selecionado = st.selectbox("Selecione o ID da Pendência para ver a descrição completa e baixar o laudo individual:", lista_ids, key="id_pendencia_select")
            
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

                if DOCX_DISPONIVEL:
                    doc_ind = Document()
                    aplicar_estilo_abadi_e_espacamento(doc_ind)
                    
                    for section in doc_ind.sections:
                        section.top_margin = Inches(1.18)
                        section.bottom_margin = Inches(0.78)
                        section.left_margin = Inches(1.18)
                        section.right_margin = Inches(0.78)
                    
                    p_ei = doc_ind.add_paragraph()
                    p_ei.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r_ei = p_ei.add_run("GRAHL CONSULTORIA E TREINAMENTOS\n")
                    r_ei.bold = True
                    r_ei.font.size = Pt(14)
                    r_ei.font.color.rgb = RGBColor(31, 78, 120)
                    
                    r_subi = p_ei.add_run("Gestão de Injeção, Reologia e Qualidade em Poliuretano\n")
                    r_subi.font.size = Pt(10)
                    
                    p_ti = doc_ind.add_paragraph()
                    p_ti.alignment = WD_ALIGN_PARAGRAPH.CENTER
                    r_ti = p_ti.add_run(f"\nRELATÓRIO TÉCNICO DE NÃO CONFORMIDADE — {limpar_valor(registro_detalhe['ID'])}\n")
                    r_ti.bold = True
                    r_ti.font.size = Pt(12)
                    
                    r_mqi = p_ti.add_run(f"Máquina Afetada: {limpar_valor(registro_detalhe['Máquina'])}")
                    r_mqi.bold = True
                    r_mqi.font.size = Pt(11)
                    
                    doc_ind.add_paragraph()
                    
                    t_meta_ind = doc_ind.add_table(rows=2, cols=2)
                    t_meta_ind.cell(0, 0).text = f"Data da Ocorrência: {limpar_valor(registro_detalhe['Data'])}"
                    t_meta_ind.cell(0, 1).text = f"Horário: {limpar_valor(registro_detalhe['Hora'])}"
                    t_meta_ind.cell(1, 0).text = f"Responsável Direcionado: {limpar_valor(registro_detalhe['Responsável'])}"
                    t_meta_ind.cell(1, 1).text = f"Status Atual: {limpar_valor(registro_detalhe['Status'])}"
                    formatar_tabela_profissional(t_meta_ind, com_cabecalho=False)
                    
                    doc_ind.add_paragraph()
                    
                    h_desc = doc_ind.add_heading("1. Descrição da Anomalia", level=2)
                    h_desc.runs[0].font.color.rgb = RGBColor(31, 78, 120)
                    doc_ind.add_paragraph(f"Problema Detectado / Ocorrência:\n{limpar_valor(registro_detalhe['Problema'])}")
                    
                    h_5w = doc_ind.add_heading("2. Plano de Ação Corretiva (Matriz 5W1H)", level=2)
                    h_5w.runs[0].font.color.rgb = RGBColor(31, 78, 120)
                    
                    t_5w_ind = doc_ind.add_table(rows=8, cols=2)
                    
                    t_5w_ind.cell(0, 0).text = "Parâmetro da Matriz 5W1H"
                    t_5w_ind.cell(0, 1).text = "Detalhamento da Ação / Diretriz"
                    
                    t_5w_ind.cell(1, 0).text = "1. What (Ação Corretiva)"
                    t_5w_ind.cell(1, 1).text = limpar_valor(registro_detalhe['What (Ação)'])
                    t_5w_ind.cell(2, 0).text = "2. Why (Justificativa)"
                    t_5w_ind.cell(2, 1).text = limpar_valor(registro_detalhe['Why (Por que)'])
                    t_5w_ind.cell(3, 0).text = "3. Where (Local)"
                    t_5w_ind.cell(3, 1).text = limpar_valor(registro_detalhe['Where (Onde)'])
                    t_5w_ind.cell(4, 0).text = "4. When (Prazo Limite)"
                    t_5w_ind.cell(4, 1).text = limpar_valor(registro_detalhe['When (Quando)'])
                    t_5w_ind.cell(5, 0).text = "5. Who (Responsável Execução)"
                    t_5w_ind.cell(5, 1).text = limpar_valor(registro_detalhe['Who (Quem)'])
                    t_5w_ind.cell(6, 0).text = "6. How (Método)"
                    t_5w_ind.cell(6, 1).text = limpar_valor(registro_detalhe['How (Como)'])
                    t_5w_ind.cell(7, 0).text = "Status da Tratativa"
                    t_5w_ind.cell(7, 1).text = limpar_valor(registro_detalhe['Status'])
                    
                    formatar_tabela_profissional(t_5w_ind, com_cabecalho=True)
                    adicionar_assinatura_padrao(doc_ind, responsavel=limpar_valor(registro_detalhe['Responsável']))
                    
                    bio_ind = io.BytesIO()
                    doc_ind.save(bio_ind)
                    bio_ind.seek(0)
                    
                    st.download_button(
                        label=f"📥 Baixar Laudo Individual da Ocorrência {registro_detalhe['ID']} (.docx)",
                        data=bio_ind.getvalue(),
                        file_name=f"Laudo_Ocorrencia_{registro_detalhe['ID']}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                        key=f"btn_dl_ind_{registro_detalhe['ID']}"
                    )

st.markdown("---")
st.caption("Grahl Consultoria e Treinamentos — Tecnologia aplicada ao chão de fábrica.")
