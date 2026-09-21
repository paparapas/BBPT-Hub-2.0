import streamlit as st
import pandas as pd
import json
import base64
import os

st.set_page_config(page_title="Histórico de Ligas", page_icon="logo.png", layout="wide")

# ==========================================
# 🔐 AUTENTICAÇÃO ESTÁTICA & PERSISTENTE (RBAC)
# ==========================================
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "is_judge" not in st.session_state: st.session_state.is_judge = False
if "auth_token" not in st.session_state: st.session_state.auth_token = None

admin_passwords = list(st.secrets.get("ADMINS", {}).values())
judge_passwords = list(st.secrets.get("JUDGES", {}).values())

admin_key_url = st.query_params.get("admin")
judge_key_url = st.query_params.get("judge")

if admin_key_url in admin_passwords:
    st.session_state.is_admin = True
    st.session_state.is_judge = False
    st.session_state.auth_token = admin_key_url
elif judge_key_url in judge_passwords:
    st.session_state.is_judge = True
    st.session_state.is_admin = False
    st.session_state.auth_token = judge_key_url

if st.session_state.is_admin and st.query_params.get("admin") != st.session_state.auth_token:
    st.query_params["admin"] = st.session_state.auth_token
elif st.session_state.is_judge and st.query_params.get("judge") != st.session_state.auth_token:
    st.query_params["judge"] = st.session_state.auth_token
elif not st.session_state.is_admin and not st.session_state.is_judge:
    st.session_state.auth_token = None

# ==========================================
# GESTÃO GLOBAL DA SIDEBAR
# ==========================================
logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"
if os.path.exists(logo_path):
    with st.sidebar:
        with open(logo_path, "rb") as image_file: encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

if st.session_state.is_admin:
    st.sidebar.success("🔓 ADMIN")
elif st.session_state.is_judge:
    st.sidebar.success("⚖️ JUIZ")
else:
    st.sidebar.info("👤 PLAYER")

# ==========================================
# DADOS HISTÓRICOS E FUNÇÕES DE RENDERIZAÇÃO
# ==========================================
@st.cache_data
def load_data():
    try:
        with open('bbpt_master_db.json', 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return None

def load_communications(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f: return f.read().strip()
    return None

db = load_data()

def render_advanced_metrics(metrics, league_mode=True):
    st.subheader("📈 League Advanced Metrics")
    st.markdown("### 👑 Kings of the League")
    for king in metrics.get('kings', []): st.write(king)
    st.markdown("### ⚔️ Upset of the Season")
    st.info(metrics.get('upset_season', 'N/A'))
    st.markdown("### 🛡️ The Gatekeeper")
    st.warning(metrics.get('gatekeeper', 'N/A'))
    st.markdown("### 📊 Meta-Health (Média de Pontos)")
    st.success(metrics.get('meta_health', 'N/A'))

def render_league_page(league_name, league_key, comm_file):
    nome_ficheiro = "fenix.png" if "versus" in league_name.lower() or "fenix" in league_key.lower() else "critical.png"
    img_path = nome_ficheiro if os.path.exists(nome_ficheiro) else f"../{nome_ficheiro}"
    
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file: encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(f"""<div style="display: flex; align-items: center; margin-bottom: 15px;"><img src="data:image/png;base64,{encoded_string}" width="70" style="margin-right: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.8rem;">{league_name}</h1></div>""", unsafe_allow_html=True)
    else: st.markdown(f"<h1 style='font-size: 2.8rem;'>🏆 {league_name}</h1>", unsafe_allow_html=True)
    
    comunicado = load_communications(comm_file)
    if comunicado: st.info(f"📢 **Quadro de Avisos:**\n\n{comunicado}")
    
    data = db.get(league_key)
    if not data or not data.get("standings_top8"):
        st.warning(f"Ainda não há dados disponíveis para a {league_name}.")
        return

    st.subheader("📊 Classificação Final")
    mostrar_totais = st.toggle("Mostrar Pontuação Total (Todas as Participações)")
    df_standings = pd.DataFrame(data['standings_total'] if mostrar_totais else data['standings_top8'])
    if not df_standings.empty: df_standings.set_index('Rank', inplace=True)
    st.dataframe(df_standings, use_container_width=True)

    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1: render_advanced_metrics(data['advanced_metrics'], league_mode=True)
    with col2:
        st.subheader("📋 Audit Log")
        df_audit = pd.DataFrame(data['audit_log'])
        if not df_audit.empty:
            df_audit.index += 1
            df_audit.index.name = "#"
        st.dataframe(df_audit, use_container_width=True)

# ==========================================
# INTERFACE DA PÁGINA
# ==========================================
st.title("🏛️ Arquivo BBPT")
st.markdown("Consulta aqui os resultados finais das temporadas passadas.")

if not db:
    st.error("⚠️ Base de dados histórica não encontrada.")
    st.stop()

# Navegação interna escalável via dropdown list
liga = st.selectbox("Escolhe a Temporada:", ["Liga Critical - Season I", "Liga Fénix Negra - Season I"])
st.divider()

if liga == "Liga Critical - Season I":
    render_league_page("Liga Critical X - Season I", "league_critical", "comunicacoesCritical.txt")
elif liga == "Liga Fénix Negra - Season I":
    render_league_page("Liga Fénix Negra - Season I", "league_versus", "comunicacoesVersus.txt")
