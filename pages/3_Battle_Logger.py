import streamlit as st
import pandas as pd
import os
import base64
from streamlit_cookies_controller import CookieController
from db_connection import supabase

st.set_page_config(page_title="Battle Logger", page_icon="⚔️", layout="wide")

# ==========================================
# GESTÃO BLINDADA DE LOGIN E COOKIES
# ==========================================
if "user_role" not in st.session_state: st.session_state.user_role = None

controller = CookieController()
c_role = controller.get('user_role')
if c_role: st.session_state.user_role = c_role

logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"
has_logo = os.path.exists(logo_path)

with st.sidebar:
    if has_logo:
        with open(logo_path, "rb") as image_file: encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-right:10px;'><h1 style='display:inline;font-size:1.8rem;'></h1></div>", unsafe_allow_html=True)
    else: st.title("🛡️ BBPT App")
    st.divider()
    
    if not st.session_state.user_role:
        with st.expander("🔐 Acesso Organização / Judges"):
            pwd = st.text_input("Password:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                if pwd.strip() == st.secrets["PASSWORDS"]["OWNER"]:
                    st.session_state.user_role = "owner"
                    controller.set('user_role', 'owner', max_age=43200)
                    st.rerun()
                elif pwd.strip() == st.secrets["PASSWORDS"]["ADMIN"]:
                    st.session_state.user_role = "admin"
                    controller.set('user_role', 'admin', max_age=43200)
                    st.rerun()
                elif pwd.strip() == st.secrets["PASSWORDS"]["JUDGE"]:
                    st.session_state.user_role = "judge"
                    controller.set('user_role', 'judge', max_age=43200)
                    st.rerun()
                else: st.error("Incorreta!")
    else:
        st.success(f"🔓 Modo {st.session_state.user_role.upper()} Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.user_role = None
            try: controller.remove('user_role')
            except: pass
            st.rerun()

if st.session_state.user_role not in ["admin", "owner", "judge"]:
    st.error("🛑 Acesso Restrito: Apenas a Organização e os Judges oficiais podem registar combates.")
    st.stop()

# ==========================================
# INTEGRAÇÃO SUPABASE COM CACHE AGRESSIVO ⚡
# ==========================================
@st.cache_data(ttl=600)
def get_active_tournaments():
    res = supabase.table("tournaments").select("*").eq("is_active", True).execute()
    return res.data

@st.cache_data(ttl=600)
def get_tournament_players(tournament_id):
    res = supabase.table("tournament_registrations").select("id, bladers(id, alias)").eq("tournament_id", tournament_id).execute()
    players = []
    for r in res.data:
        if r.get("bladers"):
            players.append({"reg_id": r["id"], "blader_id": r["bladers"]["id"], "alias": r["bladers"]["alias"]})
    return sorted(players, key=lambda x: x["alias"])

@st.cache_data(ttl=600)
def get_matches(tournament_id):
    res = supabase.table("matches").select("*, player1:p1_id(alias), player2:p2_id(alias)").eq("tournament_id", tournament_id).order("created_at", desc=True).execute()
    return res.data

# Funções de escrita (Limpam a cache para forçar dados novos)
def create_match(tournament_id, p1_id, p2_id, p1_name, p2_name):
    res = supabase.table("matches").insert({
        "tournament_id": tournament_id, "p1_id": p1_id, "p2_id": p2_id,
        "p1_score": 0, "p2_score": 0, "status": "ongoing"
    }).execute()
    get_matches.clear()
    return res.data[0]

def update_match_score(match_id, p1_score, p2_score, status="ongoing"):
    supabase.table("matches").update({"p1_score": p1_score, "p2_score": p2_score, "status": status}).eq("id", match_id).execute()
    get_matches.clear()

def log_round(match_id, p1_id, p2_id, winner_id, finish_type, points):
    supabase.table("match_rounds").insert({
        "match_id": match_id, "p1_id": p1_id, "p2_id": p2_id, 
        "winner_id": winner_id, "finish_type": finish_type, "points": points
    }).execute()

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
st.title("⚔️ Battle Logger Oficial")

active_tournaments = get_active_tournaments()
if not active_tournaments:
    st.warning("⚠️ Não há nenhum torneio ativo. Vai ao Painel de Organização iniciar um torneio.")
    st.stop()

if len(active_tournaments) > 1:
    t_names = [t["name"] for t in active_tournaments]
    selected_t = st.selectbox("Torneio:", t_names)
    active_tourney = next(t for t in active_tournaments if t["name"] == selected_t)
else:
    active_tourney = active_tournaments[0]

st.info(f"🏆 A registar batalhas para o evento: **{active_tourney['name']}**")

# Navegação interna
tabs = st.tabs(["🤺 Criar Combate", "⚔️ Batalha em Curso", "📊 Resultados"])

# ==========================================
# TAB 1: CRIAR NOVA BATALHA
# ==========================================
with tabs[0]:
    st.subheader("Configurar Novo Match")
    players = get_tournament_players(active_tourney["id"])
    
    if len(players) < 2:
        st.warning("É preciso pelo menos 2 jogadores registados para iniciar um combate.")
    else:
        player_names = [p["alias"] for p in players]
        col1, col2 = st.columns(2)
        p1_alias = col1.selectbox("Blader 1 (Canto Vermelho):", player_names)
        p2_alias = col2.selectbox("Blader 2 (Canto Azul):", [p for p in player_names if p != p1_alias])
        
        if st.button("Iniciar Batalha ⚡", type="primary", use_container_width=True):
            p1_data = next(p for p in players if p["alias"] == p1_alias)
            p2_data = next(p for p in players if p["alias"] == p2_alias)
            
            new_match = create_match(active_tourney["id"], p1_data["blader_id"], p2_data["blader_id"], p1_alias, p2_alias)
            
            # Guardamos na memória qual é o combate a decorrer agora neste telemóvel
            st.session_state.active_match = {
                "id": new_match["id"],
                "p1_id": p1_data["blader_id"], "p1_name": p1_alias, "p1_score": 0,
                "p2_id": p2_data["blader_id"], "p2_name": p2_alias, "p2_score": 0
            }
            st.success("Batalha iniciada! Muda para a aba 'Batalha em Curso'.")

# ==========================================
# TAB 2: FRAGMENTO DE BATALHA (MUITO RÁPIDO) ⚡
# ==========================================
with tabs[1]:
    if "active_match" not in st.session_state or st.session_state.active_match is None:
        st.info("Nenhuma batalha ativa no momento. Inicia um combate na aba anterior.")
    else:
        # ⚡ FRAGMENTO MÁGICO ⚡
        # Tudo o que está aqui dentro recarrega instantaneamente sem afetar o resto da página!
        @st.fragment
        def painel_de_combate():
            m = st.session_state.active_match
            
            st.markdown(f"<h2 style='text-align: center;'>{m['p1_name']} 🆚 {m['p2_name']}</h2>", unsafe_allow_html=True)
            
            # Placard Gigante
            c_score1, c_score2 = st.columns(2)
            c_score1.markdown(f"<div style='text-align:center; background-color:#ff4b4b; padding:20px; border-radius:10px; color:white;'><h1 style='font-size:60px; margin:0;'>{m['p1_score']}</h1><p style='margin:0;font-size:20px;'>{m['p1_name']}</p></div>", unsafe_allow_html=True)
            c_score2.markdown(f"<div style='text-align:center; background-color:#1f77b4; padding:20px; border-radius:10px; color:white;'><h1 style='font-size:60px; margin:0;'>{m['p2_score']}</h1><p style='margin:0;font-size:20px;'>{m['p2_name']}</p></div>", unsafe_allow_html=True)
            
            st.write("")
            
            # Lógica para adicionar pontos
            def add_score(player_num, points, finish_type):
                if player_num == 1:
                    m['p1_score'] += points
                    log_round(m['id'], m['p1_id'], m['p2_id'], m['p1_id'], finish_type, points)
                else:
                    m['p2_score'] += points
                    log_round(m['id'], m['p1_id'], m['p2_id'], m['p2_id'], finish_type, points)
                
                update_match_score(m['id'], m['p1_score'], m['p2_score'])
                
                # Se alguém chegou aos 4 pontos, a batalha termina (Requer Refresh total para sair do ecrã)
                if m['p1_score'] >= 4 or m['p2_score'] >= 4:
                    update_match_score(m['id'], m['p1_score'], m['p2_score'], status="completed")
                    st.session_state.active_match = None
                    st.rerun() # Limpa a sessão e sai do ecrã de combate

            # Botões de Ponto
            col_b1, col_b2 = st.columns(2)
            
            with col_b1:
                if st.button("🌪️ Spin Finish (1)", key="p1_s", use_container_width=True): add_score(1, 1, "Spin")
                if st.button("💥 Over Finish (2)", key="p1_o", use_container_width=True): add_score(1, 2, "Over")
                if st.button("💣 Burst Finish (2)", key="p1_b", use_container_width=True): add_score(1, 2, "Burst")
                if st.button("⚡ Xtreme Finish (3)", key="p1_x", use_container_width=True): add_score(1, 3, "Xtreme")
                
            with col_b2:
                if st.button("🌪️ Spin Finish (1)", key="p2_s", use_container_width=True): add_score(2, 1, "Spin")
                if st.button("💥 Over Finish (2)", key="p2_o", use_container_width=True): add_score(2, 2, "Over")
                if st.button("💣 Burst Finish (2)", key="p2_b", use_container_width=True): add_score(2, 2, "Burst")
                if st.button("⚡ Xtreme Finish (3)", key="p2_x", use_container_width=True): add_score(2, 3, "Xtreme")

            st.divider()
            
            # Opção de forçar o fim do combate (Desistência, penalização grave, etc)
            if st.button("🛑 Terminar Combate Forçadamente", type="secondary", use_container_width=True):
                update_match_score(m['id'], m['p1_score'], m['p2_score'], status="completed")
                st.session_state.active_match = None
                st.rerun() # Refresh total para sair

        # Chama a função fragmentada para renderizar o ecrã instantâneo
        painel_de_combate()

# ==========================================
# TAB 3: RESULTADOS E HISTÓRICO
# ==========================================
with tabs[2]:
    st.subheader("Últimos Combates Registados")
    matches = get_matches(active_tourney["id"])
    
    if not matches:
        st.info("Nenhuma batalha registada neste evento ainda.")
    else:
        for m in matches:
            if m['status'] == "completed":
                vencedor = m['player1']['alias'] if m['p1_score'] > m['p2_score'] else m['player2']['alias']
                cor = "green"
            else:
                vencedor = "Em Curso..."
                cor = "orange"
                
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{m['player1']['alias']}** vs **{m['player2']['alias']}**")
                c2.markdown(f"**{m['p1_score']}** - **{m['p2_score']}**")
                c3.markdown(f"<span style='color:{cor};'>{vencedor}</span>", unsafe_allow_html=True)
                
        if st.button("🔄 Atualizar Histórico", use_container_width=True):
            get_matches.clear()
            st.rerun()