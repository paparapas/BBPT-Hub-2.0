import streamlit as st
import pandas as pd
import base64
import os
import copy
import uuid
from datetime import datetime, timezone
from db_connection import supabase

# 🛑 FORÇAR O MODO "WIDE" E REMOVER ESPAÇOS BRANCOS 🛑
st.set_page_config(page_title="Battle Logger", page_icon="logo.png", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    /* Forçar o botão da sidebar a estar sempre visível */
    button[kind="header"] {
        display: block !important;
        visibility: visible !important;
    }

    /* Garantir que o contêiner da seta não é removido */
    [data-testid="stSidebarCollapsedControl"] {
        display: block !important;
        visibility: visible !important;
        position: fixed !important;
        left: 0 !important;
        z-index: 999999 !important;
    }
    
    /* Impedir que o telemóvel oculte a sidebar se for clicada */
    [data-testid="stSidebar"] {
        display: block !important;
    }
</style>
""", unsafe_allow_html=True)

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
has_logo = os.path.exists(logo_path)

@st.cache_data
def get_logo_b64(path):
    with open(path, "rb") as image_file: return base64.b64encode(image_file.read()).decode()

with st.sidebar:
    if has_logo:
        st.markdown(f"<div><img src='data:image/png;base64,{get_logo_b64(logo_path)}' width='150' style='margin-right:10px;'></div>", unsafe_allow_html=True)
    else: st.title("🛡️ BBPT App")
    st.divider()

    if st.session_state.is_admin:
        st.success("🔓 Modo ADMIN Ativo")
        if st.button("Sair (Logout) 🔒", width="stretch"):
            st.session_state.is_admin = False
            st.session_state.auth_token = None
            st.query_params.clear()
            st.rerun()
    elif st.session_state.is_judge:
        st.success("⚖️ Modo JUIZ Ativo")
        if st.button("Sair (Logout) 🔒", width="stretch"):
            st.session_state.is_judge = False
            st.session_state.auth_token = None
            st.query_params.clear()
            st.rerun()
    else:
        st.info("👤 Modo Público (Player)")

# --- BLOQUEIO DE PÁGINA PARA PÚBLICO (ACEITA AMBOS) ---
if not (st.session_state.is_admin or st.session_state.is_judge):
    st.warning("🛑 Acesso Restrito: Apenas a Organização e os Juízes podem aceder ao Battle Logger.")
    
    admin_pwd_input = st.text_input("Introduz a Chave de Acesso para prosseguir:", type="password")
    if st.button("Autenticar 🔑", type="primary"):
        if admin_pwd_input.strip() in admin_passwords:
            st.session_state.is_admin = True
            st.session_state.auth_token = admin_pwd_input.strip()
            st.query_params["admin"] = admin_pwd_input.strip()
            st.rerun()
        elif admin_pwd_input.strip() in judge_passwords:
            st.session_state.is_judge = True
            st.session_state.auth_token = admin_pwd_input.strip()
            st.query_params["judge"] = admin_pwd_input.strip()
            st.rerun()
        else:
            st.error("Chave incorreta!")
    st.stop()

if supabase is None:
    st.error("❌ Sem ligação à base de dados. Recarrega a página dentro de alguns segundos.")
    st.stop()

# ==========================================
# CONSTANTES DO ESTADO DA BATALHA
# ==========================================
# Tudo o que define uma batalha. É guardado no Supabase (tabela live_battles) a cada ação.
BATTLE_KEYS = ['p1_name', 'p2_name', 'p1_score', 'p2_score', 'limit', 'phase', 'current_round',
               'match_log', 'p1_active_deck', 'p2_active_deck', 'p1_deck_pool', 'p2_deck_pool',
               'p1_warnings', 'p2_warnings', 'ordering_mode', 'history']
SNAPSHOT_KEYS = [k for k in BATTLE_KEYS if k != 'history']   # O que o "Desfazer" repõe
BATTLE_DEFAULTS = {'p1_warnings': 0, 'p2_warnings': 0, 'ordering_mode': 'reshuffle', 'history': [], 'match_log': []}
ORDER_WIDGET_KEYS = ['p1_1', 'p1_2', 'p1_3', 'p2_1', 'p2_2', 'p2_3']
SETUP_WIDGET_KEYS = ['setup_p1_name', 'setup_p2_name', 'setup_p1_1', 'setup_p1_2', 'setup_p1_3', 'setup_p2_1', 'setup_p2_2', 'setup_p2_3']

# Prefixos do Match Log. Só as entradas "⚔️" (finishes normais) vão para o match_logs.
LOG_FINISH, LOG_WARNING, LOG_PENALTY = "⚔️", "⚠️", "🚫"

# ==========================================
# LEITURAS DO SUPABASE
# ==========================================
@st.cache_data(ttl=15)
def get_all_events_info():
    """Devolve {nome: info} ou None se houver erro de ligação."""
    try:
        res = supabase.table("tournaments").select("name, is_active, checkin_open").execute()
        events = {}
        for row in res.data:
            ev_name = str(row.get("name") or "").strip()
            if not ev_name: continue
            is_current = bool(row.get("is_active"))
            deck_check_is_open = bool(row.get("checkin_open"))
            if is_current:
                events[ev_name] = {"matching_open": not deck_check_is_open, "is_current": True}
            elif ev_name not in events:
                events[ev_name] = {"matching_open": False, "is_current": False}
        return events
    except Exception:
        return None

@st.cache_data(ttl=30)
def get_real_players_and_combos(active_event_name):
    """Devolve {jogador: [combos]} ou None se houver erro de ligação."""
    try:
        res_t = supabase.table("tournaments").select("id").eq("name", active_event_name).execute()
        if not res_t.data: return {}
        t_id = res_t.data[0]["id"]
        res_reg = supabase.table("tournament_registrations").select("combo_1, combo_2, combo_3, combo_4, bladers(alias)").eq("tournament_id", t_id).execute()
        db_combos = {}
        for row in res_reg.data:
            player = row["bladers"]["alias"] if row.get("bladers") else ""
            if player:
                combos = [str(row.get(f"combo_{i}") or "").strip() for i in range(1, 5)]
                db_combos[player] = [c for c in combos if c]
        return dict(sorted(db_combos.items(), key=lambda x: x[0].lower()))
    except Exception:
        return None

def get_pending_battles(event_name):
    try:
        res = supabase.table("live_battles").select("*").eq("event_name", event_name) \
            .in_("status", ["Em Curso", "Por Confirmar"]).order("updated_at", desc=True).execute()
        return res.data or []
    except Exception:
        return None

def get_finished_battles(event_name):
    try:
        res = supabase.table("match_logs").select("id, battle_id, player_1, player_2, final_score, created_at") \
            .eq("event_name", event_name).order("created_at", desc=True).execute()
        return res.data or []
    except Exception:
        return None

# ==========================================
# ESCRITAS NO SUPABASE
# ==========================================
def save_battle():
    """Guarda o estado completo da batalha atual. Devolve True/False e nunca rebenta a app."""
    try:
        state = {k: st.session_state.get(k, BATTLE_DEFAULTS.get(k)) for k in BATTLE_KEYS}
        supabase.table("live_battles").upsert({
            "battle_id": st.session_state.battle_id,
            "event_name": st.session_state.active_event,
            "p1_name": st.session_state.p1_name,
            "p2_name": st.session_state.p2_name,
            "p1_score": st.session_state.p1_score,
            "p2_score": st.session_state.p2_score,
            "status": "Por Confirmar" if st.session_state.phase == 'match_over' else "Em Curso",
            "state": state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        st.session_state.save_error = False
        return True
    except Exception:
        st.session_state.save_error = True
        return False

def archive_match_to_supabase():
    """Envia o resultado final para match_logs (só finishes normais) e fecha a live battle."""
    b_id = st.session_state.battle_id
    exists = supabase.table("match_logs").select("id").eq("battle_id", b_id).execute()
    if not exists.data:  # Proteção contra duplicados (duplo toque, dois telemóveis...)
        clean_log = [e for e in st.session_state.match_log if e.startswith(LOG_FINISH)]
        supabase.table("match_logs").insert({
            "event_name": st.session_state.active_event,
            "battle_id": b_id,
            "player_1": st.session_state.p1_name,
            "player_2": st.session_state.p2_name,
            "final_score": f"{st.session_state.p1_score}-{st.session_state.p2_score}",
            "detailed_log": " | ".join(clean_log)
        }).execute()
    supabase.table("live_battles").update({"status": "Terminada", "updated_at": datetime.now(timezone.utc).isoformat()}).eq("battle_id", b_id).execute()

def delete_finished_battle(row_id, battle_id):
    supabase.table("match_logs").delete().eq("id", row_id).execute()
    if battle_id: supabase.table("live_battles").delete().eq("battle_id", battle_id).execute()

# ==========================================
# GESTÃO DE MEMÓRIA DA SESSÃO
# ==========================================
def clear_keys(keys):
    for k in keys:
        if k in st.session_state: del st.session_state[k]

def clear_battle_state():
    """Limpa só a batalha. Login e evento ficam intactos."""
    clear_keys(BATTLE_KEYS + ['battle_id', 'save_error', 'balloons_shown'] + ORDER_WIDGET_KEYS + SETUP_WIDGET_KEYS)

def load_battle_into_memory(row):
    clear_battle_state()
    state = row.get("state") or {}
    for k in BATTLE_KEYS:
        st.session_state[k] = copy.deepcopy(state.get(k, BATTLE_DEFAULTS.get(k)))
    st.session_state.battle_id = row["battle_id"]
    if st.session_state.phase == 'match_over': st.session_state.balloons_shown = True

def go_to_lobby():
    clear_battle_state()
    st.session_state.phase = 'lobby'

def leave_battle_to_lobby():
    """Sai para o lobby. Se a última gravação falhou, tenta guardar antes para não perder nada."""
    if st.session_state.get('save_error') and not save_battle():
        st.error("❌ Ainda sem ligação: não saias desta batalha até conseguir guardar (toca em 🔁 Guardar agora).")
        return False
    go_to_lobby()
    return True

# ==========================================
# LÓGICA DA BATALHA (callbacks)
# ==========================================
def other(side): return 'p2' if side == 'p1' else 'p1'

def push_history():
    snap = {k: copy.deepcopy(st.session_state.get(k, BATTLE_DEFAULTS.get(k))) for k in SNAPSHOT_KEYS}
    st.session_state.history.append(snap)

def check_match_over():
    if st.session_state.p1_score >= st.session_state.limit or st.session_state.p2_score >= st.session_state.limit:
        st.session_state.phase = 'match_over'
        return True
    return False

def register_result(side, finish_type, points):
    """Finish normal: dá pontos, avança a ronda e limpa os avisos de ambos."""
    push_history()
    r = st.session_state.current_round
    bey_w = st.session_state[f"{side}_active_deck"][r]
    bey_l = st.session_state[f"{other(side)}_active_deck"][r]
    winner_name = st.session_state[f"{side}_name"]
    st.session_state[f"{side}_score"] += points
    st.session_state.match_log.append(f"{LOG_FINISH} {winner_name} ({bey_w}) venceu por {finish_type} (+{points}) contra {bey_l}")
    st.session_state.p1_warnings = 0
    st.session_state.p2_warnings = 0
    if not check_match_over():
        st.session_state.current_round += 1
        if st.session_state.current_round > 2:
            st.session_state.phase = 'ordering'
            st.session_state.ordering_mode = 'reshuffle'
            clear_keys(ORDER_WIDGET_KEYS)
    save_battle()

def register_launch_error(side):
    """1º erro = aviso. 2º erro = +1 ao adversário, avisos voltam a 0, mesma ronda e mesmos Beys."""
    push_history()
    name = st.session_state[f"{side}_name"]
    opp = other(side)
    st.session_state[f"{side}_warnings"] += 1
    if st.session_state[f"{side}_warnings"] >= 2:
        st.session_state[f"{opp}_score"] += 1
        st.session_state[f"{side}_warnings"] = 0
        st.session_state.match_log.append(f"{LOG_PENALTY} {name}: 2º Launch Error, +1 para {st.session_state[f'{opp}_name']}")
        check_match_over()
    else:
        st.session_state.match_log.append(f"{LOG_WARNING} {name}: Launch Error (1º aviso)")
    save_battle()

def undo_last_action():
    if st.session_state.get('history'):
        last = st.session_state.history.pop()
        for k, v in last.items(): st.session_state[k] = v
        clear_keys(ORDER_WIDGET_KEYS + ['balloons_shown'])
        save_battle()

def auto_fill(prefix, pool):
    """Se só sobrar uma opção possível, preenche o lugar vazio."""
    keys = [f"{prefix}_{i}" for i in (1, 2, 3)]
    selected = [st.session_state.get(k) for k in keys]
    chosen = [s for s in selected if s is not None]
    if len(chosen) == 2 and len(set(chosen)) == 2:
        remaining = [c for c in pool if c not in chosen]
        if len(remaining) == 1:
            for k, s in zip(keys, selected):
                if s is None: st.session_state[k] = remaining[0]

def on_setup_player_change(side):
    clear_keys([f"setup_{side}_{i}" for i in (1, 2, 3)])
    if side == 'p1' and st.session_state.get('setup_p2_name') == st.session_state.get('setup_p1_name'):
        clear_keys(['setup_p2_name', 'setup_p2_1', 'setup_p2_2', 'setup_p2_3'])

def open_order_correction():
    st.session_state.phase = 'ordering'
    st.session_state.ordering_mode = 'correction'
    for side in ('p1', 'p2'):
        for i, bey in enumerate(st.session_state[f"{side}_active_deck"]):
            st.session_state[f"{side}_{i + 1}"] = bey
    save_battle()

# ==========================================
# COMPONENTES VISUAIS
# ==========================================
def warning_badge(n):
    return f" <span style='background:#f0ad4e; color:#000; border-radius:6px; padding:0 6px; font-size:0.8rem;'>⚠️ {n}</span>" if n else ""

def render_score_bar():
    s = st.session_state
    st.markdown(f"""
    <div style='display:flex; justify-content:space-between; align-items:center; border:1px solid rgba(128,128,128,0.35);
                border-radius:10px; padding:8px 14px; margin-bottom:10px;'>
        <div style='text-align:left; flex:1;'><b>{s.p1_name}</b>{warning_badge(s.p1_warnings)}</div>
        <div style='text-align:center; flex:1; font-size:1.8rem; font-weight:900; white-space:nowrap;'>
            <span style='color:#4CAF50;'>{s.p1_score}</span> - <span style='color:#FF4B4B;'>{s.p2_score}</span>
            <div style='font-size:0.7rem; color:gray; font-weight:400;'>Jogam até {s.limit} pts</div>
        </div>
        <div style='text-align:right; flex:1;'>{warning_badge(s.p2_warnings)}<b>{s.p2_name}</b></div>
    </div>
    """, unsafe_allow_html=True)

def render_save_error():
    if st.session_state.get('save_error'):
        c_msg, c_btn = st.columns([3, 1])
        c_msg.error("☁️ A última ação não foi guardada na nuvem (rede?). O placar neste ecrã está correto.")
        if c_btn.button("🔁 Guardar agora", width="stretch"):
            if save_battle(): st.toast("✅ Guardado!")
            st.rerun()

# ==========================================
# INICIALIZAÇÃO DA SESSÃO
# ==========================================
if 'active_event' not in st.session_state: st.session_state.active_event = None
if 'phase' not in st.session_state or st.session_state.phase == 'login':
    st.session_state.phase = 'event_selection'
if st.session_state.phase in ('battle', 'ordering', 'match_over') and 'battle_id' not in st.session_state:
    st.session_state.phase = 'lobby'   # Segurança: estado incompleto volta ao lobby

# ==========================================
# FASE 0.25: SELEÇÃO DE EVENTO 
# ==========================================
if st.session_state.phase == 'event_selection':
    st.markdown("### 📅 Selecionar Evento Ativo")
    st.info("Escolhe o evento atual ou consulta o histórico de eventos anteriores.")
    
    all_events = get_all_events_info()
    
    if all_events is None:
        st.error("❌ Não foi possível contactar a base de dados.")
        if st.button("🔄 Tentar novamente", width="stretch"):
            get_all_events_info.clear()
            st.rerun()
    elif not all_events:
        st.warning("Não há eventos na base de dados do Supabase.")
    else:
        lista_eventos = list(all_events.keys())
        event_name = st.selectbox("📍 Evento:", options=lista_eventos, index=None, placeholder="Escolhe um evento...")
        
        if st.button("Entrar no Lobby do Evento", type="primary", width="stretch"):
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
        if st.button("🔄 Mudar Evento", width="stretch"):
            st.session_state.active_event = None
            st.session_state.phase = 'event_selection'
            st.rerun()
        if st.button("♻️ Atualizar", width="stretch"):
            get_all_events_info.clear()
            get_real_players_and_combos.clear()
            st.rerun()
            
    st.write("")
    col1, col2 = st.columns([1, 1])
    
    with col1:
        all_events = get_all_events_info() or {}
        event_data = all_events.get(st.session_state.active_event, {})
        is_matching_open = event_data.get("matching_open", False)
        is_current = event_data.get("is_current", False)
        
        if is_matching_open:
            st.info("O Deck Check está fechado. As batalhas estão Abertas!")
            if st.button("➕ Criar Nova Batalha", width="stretch", type="primary"):
                clear_battle_state()
                st.session_state.phase = 'setup'
                st.rerun()
        else:
            if is_current:
                st.warning("🔒 Batalhas Bloqueadas")
                st.caption("O Deck Check do torneio ainda está ABERTO. Para iniciar batalhas, o Admin deve fechar o Check-in. Depois toca em ♻️ Atualizar.")
            else:
                st.warning("🗄️ Evento Arquivado")
                st.caption("Este torneio já terminou. Estás em modo de consulta do histórico.")
            
    with col2:
        st.warning("Retomar batalha pendente:")
        pendentes = get_pending_battles(st.session_state.active_event)
        
        if pendentes is None:
            st.error("❌ Não foi possível carregar as batalhas em curso.")
        elif pendentes:
            por_id = {b["battle_id"]: b for b in pendentes}
            def fmt(b_id):
                b = por_id[b_id]
                tag = " ✅ Por Confirmar" if b["status"] == "Por Confirmar" else ""
                return f"{b['p1_name']} vs {b['p2_name']} ({b['p1_score']}-{b['p2_score']}){tag}"
            escolha = st.selectbox("Selecionar Batalha em Curso:", options=list(por_id.keys()), format_func=fmt)
            if st.button("▶️ Retomar Batalha", width="stretch"):
                load_battle_into_memory(por_id[escolha])
                st.rerun()
        else:
            st.success("Nenhuma batalha ativa neste evento.")

    st.divider()
    st.markdown("### 🏆 Batalhas Concluídas")
    
    concluidas = get_finished_battles(st.session_state.active_event)
    
    if concluidas is None:
        st.error("❌ Não foi possível carregar as batalhas concluídas.")
    elif concluidas:
        for b in concluidas:
            row_id = b["id"]
            c_info, c_del, c_space = st.columns([4, 2, 4])
            with c_info:
                st.markdown(f"#### 👤 {b['player_1']} vs {b['player_2']}")
                st.caption(f"Placar Final: **{b['final_score']}**")
            with c_del:
                if st.session_state.is_admin:
                    st.write("") 
                    if st.session_state.get(f"confirm_del_{row_id}"):
                        c_yes, c_no = st.columns(2)
                        if c_yes.button("✔️", key=f"yes_{row_id}"):
                            try:
                                delete_finished_battle(row_id, b.get("battle_id"))
                                st.toast("🗑️ Batalha eliminada.")
                            except Exception:
                                st.error("❌ Não foi possível eliminar (rede?). Tenta novamente.")
                            st.session_state[f"confirm_del_{row_id}"] = False
                            st.rerun()
                        if c_no.button("❌", key=f"no_{row_id}"):
                            st.session_state[f"confirm_del_{row_id}"] = False
                            st.rerun()
                    else:
                        if st.button("🗑️ Eliminar", key=f"del_{row_id}", width="stretch"):
                            st.session_state[f"confirm_del_{row_id}"] = True
                            st.rerun()
            st.write("") 
    else: st.info(f"Ainda não há resultados finais para '{st.session_state.active_event}'.")

# ==========================================
# FASE 1: SETUP E DRAFTING
# ==========================================
elif st.session_state.phase == 'setup':
    
    @st.fragment
    def painel_de_setup():
        if st.session_state.phase != 'setup': st.rerun()

        st.markdown(f"### 1. Configuração da Partida")
        st.caption(f"A indexar a: **{st.session_state.active_event}**")
        st.write("")
        
        current_db = get_real_players_and_combos(st.session_state.active_event)
        if current_db is None:
            st.error("❌ Não foi possível carregar os jogadores (rede?).")
            if st.button("🔄 Tentar novamente"):
                get_real_players_and_combos.clear()
                st.rerun()
            return
        lista_jogadores = list(current_db.keys())
        
        if not lista_jogadores:
            st.warning(f"Ainda não há jogadores submetidos no evento '{st.session_state.active_event}'.")
            if st.button("Voltar ao Lobby"):
                go_to_lobby()
                st.rerun()
            return

        c1, c2 = st.columns(2)
        with c1:
            p1_name = st.selectbox("Jogador 1:", options=lista_jogadores, index=None, key="setup_p1_name", on_change=on_setup_player_change, args=('p1',))
            p1_pool = current_db.get(p1_name, []) if p1_name else []
            st.markdown("**Ordem Inicial (Escolhe 3 de 4):**")
            p1_draft = [st.selectbox(f"{i}º Beyblade (P1)", p1_pool, index=None, key=f"setup_p1_{i}", disabled=not p1_name,
                                     on_change=auto_fill, args=('setup_p1', p1_pool)) for i in (1, 2, 3)]

        with c2:
            opcoes_p2 = [j for j in lista_jogadores if j != p1_name]
            p2_name = st.selectbox("Jogador 2:", options=opcoes_p2, index=None, key="setup_p2_name", on_change=on_setup_player_change, args=('p2',))
            p2_pool = current_db.get(p2_name, []) if p2_name else []
            st.markdown("**Ordem Inicial (Escolhe 3 de 4):**")
            p2_draft = [st.selectbox(f"{i}º Beyblade (P2)", p2_pool, index=None, key=f"setup_p2_{i}", disabled=not p2_name,
                                     on_change=auto_fill, args=('setup_p2', p2_pool)) for i in (1, 2, 3)]

        limit = st.radio("Limite de Pontos:", [4, 5, 7], horizontal=True)

        st.write("")
        col_back, col_start = st.columns(2)
        
        with col_back:
            if st.button("🚪 Voltar ao Lobby", width="stretch"):
                go_to_lobby()
                st.rerun()
                
        with col_start:
            if st.button("▶️ Iniciar Batalha", width="stretch", type="primary"):
                if not (p1_name and p2_name) or None in p1_draft or None in p2_draft:
                    st.warning("⚠️ Seleciona os dois jogadores e a ordem completa!")
                elif p1_name == p2_name:
                    st.error("⚠️ Um jogador não pode batalhar contra si próprio!")
                elif len(set(p1_draft)) != 3 or len(set(p2_draft)) != 3:
                    st.error("⚠️ Encontrámos Beys repetidos na seleção!")
                else:
                    st.session_state.p1_name = p1_name
                    st.session_state.p2_name = p2_name
                    st.session_state.p1_deck_pool = p1_draft.copy()
                    st.session_state.p2_deck_pool = p2_draft.copy()
                    st.session_state.p1_active_deck = p1_draft.copy()
                    st.session_state.p2_active_deck = p2_draft.copy()
                    st.session_state.limit = limit
                    st.session_state.p1_score = 0
                    st.session_state.p2_score = 0
                    st.session_state.p1_warnings = 0
                    st.session_state.p2_warnings = 0
                    st.session_state.current_round = 0
                    st.session_state.match_log = []
                    st.session_state.history = []
                    st.session_state.ordering_mode = 'reshuffle'
                    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    st.session_state.battle_id = f"{p1_name}_{p2_name}_{stamp}_{uuid.uuid4().hex[:4]}"
                    st.session_state.phase = 'battle'
                    clear_keys(SETUP_WIDGET_KEYS)
                    save_battle()
                    st.rerun()

    painel_de_setup()

# ==========================================
# FASE 2: ORDERING / RESHUFFLE
# ==========================================
elif st.session_state.phase == 'ordering':
    
    @st.fragment
    def painel_de_ordem():
        # Se o "Desfazer" mudar a fase, sai do fragmento imediatamente
        if st.session_state.phase != 'ordering': st.rerun()

        render_save_error()
        render_score_bar()

        if st.session_state.get('ordering_mode') == 'correction':
            st.markdown("### 🔄 Corrigir Ordem dos Beys")
            st.caption("Ajusta a ordem inicial e volta à Arena.")
        else:
            st.markdown("""
            <div style='background-color: #ff4b4b; padding: 15px; border-radius: 10px; text-align: center; margin-bottom: 20px;'>
                <h1 style='color: white; margin: 0; font-size: 3rem;'>🚨 RESHUFFLE 🚨</h1>
                <p style='color: white; font-size: 1.2rem; margin: 0;'>Escolham a nova ordem secreta dos Beys!</p>
            </div>
            """, unsafe_allow_html=True)
            st.info("💡 Dica: Ao escolheres 2 combos, o 3º preenche automaticamente.")
        
        if st.session_state.history: st.button("↩️ OOPS! Desfazer Última Ação", width="stretch", on_click=undo_last_action)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"### 🟢 {st.session_state.p1_name}")
            p1_choices = [st.selectbox(f"{i}º Beyblade (P1)", st.session_state.p1_deck_pool, index=None, key=f"p1_{i}",
                                       on_change=auto_fill, args=('p1', st.session_state.p1_deck_pool)) for i in (1, 2, 3)]
        with c2:
            st.markdown(f"### 🔴 {st.session_state.p2_name}")
            p2_choices = [st.selectbox(f"{i}º Beyblade (P2)", st.session_state.p2_deck_pool, index=None, key=f"p2_{i}",
                                       on_change=auto_fill, args=('p2', st.session_state.p2_deck_pool)) for i in (1, 2, 3)]

        st.write("")
        col_back, col_enter = st.columns(2)
        
        with col_back:
            if st.button("🚪 Voltar ao Lobby", width="stretch"):
                if leave_battle_to_lobby(): st.rerun()
                
        with col_enter:
            if st.button("⚔️ Entrar na Arena!", width="stretch", type="primary"):
                if None in p1_choices or None in p2_choices: st.error("⚠️ Preenche os 3 lugares!")
                elif len(set(p1_choices)) == 3 and len(set(p2_choices)) == 3:
                    st.session_state.p1_active_deck = p1_choices
                    st.session_state.p2_active_deck = p2_choices
                    st.session_state.current_round = 0 
                    st.session_state.phase = 'battle'
                    clear_keys(ORDER_WIDGET_KEYS)
                    save_battle()
                    st.rerun()
                else: st.error("⚠️ Encontrámos Beys repetidos!")

    painel_de_ordem()

# ==========================================
# FASE 3: BATTLE LOOP (ISOLADO PARA VELOCIDADE MÁXIMA)
# ==========================================
elif st.session_state.phase == 'battle':
    
    @st.fragment
    def painel_de_batalha():
        # Se a fase mudar por causa de uma vitória, reshuffle ou desfazer, sai do fragmento instantaneamente
        if st.session_state.phase != 'battle':
            st.rerun()

        # Os seletores .st-key-* vêm do parâmetro key= dos containers (estável nas versões atuais do Streamlit)
        st.markdown("""
        <style>
            .block-container, [data-testid="stMainBlockContainer"] { padding-top: 0.5rem !important; padding-bottom: 0.5rem !important; }
            .stButton button { min-height: 45px !important; height: auto !important; border-radius: 6px !important; white-space: normal !important; padding: 2px !important; }
            .stButton button p { font-size: clamp(12px, 2.5vw, 15px) !important; font-weight: 800 !important; line-height: 1 !important; margin: 0 !important; }
            .st-key-grid_p1 [data-testid="stHorizontalBlock"], .st-key-grid_p2 [data-testid="stHorizontalBlock"], .st-key-bottom_btns [data-testid="stHorizontalBlock"] {
                display: flex !important; flex-direction: row !important; flex-wrap: nowrap !important; gap: 0.25rem !important; }
            .st-key-grid_p1 [data-testid="stColumn"], .st-key-grid_p2 [data-testid="stColumn"], .st-key-bottom_btns [data-testid="stColumn"] {
                min-width: 0 !important; width: auto !important; flex: 1 1 0 !important; }
        </style>
        """, unsafe_allow_html=True)

        render_save_error()

        s = st.session_state
        r_idx = s.current_round
        beys = {'p1': s.p1_active_deck[r_idx], 'p2': s.p2_active_deck[r_idx]}
        
        st.markdown(f"<p style='text-align: center; color: gray; margin: 0; padding: 0; font-size: 0.8rem;'><b>RONDA {r_idx + 1}/3 | Jogam até {s.limit} pts</b></p>", unsafe_allow_html=True)
        
        cols = dict(zip(('p1', 'p2'), st.columns(2)))
        for side, color in (('p1', '#4CAF50'), ('p2', '#FF4B4B')):
            with cols[side]:
                with st.container(border=True, key=f"card_{side}"):
                    # Nome + placar + Bey num único bloco: sem espaços entre elementos, nada se sobrepõe
                    st.markdown(f"""
                    <div style='text-align: center;'>
                        <div style='font-size: 1.25rem; font-weight: 700; line-height: 1.2;'>{s[f'{side}_name']}{warning_badge(s[f'{side}_warnings'])}</div>
                        <div style='font-size: clamp(3rem, 8vw, 4rem); font-weight: 800; color: {color}; line-height: 1;'>{s[f'{side}_score']}</div>
                        <div style='color: gray; font-size: 0.75rem; line-height: 1.2; margin-bottom: 4px;'>🛡️ {beys[side]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    with st.container(key=f"grid_{side}"):
                        b1, b2 = st.columns(2)
                        with b1:
                            st.button("🌀 Spin (+1)", key=f"{side}_spin", width="stretch", on_click=register_result, args=(side, "Spin Finish", 1))
                            st.button("💥 Burst (+2)", key=f"{side}_burst", width="stretch", on_click=register_result, args=(side, "Burst Finish", 2))
                        with b2:
                            st.button("💨 Over (+2)", key=f"{side}_over", width="stretch", on_click=register_result, args=(side, "Over Finish", 2))
                            st.button("⚡ X-Treme (+3)", key=f"{side}_extreme", width="stretch", type="primary", on_click=register_result, args=(side, "X-Treme Finish", 3))
                    st.button("⚠️ Launch Error", key=f"{side}_launch", width="stretch", on_click=register_launch_error, args=(side,))
                
        with st.container(key="bottom_btns"):
            aux_col1, aux_col2 = st.columns(2)
            with aux_col1:
                if st.button("🚪 Voltar ao Lobby", width="stretch"):
                    if leave_battle_to_lobby(): st.rerun()   # A batalha já está guardada na nuvem a cada ação
            with aux_col2:
                if s.history: st.button("↩️ OOPS! Desfazer Última Ação", width="stretch", on_click=undo_last_action)

        if s.current_round == 0:
            st.button("🔄 Corrigir Ordem dos Beys", width="stretch", on_click=open_order_correction)

    # EXECUTA A FUNÇÃO ISOLADA
    painel_de_batalha()

# ==========================================
# FASE 4: MATCH OVER
# ==========================================
elif st.session_state.phase == 'match_over':
    if not st.session_state.get('balloons_shown'):
        st.balloons()
        st.session_state.balloons_shown = True
    st.success("🏆 BATALHA TERMINADA!")
    render_save_error()
    
    s = st.session_state
    st.markdown(f"<h1 style='text-align: center; font-size: 5rem;'>{s.p1_score} - {s.p2_score}</h1>", unsafe_allow_html=True)
    
    if s.p1_score > s.p2_score: 
        st.markdown(f"<h2 style='text-align: center;'>Vencedor: 👑 {s.p1_name}</h2>", unsafe_allow_html=True)
    elif s.p2_score > s.p1_score: 
        st.markdown(f"<h2 style='text-align: center;'>Vencedor: 👑 {s.p2_name}</h2>", unsafe_allow_html=True)
        
    st.write("")
    col_undo, col_new = st.columns(2)
    with col_undo:
        if s.get('history'):
            st.button("↩️ Desfazer Último Ponto", width="stretch", on_click=undo_last_action)
            
    with col_new:
        if st.button("✅ Confirmar o Resultado e Voltar ao Lobby do Evento", width="stretch", type="primary"):
            try:
                archive_match_to_supabase()
                go_to_lobby()
                st.rerun()
            except Exception:
                st.error("❌ Não foi possível enviar o resultado (rede?). Nada se perdeu: toca outra vez em Confirmar.")
            
    st.divider()
    st.markdown("### Match Log Oficial:")
    st.caption("Os avisos ⚠️ e penalizações 🚫 aparecem aqui, mas não são enviados para o Battle Logs.")
    st.dataframe(pd.DataFrame(s.get('match_log', []), columns=["Ação Registada"]), width="stretch")
