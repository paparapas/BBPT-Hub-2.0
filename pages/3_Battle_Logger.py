import streamlit as st
import pandas as pd
import json
import base64
import os
import time
from datetime import datetime
from streamlit_cookies_controller import CookieController
from db_connection import supabase

# 🛑 FORÇAR O MODO "WIDE" E REMOVER ESPAÇOS BRANCOS 🛑
st.set_page_config(page_title="Battle Logger", page_icon="logo.png", layout="wide", initial_sidebar_state="collapsed")

# --- PASSWORDS DE ACESSO ---
ADMIN_PASSWORD = "bbpt-paparapas" 
JUDGE_PASSWORD = "bbpt-judge"

st.markdown("""
<style>
    header[data-testid="stHeader"] { display: none !important; }
    .block-container { padding-top: 2rem !important; padding-bottom: 0.5rem !important; max-width: 100% !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# GESTÃO GLOBAL DE LOGIN (SIDEBAR AJUSTADA)
# ==========================================
from streamlit_cookies_controller import CookieController
import hashlib

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
        with open(logo_path, "rb") as image_file: encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-right:10px;'><h1 style='display:inline;font-size:1.8rem;'></h1></div>", unsafe_allow_html=True)
    else: st.title("🛡️ BBPT App")
    st.divider()

    # Menu Dinâmico Hierárquico
    opcoes_menu = ["📝 Formulário Público", "🔍 Consulta Pública"]
    if st.session_state.user_role in ["admin", "owner"]:
        opcoes_menu.append("⚙️ Painel de Organização")
    if st.session_state.user_role == "owner":
        opcoes_menu.append("👥 Gestão de Utilizadores")

    menu = st.radio("Navegação:", opcoes_menu)
    st.divider()
    
    # Sistema Unificado de Input de Chaves
    if not st.session_state.user_role:
        with st.expander("🔐 Acesso Organização / Judges"):
            pwd = st.text_input("Password:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                # AGORA LÊ DO SECRETS.TOML COM SEGURANÇA
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
        st.success(f"🔓 Modo {st.session_state.user_role.upper()} Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.user_role = None
            st.session_state.finance_auth = False # Garante que limpa a RAM
            
            # Tenta apagar os cookies de forma segura, ignorando se não existirem
            try: controller.remove('user_role')
            except: pass
            
            try: controller.remove('finance_auth')
            except: pass
            
            st.rerun()

# --- BLOQUEIO DE PÁGINA PARA PÚBLICO ---
if st.session_state.user_role not in ["admin", "judge"]:
    st.warning("🛑 Acesso Restrito: Apenas a Organização e os Juízes (Judges) podem aceder ao Battle Logger.")
    st.stop()

# ==========================================
# LIGAÇÃO À BASE DE DADOS E FUNCÕES DE BATALHA
# ==========================================
DB_FILE = 'logger_db.json'

@st.cache_data(ttl=2) # ⚡ SUPER RÁPIDO
def get_all_events_info():
    try:
        res = supabase.table("tournaments").select("*").execute()
        events = {}
        for row in res.data:
            ev_name = str(row.get("name", "")).strip()
            is_current = row.get("is_active", False)
            deck_check_is_open = row.get("checkin_open", False)
            if ev_name:
                if is_current:
                    events[ev_name] = {"matching_open": not deck_check_is_open, "is_current": True, "deck_check_status": deck_check_is_open}
                else:
                    if ev_name not in events:
                        events[ev_name] = {"matching_open": False, "is_current": False, "deck_check_status": False}
        return events
    except Exception as e: return {}

@st.cache_data(ttl=5) # ⚡ RÁPIDO
def get_real_players_and_combos(active_event_name):
    try:
        res_t = supabase.table("tournaments").select("id").eq("name", active_event_name).execute()
        if not res_t.data: return {}
        t_id = res_t.data[0]["id"]
        res_reg = supabase.table("tournament_registrations").select("combo_1, combo_2, combo_3, combo_4, bladers(alias)").eq("tournament_id", t_id).execute()
        db_combos = {}
        for row in res_reg.data:
            player = row["bladers"]["alias"] if row.get("bladers") else ""
            if player:
                combos = [str(row.get("combo_1", "")).strip(), str(row.get("combo_2", "")).strip(), str(row.get("combo_3", "")).strip(), str(row.get("combo_4", "")).strip()]
                db_combos[player] = [c for c in combos if c]
        return db_combos
    except Exception as e: return {}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {}

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

def auto_save_battle():
    db = load_db()
    b_id = st.session_state.battle_id
    db[b_id] = {
        "Event_Name": st.session_state.active_event,
        "Status": "Em Curso" if st.session_state.phase != 'match_over' else "Terminada",
        "P1_Name": st.session_state.p1_name, "P2_Name": st.session_state.p2_name,
        "P1_Score": st.session_state.p1_score, "P2_Score": st.session_state.p2_score,
        "Limit": st.session_state.limit, "Phase": st.session_state.phase,
        "Current_Round": st.session_state.current_round, "Match_Log": st.session_state.match_log,
        "P1_Active_Deck": st.session_state.get('p1_active_deck', []), "P2_Active_Deck": st.session_state.get('p2_active_deck', []),
        "P1_Deck_Pool": st.session_state.p1_deck_pool, "P2_Deck_Pool": st.session_state.p2_deck_pool
    }
    save_db(db)

def load_battle_into_memory(b_id, data):
    st.session_state.battle_id = b_id
    for key, value in data.items(): st.session_state[key.lower()] = value
    st.session_state.phase = data["Phase"]

def register_result(winner_name, finish_type, points, bey_winner, bey_loser):
    st.session_state.history.append({'p1_score': st.session_state.p1_score, 'p2_score': st.session_state.p2_score, 'current_round': st.session_state.current_round, 'phase': st.session_state.phase, 'log_len': len(st.session_state.match_log)})
    if winner_name == st.session_state.p1_name: st.session_state.p1_score += points
    else: st.session_state.p2_score += points
    st.session_state.match_log.append(f"⚔️ {winner_name} ({bey_winner}) venceu por {finish_type} (+{points}) contra {bey_loser}")
    if st.session_state.p1_score >= st.session_state.limit or st.session_state.p2_score >= st.session_state.limit: st.session_state.phase = 'match_over'
    else:
        st.session_state.current_round += 1
        if st.session_state.current_round > 2: st.session_state.phase = 'ordering'
    auto_save_battle()

def undo_last_action():
    if st.session_state.history:
        last = st.session_state.history.pop()
        st.session_state.p1_score = last['p1_score']
        st.session_state.p2_score = last['p2_score']
        st.session_state.current_round = last['current_round']
        st.session_state.phase = last['phase']
        st.session_state.match_log = st.session_state.match_log[:last['log_len']]
        auto_save_battle()

def auto_fill_p1():
    pool, s1, s2, s3 = st.session_state.p1_deck_pool, st.session_state.p1_1, st.session_state.p1_2, st.session_state.p1_3
    selected = [s for s in [s1, s2, s3] if s is not None]
    if len(selected) == 2 and len(set(selected)) == 2:
        rem = [c for c in pool if c not in selected][0]
        if s1 is None: st.session_state.p1_1 = rem
        if s2 is None: st.session_state.p1_2 = rem
        if s3 is None: st.session_state.p1_3 = rem

def auto_fill_p2():
    pool, s1, s2, s3 = st.session_state.p2_deck_pool, st.session_state.p2_1, st.session_state.p2_2, st.session_state.p2_3
    selected = [s for s in [s1, s2, s3] if s is not None]
    if len(selected) == 2 and len(set(selected)) == 2:
        rem = [c for c in pool if c not in selected][0]
        if s1 is None: st.session_state.p2_1 = rem
        if s2 is None: st.session_state.p2_2 = rem
        if s3 is None: st.session_state.p2_3 = rem

def archive_match_to_supabase(event_name, b_id, p1, p2, p1_score, p2_score, log):
    #try:
        supabase.table("matches").upsert({"id": b_id, "event_name": event_name, "p1_name": p1, "p2_name": p2, "score": f"{p1_score}-{p2_score}", "match_log": " | ".join(log)}).execute()
        st.success(f"✅ Partida do evento '{event_name}' arquivada na nuvem com sucesso!")
    #except Exception as e: st.error(f"❌ Erro ao comunicar com a Base de Dados na Nuvem: {e}")

def sync_from_supabase(event_name):
    try:
        res = supabase.table("matches").select("*").eq("event_name", event_name).execute()
        db = load_db()
        for k in [k for k, v in db.items() if v.get("Event_Name") == event_name and v.get("Status") == "Terminada"]: del db[k]
        count = 0
        for row in res.data:
            b_id = row["id"]
            placar = str(row["score"]).split('-')
            p1_s = int(placar[0]) if len(placar) == 2 and placar[0].strip().isdigit() else 0
            p2_s = int(placar[1]) if len(placar) == 2 and placar[1].strip().isdigit() else 0
            log_raw = str(row.get("match_log", ""))
            db[b_id] = {"Event_Name": event_name, "Status": "Terminada", "P1_Name": row["p1_name"], "P2_Name": row["p2_name"], "P1_Score": p1_s, "P2_Score": p2_s, "Match_Log": log_raw.split(" | ") if log_raw else [], "Phase": "match_over"}
            count += 1
        save_db(db)
        return True, count
    except Exception as e: return False, str(e)

# ==========================================
# INICIALIZAÇÃO DA SESSÃO
# ==========================================
if 'active_event' not in st.session_state: st.session_state.active_event = None
if 'history' not in st.session_state: st.session_state.history = []
if 'phase' not in st.session_state or st.session_state.phase == 'login': 
    st.session_state.phase = 'event_selection'

# ==========================================
# FASE 0.25: SELEÇÃO DE EVENTO 
# ==========================================
if st.session_state.phase == 'event_selection':
    st.markdown("### 📅 Selecionar Evento Ativo")
    st.info("Escolhe o evento atual ou consulta o histórico de eventos anteriores.")
    
    all_events = get_all_events_info()
    
    if not all_events:
        st.warning("Não há eventos na base de dados do Supabase.")
    else:
        lista_eventos = list(all_events.keys())
        event_name = st.selectbox("📍 Evento:", options=lista_eventos, index=None, placeholder="Escolhe um evento...")
        
        if st.button("Entrar no Lobby do Evento", type="primary", use_container_width=True):
            if event_name:
                st.session_state.active_event = event_name
                st.session_state.phase = 'lobby'
                st.rerun()
            else:
                st.error("⚠️ Seleciona um evento para continuar!")

# ==========================================
# FASE 0.5: O LOBBY
# ==========================================
elif st.session_state.phase == 'lobby':
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1: st.markdown(f"### 🏟️ Lobby: **{st.session_state.active_event}**")
    with col_t2:
        if st.button("🔄 Mudar Evento", use_container_width=True):
            st.session_state.active_event = None
            st.session_state.phase = 'event_selection'
            st.rerun()
            
    st.write("")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        all_events = get_all_events_info()
        event_data = all_events.get(st.session_state.active_event, {})
        is_matching_open = event_data.get("matching_open", False)
        is_current = event_data.get("is_current", False)
        
        if is_matching_open:
            st.info("O Deck Check está fechado. As batalhas estão Abertas!")
            if st.button("➕ Criar Nova Batalha", use_container_width=True, type="primary"):
                st.session_state.phase = 'setup'
                st.rerun()
        else:
            if is_current:
                st.warning("🔒 Batalhas Bloqueadas")
                st.caption("O Deck Check do torneio ainda está ABERTO. Para iniciar batalhas, o Admin deve fechar o Check-in.")
            else:
                st.warning("🗄️ Evento Arquivado")
                st.caption("Este torneio já terminou. Estás em modo de consulta do histórico.")
            
    with col2:
        st.warning("Retomar batalha pendente:")
        db = load_db()
        batalhas_ativas = {k: v for k, v in db.items() if v["Status"] == "Em Curso" and v.get("Event_Name") == st.session_state.active_event}
        
        if batalhas_ativas:
            opcoes = {k: f"{v['P1_Name']} vs {v['P2_Name']} ({v['P1_Score']}-{v['P2_Score']})" for k, v in batalhas_ativas.items()}
            escolha = st.selectbox("Selecionar Batalha em Curso:", options=list(opcoes.keys()), format_func=lambda x: opcoes[x])
            if st.button("▶️ Retomar Batalha", use_container_width=True):
                load_battle_into_memory(escolha, db[escolha])
                st.rerun()
        else:
            st.success("Nenhuma batalha ativa neste evento.")

    st.divider()
    st.markdown("### 🏆 Batalhas Concluídas (Arquivo Local)")
    
    if st.button("☁️ Recuperar Histórico da Nuvem", use_container_width=True):
        with st.spinner("A procurar na nuvem e a reescrever o ficheiro local..."):
            success, msg = sync_from_supabase(st.session_state.active_event)
            if success:
                st.success(f"✅ Foram recuperadas {msg} batalhas para o lobby.")
                time.sleep(1.5)
                st.rerun()
            else: st.error(f"❌ Erro ao sincronizar: {msg}")
    
    db = load_db() 
    batalhas_concluidas = {k: v for k, v in db.items() if v["Status"] == "Terminada" and v.get("Event_Name") == st.session_state.active_event}
    
    if batalhas_concluidas:
        for b_id, b_data in batalhas_concluidas.items():
            c_info, c_del, c_space = st.columns([4, 2, 4])
            with c_info:
                st.markdown(f"#### 👤 {b_data['P1_Name']} vs {b_data['P2_Name']}")
                st.caption(f"Placar Final: **{b_data['P1_Score']} - {b_data['P2_Score']}**")
            with c_del:
                st.write("") 
                if st.session_state.get(f"confirm_del_{b_id}"):
                    c_yes, c_no = st.columns(2)
                    if c_yes.button("✔️", key=f"yes_{b_id}"):
                        del db[b_id]
                        save_db(db)
                        supabase.table("match_logs").delete().eq("battle_id", b_id).execute()
                        st.session_state[f"confirm_del_{b_id}"] = False
                        st.rerun()
                    if c_no.button("❌", key=f"no_{b_id}"):
                        st.session_state[f"confirm_del_{b_id}"] = False
                        st.rerun()
                else:
                    if st.button("🗑️ Eliminar", key=f"del_{b_id}", use_container_width=True):
                        st.session_state[f"confirm_del_{b_id}"] = True
                        st.rerun()
            st.write("") 
    else: st.info(f"Ainda não há resultados finais para '{st.session_state.active_event}'.")

# ==========================================
# FASE 1: SETUP E DRAFTING
# ==========================================
elif st.session_state.phase == 'setup':
    st.markdown(f"### 1. Configuração da Partida")
    st.caption(f"A indexar a: **{st.session_state.active_event}**")
    st.write("")
    
    current_db = get_real_players_and_combos(st.session_state.active_event)
    lista_jogadores = list(current_db.keys())
    
    if not lista_jogadores:
        st.warning(f"Ainda não há jogadores submetidos no evento '{st.session_state.active_event}'.")
        if st.button("Voltar ao Lobby"):
            st.session_state.phase = 'lobby'
            st.rerun()
    else:
        c1, c2 = st.columns(2)
        with c1:
            p1_name = st.selectbox("Jogador 1:", options=lista_jogadores, index=None)
            p1_pool = current_db.get(p1_name, []) if p1_name else []
            st.markdown("**Ordem Inicial (Escolhe 3 de 4):**")
            p1_1 = st.selectbox("1º Beyblade (P1)", p1_pool, index=None, key="setup_p1_1", disabled=not p1_name)
            p1_2 = st.selectbox("2º Beyblade (P1)", p1_pool, index=None, key="setup_p1_2", disabled=not p1_name)
            p1_3 = st.selectbox("3º Beyblade (P1)", p1_pool, index=None, key="setup_p1_3", disabled=not p1_name)
            p1_draft = [p1_1, p1_2, p1_3]

        with c2:
            p2_name = st.selectbox("Jogador 2:", options=lista_jogadores, index=None)
            p2_pool = current_db.get(p2_name, []) if p2_name else []
            st.markdown("**Ordem Inicial (Escolhe 3 de 4):**")
            p2_1 = st.selectbox("1º Beyblade (P2)", p2_pool, index=None, key="setup_p2_1", disabled=not p2_name)
            p2_2 = st.selectbox("2º Beyblade (P2)", p2_pool, index=None, key="setup_p2_2", disabled=not p2_name)
            p2_3 = st.selectbox("3º Beyblade (P2)", p2_pool, index=None, key="setup_p2_3", disabled=not p2_name)
            p2_draft = [p2_1, p2_2, p2_3]

        limit = st.radio("Limite de Pontos:", [4, 5, 7], horizontal=True)

        st.write("")
        col_back, col_start = st.columns(2)
        
        with col_back:
            if st.button("🚪 Voltar ao Lobby", use_container_width=True):
                evt = st.session_state.active_event
                st.session_state.clear()
                st.session_state.active_event = evt
                st.session_state.phase = 'lobby'
                st.rerun()
                
        with col_start:
            if st.button("▶️ Iniciar Batalha", use_container_width=True, type="primary"):
                if p1_name and p2_name and p1_name == p2_name:
                    st.error("⚠️ Um jogador não pode batalhar contra si próprio!")
                elif p1_name and p2_name and None not in p1_draft and None not in p2_draft:
                    if len(set(p1_draft)) == 3 and len(set(p2_draft)) == 3:
                        st.session_state.p1_name = p1_name
                        st.session_state.p2_name = p2_name
                        st.session_state.p1_deck_pool = p1_draft.copy()
                        st.session_state.p2_deck_pool = p2_draft.copy()
                        st.session_state.p1_active_deck = p1_draft.copy()
                        st.session_state.p2_active_deck = p2_draft.copy()
                        st.session_state.limit = limit
                        st.session_state.p1_score = 0
                        st.session_state.p2_score = 0
                        st.session_state.current_round = 0
                        st.session_state.match_log = []
                        
                        timestamp = datetime.now().strftime("%H%M%S")
                        st.session_state.battle_id = f"{p1_name}_{p2_name}_{timestamp}"
                        st.session_state.phase = 'battle'
                        
                        for k in ['setup_p1_1', 'setup_p1_2', 'setup_p1_3', 'setup_p2_1', 'setup_p2_2', 'setup_p2_3']: 
                            if k in st.session_state: del st.session_state[k]
                            
                        auto_save_battle() 
                        st.rerun()
                    else: st.error("⚠️ Encontrámos Beys repetidos na seleção!")
                else: st.warning("⚠️ Seleciona os dois jogadores e a ordem completa!")

# ==========================================
# FASE 2: ORDERING / RESHUFFLE
# ==========================================
elif st.session_state.phase == 'ordering':
    st.markdown("""
    <div style='background-color: #ff4b4b; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
        <h1 style='color: white; margin: 0; font-size: 3rem;'>🚨 RESHUFFLE 🚨</h1>
        <p style='color: white; font-size: 1.2rem; margin: 0;'>Escolham a nova ordem secreta dos Beys!</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("💡 Dica: Ao escolheres 2 combos, o 3º preenche automaticamente.")
    
    if st.session_state.history: st.button("↩️ OOPS! Desfazer Última Ação", use_container_width=True, on_click=undo_last_action)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"### 🟢 {st.session_state.p1_name}")
        p1_1 = st.selectbox("1º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key="p1_1", on_change=auto_fill_p1)
        p1_2 = st.selectbox("2º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key="p1_2", on_change=auto_fill_p1)
        p1_3 = st.selectbox("3º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key="p1_3", on_change=auto_fill_p1)
        
    with c2:
        st.markdown(f"### 🔴 {st.session_state.p2_name}")
        p2_1 = st.selectbox("1º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key="p2_1", on_change=auto_fill_p2)
        p2_2 = st.selectbox("2º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key="p2_2", on_change=auto_fill_p2)
        p2_3 = st.selectbox("3º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key="p2_3", on_change=auto_fill_p2)

    st.write("")
    col_back, col_enter = st.columns(2)
    
    with col_back:
        if st.button("🚪 Voltar ao Lobby", use_container_width=True):
            evt = st.session_state.active_event
            st.session_state.clear()
            st.session_state.active_event = evt
            st.session_state.phase = 'lobby'
            st.rerun()
            
    with col_enter:
        if st.button("⚔️ Entrar na Arena!", use_container_width=True, type="primary"):
            p1_choices = [p1_1, p1_2, p1_3]
            p2_choices = [p2_1, p2_2, p2_3]
            
            if None in p1_choices or None in p2_choices: st.error("⚠️ Preenche os 3 lugares!")
            elif len(set(p1_choices)) == 3 and len(set(p2_choices)) == 3:
                st.session_state.p1_active_deck = p1_choices
                st.session_state.p2_active_deck = p2_choices
                st.session_state.current_round = 0 
                st.session_state.phase = 'battle'
                for k in ['p1_1', 'p1_2', 'p1_3', 'p2_1', 'p2_2', 'p2_3']: del st.session_state[k]
                auto_save_battle() 
                st.rerun()
            else: st.error("⚠️ Encontrámos Beys repetidos!")

# ==========================================
# FASE 3: BATTLE LOOP
# ==========================================
elif st.session_state.phase == 'battle':
    st.markdown("""
    <style>
        .block-container { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; gap: 0.2rem !important; }
        div[data-testid="stVerticalBlockBorderWrapper"] > div { padding: 0.5rem !important; gap: 0.2rem !important; }
        div.stButton > button { min-height: 45px !important; height: auto !important; border-radius: 6px !important; white-space: normal !important; margin-bottom: 0px !important; padding: 2px !important; }
        div.stButton > button p { font-size: clamp(12px, 2.5vw, 15px) !important; font-weight: 800 !important; line-height: 1 !important; margin: 0 !important; }
        .element-container:has(#btn-grid-p1) + .element-container > div[data-testid="stHorizontalBlock"], .element-container:has(#btn-grid-p2) + .element-container > div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 0.2rem !important; }
        .element-container:has(#btn-grid-p1) + .element-container > div[data-testid="stHorizontalBlock"] > div[data-testid="column"], .element-container:has(#btn-grid-p2) + .element-container > div[data-testid="stHorizontalBlock"] > div[data-testid="column"] { width: 50% !important; min-width: 48% !important; flex: 1 1 50% !important; }
        .element-container:has(#bottom-btns) + .element-container > div[data-testid="stHorizontalBlock"] { display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 0.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

    r_idx = st.session_state.current_round
    bey_p1 = st.session_state.p1_active_deck[r_idx]
    bey_p2 = st.session_state.p2_active_deck[r_idx]
    
    st.markdown(f"<p style='text-align: center; color: gray; margin: 0; padding: 0; font-size: 0.8rem;'><b>RONDA {r_idx + 1}/3 | Jogam até {st.session_state.limit} pts</b></p>", unsafe_allow_html=True)
    
    c_p1, c_p2 = st.columns(2)
    
    with c_p1:
        with st.container(border=True):
            st.markdown(f"<h4 style='text-align: center; margin: 0; padding: 0; line-height: 1.2;'>{st.session_state.p1_name}</h4>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='text-align: center; font-size: clamp(3rem, 8vw, 4rem); color: #4CAF50; line-height: 0.9; margin: 0; padding: 0;'>{st.session_state.p1_score}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.75rem; margin: 0 0 5px 0; padding: 0; line-height: 1;'>🛡️ {bey_p1}</p>", unsafe_allow_html=True)
            
            st.markdown('<span id="btn-grid-p1"></span>', unsafe_allow_html=True)
            btn1_p1, btn2_p1 = st.columns(2)
            with btn1_p1:
                st.button("🌀 Spin (+1)", key="p1_spin", use_container_width=True, on_click=register_result, args=(st.session_state.p1_name, "Spin Finish", 1, bey_p1, bey_p2))
                st.button("💥 Burst (+2)", key="p1_burst", use_container_width=True, on_click=register_result, args=(st.session_state.p1_name, "Burst Finish", 2, bey_p1, bey_p2))
            with btn2_p1:
                st.button("💨 Over (+2)", key="p1_over", use_container_width=True, on_click=register_result, args=(st.session_state.p1_name, "Over Finish", 2, bey_p1, bey_p2))
                st.button("⚡ X-Treme (+3)", key="p1_extreme", use_container_width=True, type="primary", on_click=register_result, args=(st.session_state.p1_name, "X-Treme Finish", 3, bey_p1, bey_p2))

    with c_p2:
        with st.container(border=True):
            st.markdown(f"<h4 style='text-align: center; margin: 0; padding: 0; line-height: 1.2;'>{st.session_state.p2_name}</h4>", unsafe_allow_html=True)
            st.markdown(f"<h1 style='text-align: center; font-size: clamp(3rem, 8vw, 4rem); color: #FF4B4B; line-height: 0.9; margin: 0; padding: 0;'>{st.session_state.p2_score}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.75rem; margin: 0 0 5px 0; padding: 0; line-height: 1;'>🛡️ {bey_p2}</p>", unsafe_allow_html=True)
            
            st.markdown('<span id="btn-grid-p2"></span>', unsafe_allow_html=True)
            btn1_p2, btn2_p2 = st.columns(2)
            with btn1_p2:
                st.button("🌀 Spin (+1)", key="p2_spin", use_container_width=True, on_click=register_result, args=(st.session_state.p2_name, "Spin Finish", 1, bey_p2, bey_p1))
                st.button("💥 Burst (+2)", key="p2_burst", use_container_width=True, on_click=register_result, args=(st.session_state.p2_name, "Burst Finish", 2, bey_p2, bey_p1))
            with btn2_p2:
                st.button("💨 Over (+2)", key="p2_over", use_container_width=True, on_click=register_result, args=(st.session_state.p2_name, "Over Finish", 2, bey_p2, bey_p1))
                st.button("⚡ X-Treme (+3)", key="p2_extreme", use_container_width=True, type="primary", on_click=register_result, args=(st.session_state.p2_name, "X-Treme Finish", 3, bey_p2, bey_p1))
            
    st.markdown('<span id="bottom-btns"></span>', unsafe_allow_html=True)
    aux_col1, aux_col2 = st.columns(2)
    with aux_col1:
        if st.button("🚪 Voltar ao Lobby", use_container_width=True):
            evt = st.session_state.active_event
            st.session_state.clear()
            st.session_state.active_event = evt
            st.session_state.phase = 'lobby'
            st.rerun()
            
    with aux_col2:
        if st.session_state.history: st.button("↩️ OOPS! Desfazer Última Ação", use_container_width=True, on_click=undo_last_action)

    if st.session_state.current_round == 0:
        if st.button("🔄 Corrigir Ordem dos Beys", use_container_width=True):
            st.session_state.phase = 'ordering'
            st.rerun()

# ==========================================
# FASE 4: MATCH OVER
# ==========================================
elif st.session_state.phase == 'match_over':
    st.balloons()
    st.success("🏆 BATALHA TERMINADA!")
    st.markdown(f"<h1 style='text-align: center; font-size: 5rem;'>{st.session_state.get('p1_score', 0)} - {st.session_state.get('p2_score', 0)}</h1>", unsafe_allow_html=True)
    
    if st.session_state.p1_score > st.session_state.p2_score: st.markdown(f"<h2 style='text-align: center;'>Vencedor: 👑 {st.session_state.p1_name}</h2>", unsafe_allow_html=True)
    else: st.markdown(f"<h2 style='text-align: center;'>Vencedor: 👑 {st.session_state.p2_name}</h2>", unsafe_allow_html=True)
        
    st.write("")
    col_undo, col_new = st.columns(2)
    with col_undo:
        if st.session_state.history:
            if st.button("↩️ Desfazer Último Ponto", use_container_width=True):
                if 'arquivado' in st.session_state: del st.session_state['arquivado']
                undo_last_action()
                st.rerun()
            
    with col_new:
        if st.button("✅ Confirmar o Resultado e Voltar ao Lobby do Evento", use_container_width=True, type="primary"):
            if 'arquivado' not in st.session_state:
                archive_match_to_supabase(st.session_state.active_event, st.session_state.battle_id, st.session_state.p1_name, st.session_state.p2_name, st.session_state.p1_score, st.session_state.p2_score, st.session_state.match_log)
                st.session_state.arquivado = True
                db = load_db()
                if st.session_state.battle_id in db:
                    db[st.session_state.battle_id]["Status"] = "Terminada" 
                    save_db(db)

            # LIMPEZA CIRÚRGICA: Apaga só os dados do combate e mantém o login e o evento ativos
            chaves_para_limpar = ['battle_id', 'p1_name', 'p2_name', 'p1_score', 'p2_score', 'match_log', 'history', 'arquivado']
            for chave in chaves_para_limpar:
                if chave in st.session_state:
                    del st.session_state[chave]
            st.rerun()
            
    st.divider()
    st.markdown("### Match Log Oficial:")
    st.dataframe(pd.DataFrame(st.session_state.match_log, columns=["Ação Registada"]), use_container_width=True)
