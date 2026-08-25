import streamlit as st
import pandas as pd
import json
import base64
import os
import re
from db_connection import supabase

# 1. Configuração da Página
st.set_page_config(page_title="BBPT Hub", page_icon="logo.png", layout="wide")

# ==========================================
# 🔐 AUTENTICAÇÃO ESTÁTICA & PERSISTENTE
# ==========================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

secret_admin_pass = st.secrets.get("PASSWORDS", {}).get("ADMIN", "bbpt-paparapas")

# 1. Valida entrada inicial
if st.query_params.get("admin") == secret_admin_pass:
    st.session_state.is_admin = True

# 2. Garante que a navegação nativa não limpa a password do URL
if st.session_state.is_admin and st.query_params.get("admin") != secret_admin_pass:
    st.query_params["admin"] = secret_admin_pass

# ==========================================
# GESTÃO GLOBAL E SIDEBAR
# ==========================================
logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"
has_logo = os.path.exists(logo_path)

with st.sidebar:
    if has_logo:
        with open(logo_path, "rb") as image_file: 
            encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-right:10px;'></h1></div>", unsafe_allow_html=True)
    else: 
        st.title("🛡️Hub")
    st.divider()

    # O teu menu original de submódulos continua intacto
    page = st.radio("Módulos do Hub Histórico:", [
        "Liga Critical", "Liga Fénix Negra", "Torneio de Equipas - Liga Versus", 
        "Rankings Globais", "Ad-Hoc: Blader Profile", "Contactos & Organização"
    ])
    
    st.divider()

    if not st.session_state.is_admin:
        with st.expander("🔐 Acesso Organização / Judges"):
            pwd_input = st.text_input("Password:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                if pwd_input.strip() == secret_admin_pass:
                    st.session_state.is_admin = True
                    st.query_params["admin"] = secret_admin_pass
                    st.rerun()
                elif pwd_input.strip() == st.secrets.get("PASSWORDS", {}).get("OWNER"):
                    # Aceitamos owner como admin para não quebrar hábitos antigos
                    st.session_state.is_admin = True
                    st.query_params["admin"] = secret_admin_pass
                    st.rerun()
                else: 
                    st.error("Password Incorreta!")
    else:
        st.success("🔓 Modo ADMIN Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.is_admin = False
            st.query_params.clear() 
            st.rerun()   

# ==========================================
# 2. CARREGAR DADOS HISTÓRICOS (HÍBRIDO)
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

if not db:
    st.error("⚠️ Base de dados histórica não encontrada.")
    st.stop()

# ==========================================
# FUNÇÕES REUTILIZÁVEIS DE RENDERIZAÇÃO
# ==========================================
def render_advanced_metrics(metrics, league_mode=True):
    title_suffix = "League" if league_mode else "Global Rankings"
    st.subheader(f"📈 {title_suffix} Advanced Metrics")
    st.markdown(f"### 👑 Kings of the {title_suffix}")
    for king in metrics.get('kings', []): st.write(king)
    st.markdown(f"### ⚔️ Upset of the {title_suffix}")
    st.info(metrics.get('upset_season', 'N/A'))
    st.markdown("### 🛡️ The Gatekeeper")
    st.warning(metrics.get('gatekeeper', 'N/A'))
    st.markdown("### 📊 Meta-Health (Média de Pontos Combinados)")
    st.success(metrics.get('meta_health', 'N/A'))
    st.markdown("*(Jogos normais até 4 pts | Top Cut até 5 pts | Finais até 7 pts)*\n* **Alta (> 6.5 Pts):** Meta de Ataque\n* **Média (5.0 - 6.5 Pts):** Meta Equilibrada\n* **Baixa (< 5.0 Pts):** Meta de Defesa")

def render_league_page(league_name, league_key, comm_file):
    nome_ficheiro = "fenix.png" if "versus" in league_name.lower() or "versus" in league_key.lower() else "critical.png"
    img_path = nome_ficheiro if os.path.exists(nome_ficheiro) else f"../{nome_ficheiro}"
    
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file: encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(f"""<div style="display: flex; align-items: center; margin-bottom: 15px;"><img src="data:image/png;base64,{encoded_string}" width="70" style="margin-right: 15px;"><h1 style="margin: 0; padding: 0; font-size: 3.5rem;">{league_name}</h1></div>""", unsafe_allow_html=True)
    else: st.markdown(f"<h1 style='font-size: 3.5rem;'>🏆 {league_name}</h1>", unsafe_allow_html=True)
    
    comunicado = load_communications(comm_file)
    if comunicado: st.info(f"📢 **Quadro de Avisos:**\n\n{comunicado}")
    
    data = db.get(league_key)
    if not data or not data.get("standings_top8"):
        st.warning(f"Ainda não há dados disponíveis para a {league_name}.")
        return

    st.subheader("📊 League Standings")
    mostrar_totais = st.toggle("Mostrar Todas as Participações")
    df_standings = pd.DataFrame(data['standings_total'] if mostrar_totais else data['standings_top8'])
    if not df_standings.empty: df_standings.set_index('Rank', inplace=True)
    st.dataframe(df_standings, use_container_width=True)

    st.divider()
    col1, col2 = st.columns([1, 1])
    with col1: render_advanced_metrics(data['advanced_metrics'], league_mode=True)
    with col2:
        st.subheader("📋 Tournament Audit Log")
        df_audit = pd.DataFrame(data['audit_log'])
        if not df_audit.empty:
            df_audit.index += 1
            df_audit.index.name = "#"
        st.dataframe(df_audit, use_container_width=True)

# ==========================================
# RENDERIZAÇÃO DOS MÓDULOS
# ==========================================
if page == "Liga Critical": render_league_page("Liga Critical X", "league_critical", "comunicacoesCritical.txt")
elif page == "Liga Fénix Negra": render_league_page("Liga Fénix Negra", "league_versus", "comunicacoesVersus.txt")
elif page == "Torneio de Equipas - Liga Versus":
    st.title("🤝 Torneio de Equipas - Fénix Negra")
    comunicado = load_communications("comunicacoesEquipasVersus.txt")
    if comunicado: st.info(f"📢 **Quadro de Avisos:**\n\n{comunicado}")
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Standings Finais")
        try: st.image("foto_equipas.jpg", use_container_width=True)
        except Exception: st.warning("⚠️ Imagem não encontrada.")
    with col2:
        st.subheader("📺 VOD do Torneio")
        st.video("https://youtu.be/vsbuwPL5uzs?si=egyuV9P3j8Gdfc6z", start_time=1319)

elif page == "Rankings Globais":
    st.title("🌐 BBPT Global Power Rankings")
    comunicado = load_communications("comunicacoesGlobal.txt")
    if comunicado: st.info(f"📢 **Quadro de Avisos Global:**\n\n{comunicado}")
    df_rankings = pd.DataFrame(db['global_versus']['rankings'])
    if not df_rankings.empty: df_rankings.set_index('Rank', inplace=True)
    st.dataframe(df_rankings, use_container_width=True)
    st.divider()
    render_advanced_metrics(db['global_versus'].get('advanced_metrics', {}), league_mode=False)

elif page == "Ad-Hoc: Blader Profile":
    st.title("👤 Blader Intelligence Profile")
    player_list = sorted(list(db['global_versus']['profiles'].keys()))
    selected_player = st.selectbox("Selecione o Blader:", player_list)
    if selected_player:
        p_data = db['global_versus']['profiles'][selected_player]
        win_rate = p_data.get('win_rate', 0)
        total_matches = int(p_data.get('total_matches', 0))
        total_wins = sum(int(m.get('Wins', 0)) for m in p_data.get('matchups', []))
        st.markdown(f"## *{selected_player}*")
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.metric("Overall Win Rate", f"{win_rate}%")
        c2.metric("Total Wins", total_wins)
        c3.metric("Total Matches", total_matches)
        st.divider()
        st.subheader("🎯 Player Matchups")
        df_matchups = pd.DataFrame(p_data.get('matchups', []))
        if not df_matchups.empty:
            df_matchups['Win Rate %'] = (df_matchups['Wins'] / df_matchups['Games']) * 100
            st.dataframe(df_matchups[['Opponent', 'Games', 'Wins', 'Win Rate %']], use_container_width=True)

elif page == "Contactos & Organização":
    st.title("📞 Contactos & Organização")
    st.subheader("🌐 Comunidade e Redes Sociais")
    c1, c2, c3, c4 = st.columns(4) 
    c1.link_button("📸 Instagram", "https://www.instagram.com/beyblade_pt", use_container_width=True)
    c2.link_button("💬 Whatsapp", "https://chat.whatsapp.com/GCLf0RjTFjFHzc1yK2VjPo", use_container_width=True)
    c3.link_button("📺 YouTube", "https://www.youtube.com/@BeybladePortugal", use_container_width=True)
    c4.link_button("📺 Discord", "https://discord.com/invite/KssWPXxFnq", use_container_width=True)
    st.divider()
    conteudo_org = load_communications("organizacao.txt")
    if conteudo_org:
        for seccao in conteudo_org.split("==="):
            if seccao.strip():
                with st.container(border=True): st.markdown(seccao.strip())
