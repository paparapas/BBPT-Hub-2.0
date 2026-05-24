import streamlit as st
import pandas as pd
import json
import base64
import os
import re
from streamlit_cookies_controller import CookieController

# 1. Configuração da Página (Define o título do separador do browser)
st.set_page_config(page_title="BBPT Hub", page_icon="logo.png", layout="wide")

# ==========================================
# GESTÃO GLOBAL DE LOGIN E SIDEBAR
# ==========================================
controller = CookieController()
cookie_role = controller.get('user_role')

if cookie_role in ["owner", "admin", "judge"]:
    st.session_state.user_role = cookie_role
elif "user_role" not in st.session_state:
    st.session_state.user_role = None

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

    # O MENU DE SELECÇÃO DE LIGAS HISTÓRICAS
    page = st.radio("Módulos do Hub Histórico:", [
        "Liga Critical", 
        "Liga Fénix Negra", 
        "Torneio de Equipas - Liga Versus", 
        "Rankings Globais", 
        "Ad-Hoc: Blader Profile", 
        "Contactos & Organização"
    ])
    
    st.divider()

    # FORMULÁRIO DE LOGIN DE CONTA
    if not st.session_state.user_role:
        with st.expander("🔐 Acesso Organização / Judges"):
            pwd = st.text_input("Password:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                if pwd.strip() == st.secrets.get("PASSWORDS", {}).get("OWNER", "bbpt-owner123"):
                    st.session_state.user_role = "owner"
                    controller.set('user_role', 'owner', max_age=43200)
                    st.rerun()
                elif pwd.strip() == st.secrets.get("PASSWORDS", {}).get("ADMIN", "bbpt-paparapas"):
                    st.session_state.user_role = "admin"
                    controller.set('user_role', 'admin', max_age=43200)
                    st.rerun()
                elif pwd.strip() == st.secrets.get("PASSWORDS", {}).get("JUDGE", "bbpt-judge"):
                    st.session_state.user_role = "judge"
                    controller.set('user_role', 'judge', max_age=43200)
                    st.rerun()
                else: 
                    st.error("Incorreta!")
    else:
        st.success(f"🔓 Modo {st.session_state.user_role.upper()} Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.user_role = None
            if "finance_auth" in st.session_state: 
                st.session_state.finance_auth = False
            
            if controller.get('user_role') is not None: controller.remove('user_role')
            if controller.get('finance_auth') is not None: controller.remove('finance_auth')
            st.rerun()

# ==========================================
# 2. CARREGAR DADOS HISTÓRICOS (HÍBRIDO)
# ==========================================
@st.cache_data
def load_data():
    try:
        with open('bbpt_master_db.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def load_communications(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if content: return content
    return None

db = load_data()

if not db:
    st.error("⚠️ Base de dados histórica (bbpt_master_db.json) não encontrada. O Hub precisa deste ficheiro para desenhar as tabelas classificativas.")
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
    st.markdown("""
    *(Jogos normais até 4 pts | Top Cut até 5 pts | Finais até 7 pts)*
    * **Alta (> 6.5 Pts):** Meta de Ataque Agressivo (Jogos rápidos e explosivos decididos por X-Treme Finishes de 3 pts. Ex: 4-0, 5-1)
    * **Média (5.0 - 6.5 Pts):** Meta Equilibrada (Mistura saudável de Spin, Burst e Over Finishes)
    * **Baixa (< 5.0 Pts):** Meta de Defesa/Stamina (Jogos longos, muitas rondas decididas por Spin Finishes de 1 ponto. Ex: 4-3, 5-4)
    """)

def render_league_page(league_name, league_key, comm_file):
    if "versus" in league_name.lower() or "versus" in league_key.lower(): nome_ficheiro = "fenix.png"
    else: nome_ficheiro = "critical.png"
        
    img_path = nome_ficheiro if os.path.exists(nome_ficheiro) else f"../{nome_ficheiro}"
    
    if os.path.exists(img_path):
        with open(img_path, "rb") as image_file: encoded_string = base64.b64encode(image_file.read()).decode()
        st.markdown(f"""<div style="display: flex; align-items: center; margin-bottom: 15px;"><img src="data:image/png;base64,{encoded_string}" width="70" style="margin-right: 15px;"><h1 style="margin: 0; padding: 0; font-size: 3.5rem;">{league_name}</h1></div>""", unsafe_allow_html=True)
    else:
        st.markdown(f"<h1 style='font-size: 3.5rem;'>🏆 {league_name}</h1>", unsafe_allow_html=True)
    
    comunicado = load_communications(comm_file)
    if comunicado: st.info(f"📢 **Quadro de Avisos da Organização:**\n\n{comunicado}")
    
    data = db.get(league_key)
    
    if not data or not data.get("standings_top8"):
        st.warning(f"Ainda não há dados de partidas disponíveis para a {league_name}.")
        return

    st.subheader("📊 League Standings")
    mostrar_totais = st.toggle("Mostrar Todas as Participações (Pontuação Total)")
    
    if mostrar_totais:
        st.markdown("*Classificação absoluta somando o resultado de **todos** os torneios disputados.*")
        df_standings = pd.DataFrame(data['standings_total'])
    else:
        st.markdown("*Pontuação oficial da liga baseada apenas nos **8 melhores** resultados de cada Blader.*")
        df_standings = pd.DataFrame(data['standings_top8'])

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

if page == "Liga Critical":
    render_league_page("Liga Critical X", "league_critical", "comunicacoesCritical.txt")

elif page == "Liga Fénix Negra":
    render_league_page("Liga Fénix Negra", "league_versus", "comunicacoesVersus.txt")

elif page == "Torneio de Equipas - Liga Versus":
    st.title("🤝 Torneio de Equipas - Fénix Negra")
    comunicado = load_communications("comunicacoesEquipasVersus.txt")
    if comunicado: st.info(f"📢 **Quadro de Avisos:**\n\n{comunicado}")
    st.divider()
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📊 Standings Finais")
        st.markdown("Resultados oficiais do torneio de equipas.")
        try: st.image("foto_equipas.jpg", use_container_width=True)
        except Exception: st.warning("⚠️ Imagem 'foto_equipas.jpg' não encontrada.")
            
    with col2:
        st.subheader("📺 VOD do Torneio")
        st.markdown("Acompanha a ação a partir do momento chave!")
        st.video("https://youtu.be/vsbuwPL5uzs?si=egyuV9P3j8Gdfc6z", start_time=1319)

elif page == "Rankings Globais":
    st.title("🌐 BBPT Global Power Rankings")
    comunicado = load_communications("comunicacoesGlobal.txt")
    if comunicado: st.info(f"📢 **Quadro de Avisos Global:**\n\n{comunicado}")
        
    st.markdown("O sistema de Power Rating (ELO) baseado em todo o historial.")
    df_rankings = pd.DataFrame(db['global_versus']['rankings'])
    if not df_rankings.empty: df_rankings.set_index('Rank', inplace=True)
    st.dataframe(df_rankings, use_container_width=True)

    st.divider()
    render_advanced_metrics(db['global_versus'].get('advanced_metrics', {}), league_mode=False)

    st.divider()
    st.subheader("📋 Audit Log: Torneios Globais")
    st.markdown("Lista de todos os torneios que estão a alimentar o Power Rating Global e os Perfis.")
    
    global_audit = db['global_versus'].get('audit_log', [])
    if global_audit:
        df_global_audit = pd.DataFrame(global_audit)
        if not df_global_audit.empty:
            df_global_audit.index += 1
            df_global_audit.index.name = "#"
        st.dataframe(df_global_audit, use_container_width=True)
    else: st.warning("⚠️ O Log de Torneios ainda não foi exportado para a base de dados global.")

elif page == "Ad-Hoc: Blader Profile":
    st.title("👤 Blader Intelligence Profile")
    player_list = sorted(list(db['global_versus']['profiles'].keys()))
    selected_player = st.selectbox("Selecione o Blader para análise detalhada:", player_list)
    
    if selected_player:
        p_data = db['global_versus']['profiles'][selected_player]
        target_player_lower = str(selected_player).strip().lower()
        
        total_jogadores = len(db['global_versus']['profiles'])
        rank_atual = "N/A"
        for r in db['global_versus'].get('rankings', []):
            if str(r.get('Player', '')).strip().lower() == target_player_lower:
                rank_atual = r.get('Rank', 'N/A')
                break
                
        total_eventos_globais = max((int(prof.get('events_played', 0)) for prof in db['global_versus']['profiles'].values()), default=0)
        total_matches = int(p_data.get('total_matches', 0))
        events_played = int(p_data.get('events_played', 0))
        total_wins = sum(int(m.get('Wins', 0)) for m in p_data.get('matchups', []))
        total_losses = total_matches - total_wins
        win_rate = p_data.get('win_rate', 0)
        
        first_place, second_place, third_place, fourth_place, top_8_place = 0, 0, 0, 0, 0
        ai_prompt = p_data.get('ai_prompt', '')
        podios_match = re.search(r'Histórico de Pódios:\s*([^\n]+)', ai_prompt)
        
        if podios_match:
            record_str = podios_match.group(1).strip()
            if record_str and record_str != "Nenhum Top 8":
                for item in record_str.split(','):
                    item = item.strip().lower()
                    if not item: continue
                    match = re.match(r'^(\d+)\s*[xX]\s*(.+)$', item)
                    if match:
                        qtd = int(match.group(1)); pos = match.group(2).strip()
                        if pos == '1st': first_place += qtd
                        elif pos == '2nd': second_place += qtd
                        elif pos == '3rd': third_place += qtd
                        elif pos == '4th': fourth_place += qtd
                        elif pos in ['5th', '6th', '7th', '8th']: top_8_place += qtd
        
        tournaments_won = first_place
        made_top_cut = first_place + second_place + third_place + fourth_place + top_8_place
        missed_top_cut = max(0, events_played - made_top_cut)

        st.markdown(f"## *{selected_player} | Rank: {rank_atual} of {total_jogadores} players*")
        st.divider()

        st.markdown("#### Personal Match Record")
        c1, c2, c3 = st.columns(3)
        with c1:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; color: #a1e533; margin: 0;'>{win_rate}%</h2><p style='text-align: center; color: gray; margin: 0;'>Overall Win Rate</p>", unsafe_allow_html=True)
        with c2:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; color: #4CAF50; margin: 0;'>{total_wins}</h2><p style='text-align: center; color: gray; margin: 0;'>Total Wins</p>", unsafe_allow_html=True)
        with c3:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; color: #F44336; margin: 0;'>{total_losses}</h2><p style='text-align: center; color: gray; margin: 0;'>Total Losses</p>", unsafe_allow_html=True)

        c4, c5, _ = st.columns(3)
        with c4:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{total_matches}</h2><p style='text-align: center; color: gray; margin: 0;'>Total Matches</p>", unsafe_allow_html=True)
        with c5:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; color: #9C27B0; margin: 0;'>{p_data.get('elo_global', 'N/A')}</h2><p style='text-align: center; color: gray; margin: 0;'>Global ELO</p>", unsafe_allow_html=True)

        st.write("")
        st.markdown("#### Tournament Placements Record")
        t1, t2, t3 = st.columns(3)
        with t1:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{events_played} <span style='font-size: 0.5em; color: gray;'>/ {total_eventos_globais}</span></h2><p style='text-align: center; color: gray; margin: 0;'>Events Played</p>", unsafe_allow_html=True)
        with t2:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{tournaments_won}</h2><p style='text-align: center; color: gray; margin: 0;'>Tournaments Won</p>", unsafe_allow_html=True)
        with t3:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{first_place}x</h2><p style='text-align: center; color: #FFD700; margin: 0;'>🥇 1st Place</p>", unsafe_allow_html=True)

        t4, t5, t6 = st.columns(3)
        with t4:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{second_place}x</h2><p style='text-align: center; color: #C0C0C0; margin: 0;'>🥈 2nd Place</p>", unsafe_allow_html=True)
        with t5:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{third_place}x</h2><p style='text-align: center; color: #CD7F32; margin: 0;'>🥉 3rd Place</p>", unsafe_allow_html=True)
        with t6:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{fourth_place}x</h2><p style='text-align: center; color: gray; margin: 0;'>4th Place</p>", unsafe_allow_html=True)

        t7, t8, _ = st.columns(3)
        with t7:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; margin: 0;'>{top_8_place}x</h2><p style='text-align: center; color: gray; margin: 0;'>Top 8 (5th-8th)</p>", unsafe_allow_html=True)
        with t8:
            with st.container(border=True): st.markdown(f"<h2 style='text-align: center; color: #F44336; margin: 0;'>{missed_top_cut}x</h2><p style='text-align: center; color: gray; margin: 0;'>❌ Missed Top Cut</p>", unsafe_allow_html=True)

        st.divider()
        st.subheader("🤖 AI Coach Report")
        st.code(p_data.get('ai_prompt', 'N/A'), language='text')

        st.divider()
        st.subheader("🎯 Player Matchups (With True Elo Probability)")
        df_matchups = pd.DataFrame(p_data.get('matchups', []))
        if not df_matchups.empty:
            df_matchups['Losses'] = df_matchups['Games'] - df_matchups['Wins']
            df_matchups['Win Rate %'] = (df_matchups['Wins'] / df_matchups['Games']) * 100
            df_matchups = df_matchups[['Opponent', 'Games', 'Wins', 'Losses', 'Win Rate %', 'Win Likelihood (Elo)']]
            df_matchups.index += 1
            st.dataframe(df_matchups, use_container_width=True, column_config={"Win Rate %": st.column_config.ProgressColumn("Win Rate %", format="%.1f %%", min_value=0, max_value=100)})
        else: st.dataframe(df_matchups, use_container_width=True)

        st.divider()
        st.subheader("📖 Raw Match History")
        df_history = pd.DataFrame(p_data.get('raw_matches', []))
        if not df_history.empty: df_history.index += 1
        st.dataframe(df_history, use_container_width=True)

elif page == "Contactos & Organização":
    st.title("📞 Contactos & Organização")
    st.subheader("🌐 Comunidade e Redes Sociais")
    
    c1, c2, c3, c4 = st.columns(4) 
    with c1: st.link_button("📸 Instagram", "https://www.instagram.com/beyblade_pt", use_container_width=True)
    with c2: st.link_button("💬 Whatsapp", "https://chat.whatsapp.com/GCLf0RjTFjFHzc1yK2VjPo", use_container_width=True)
    with c3: st.link_button("📺 YouTube", "https://www.youtube.com/@BeybladePortugal", use_container_width=True)
    with c4: st.link_button("📺 Discord", "https://discord.com/invite/KssWPXxFnq", use_container_width=True)

    st.divider()
    st.subheader("👥 Quadro da Organização e Gestão")
    conteudo_org = load_communications("organizacao.txt")
    if conteudo_org:
        for seccao in conteudo_org.split("==="):
            if seccao.strip():
                with st.container(border=True): st.markdown(seccao.strip())