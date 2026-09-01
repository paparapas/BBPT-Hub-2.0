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
# 🔐 AUTENTICAÇÃO ESTÁTICA & PERSISTENTE (RBAC)
# ==========================================
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "is_judge" not in st.session_state: st.session_state.is_judge = False
if "auth_token" not in st.session_state: st.session_state.auth_token = None

# Carrega as listas de passwords dos Secrets
admin_passwords = list(st.secrets.get("ADMINS", {}).values())
judge_passwords = list(st.secrets.get("JUDGES", {}).values())

admin_key_url = st.query_params.get("admin")
judge_key_url = st.query_params.get("judge")

# 1. Validar entrada via URL
if admin_key_url in admin_passwords:
    st.session_state.is_admin = True
    st.session_state.is_judge = False
    st.session_state.auth_token = admin_key_url
elif judge_key_url in judge_passwords:
    st.session_state.is_judge = True
    st.session_state.is_admin = False
    st.session_state.auth_token = judge_key_url

# 2. Gatekeeper: Re-injetar URL durante a navegação
if st.session_state.is_admin and st.query_params.get("admin") != st.session_state.auth_token:
    st.query_params["admin"] = st.session_state.auth_token
elif st.session_state.is_judge and st.query_params.get("judge") != st.session_state.auth_token:
    st.query_params["judge"] = st.session_state.auth_token
elif not st.session_state.is_admin and not st.session_state.is_judge:
    st.session_state.auth_token = None

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

    # O teu menu original de submódulos
    page = st.radio("Módulos do Hub Histórico:", [
        "Liga Critical", "Liga Fénix Negra", "Torneio de Equipas - Liga Versus", 
        "Rankings Globais", "Ad-Hoc: Blader Profile", "Contactos & Organização"
    ])
    
    st.divider()

    # Feedback de Autenticação na Sidebar
    if st.session_state.is_admin:
        st.success("🔓 Modo ADMIN Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.is_admin = False
            st.session_state.auth_token = None
            st.query_params.clear() 
            st.rerun()   
    elif st.session_state.is_judge:
        st.success("⚖️ Modo JUIZ Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.is_judge = False
            st.session_state.auth_token = None
            st.query_params.clear() 
            st.rerun() 
    else:
        st.info("👤 Modo Público (Player)")
        with st.expander("🔐 Acesso Staff"):
            pwd_input = st.text_input("Password de Acesso:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                if pwd_input.strip() in admin_passwords:
                    st.session_state.is_admin = True
                    st.session_state.is_judge = False
                    st.session_state.auth_token = pwd_input.strip()
                    st.query_params["admin"] = pwd_input.strip()
                    st.rerun()
                elif pwd_input.strip() in judge_passwords:
                    st.session_state.is_judge = True
                    st.session_state.is_admin = False
                    st.session_state.auth_token = pwd_input.strip()
                    st.query_params["judge"] = pwd_input.strip()
                    st.rerun()
                elif pwd_input.strip() == st.secrets.get("PASSWORDS", {}).get("OWNER"):
                    # Fallback temporário para password antiga (opcional)
                    st.session_state.is_admin = True
                    st.session_state.auth_token = pwd_input.strip()
                    st.query_params["admin"] = pwd_input.strip()
                    st.rerun()
                else: 
                    st.error("Password Incorreta!")

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
    
    # Função auxiliar para carregar as imagens e desenhar o botão HTML
    def render_social_button(link, img_file, text):
        img_path = img_file if os.path.exists(img_file) else f"../{img_file}"
        img_tag = ""
        if os.path.exists(img_path):
            with open(img_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            img_tag = f"<img src='data:image/png;base64,{b64}' style='height: 22px; margin-right: 10px; object-fit: contain;'>"
            
        return f"""
        <a href="{link}" target="_blank" style="
            display: flex; align-items: center; justify-content: center;
            background-color: #1f2333; color: white; text-decoration: none;
            padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
            font-size: 16px; font-weight: 600; width: 100%; box-sizing: border-box;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        ">
            {img_tag}{text}
        </a>
        """

    c1, c2, c3, c4 = st.columns(4) 
    with c1: st.markdown(render_social_button("https://www.instagram.com/beyblade_pt", "instagram.png", "Instagram"), unsafe_allow_html=True)
    with c2: st.markdown(render_social_button("https://chat.whatsapp.com/GCLf0RjTFjFHzc1yK2VjPo", "whatsapp.png", "WhatsApp"), unsafe_allow_html=True)
    with c3: st.markdown(render_social_button("https://www.youtube.com/@BeybladePortugal", "youtube.png", "YouTube"), unsafe_allow_html=True)
    with c4: st.markdown(render_social_button("https://discord.com/invite/KssWPXxFnq", "discord.png", "Discord"), unsafe_allow_html=True)
    
    st.divider()
    
    st.subheader("👥 Quadro da Organização e Gestão")
    conteudo_org = load_communications("organizacao.txt")
    if conteudo_org:
        for seccao in conteudo_org.split("==="):
            if seccao.strip():
                with st.container(border=True): st.markdown(seccao.strip())
