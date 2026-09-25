import streamlit as st
import pandas as pd
import base64
import os
import time
from datetime import datetime, date
import re
import hashlib
from db_connection import supabase
from assets import img_src

# 🛑 FORÇAR O MODO "WIDE" E AJUSTAR PADRÕES 🛑
st.set_page_config(page_title="BattleLogs", page_icon="📋", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    button[kind="header"] { display: block !important; visibility: visible !important; }
    [data-testid="stSidebarCollapsedControl"] { display: block !important; visibility: visible !important; position: fixed !important; left: 0 !important; z-index: 999999 !important; }
    [data-testid="stSidebar"] { display: block !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🔐 AUTENTICAÇÃO ESTÁTICA & PERSISTENTE (RBAC)
# ==========================================
if "is_admin" not in st.session_state: st.session_state.is_admin = False
if "is_judge" not in st.session_state: st.session_state.is_judge = False
if "auth_token" not in st.session_state: st.session_state.auth_token = None
if "blader_user" not in st.session_state: st.session_state.blader_user = None

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
        
logo_src = img_src("logo.png")

with st.sidebar:
    if logo_src:
        st.markdown(f"<div><img src='{logo_src}' width='150' style='margin-right:10px;'></div>", unsafe_allow_html=True)
    st.divider()
    
    if st.session_state.is_admin: st.success("🔓 Modo ADMIN Ativo")
    elif st.session_state.is_judge: st.success("⚖️ Modo JUIZ Ativo")
    elif st.session_state.blader_user: st.success(f"👤 Blader: {st.session_state.blader_user} Ativo")
        
    if st.session_state.is_admin or st.session_state.is_judge or st.session_state.blader_user:
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.is_admin = False
            st.session_state.is_judge = False
            st.session_state.auth_token = None
            st.session_state.blader_user = None
            st.query_params.clear() 
            st.rerun()

has_access = st.session_state.is_admin or (st.session_state.blader_user is not None)

if not has_access:
    st.title("📋 Consulta de BattleLogs")
    st.warning("🔐 Esta página requer autenticação.")
    
    if st.session_state.is_judge:
        st.info("⚖️ Olá Juiz, a extração de Logs está restrita à equipa de Administração.")
        st.stop()
        
    tab_blader, tab_org = st.tabs(["👤 Login Blader", "🛡️ Login Staff"])
    with tab_org:
        with st.form("login_org_form"):
            pwd_org = st.text_input("Chave de Acesso Admin:", type="password")
            submit_org = st.form_submit_button("Entrar 🔑", use_container_width=True)
            if submit_org:
                if pwd_org.strip() in admin_passwords:
                    st.session_state.is_admin = True
                    st.session_state.auth_token = pwd_org.strip()
                    st.query_params["admin"] = pwd_org.strip()
                    st.rerun()
                else: st.error("❌ Chave Incorreta ou sem privilégios de Admin!")
                
    with tab_blader:
        with st.form("login_blader_form"):
            blader_alias = st.text_input("Nickname / Alias do Blader:").strip()
            blader_pwd = st.text_input("Password:", type="password")
            submit_blader = st.form_submit_button("Entrar como Blader 🚀", use_container_width=True)
            if submit_blader:
                if not blader_alias or not blader_pwd:
                    st.error("⚠️ Preenche todos os campos!")
                else:
                    try:
                        raw_input = re.sub(r'^\d+[\.\s]*', '', blader_alias).strip().lower()
                        res = supabase.table("bladers").select("*").ilike("alias", blader_alias).execute()
                        if not res.data:
                            KNOWN_ALIASES = {"onez": "OneZarolho", "enzo": "OneZarolho", "onezarolho": "OneZarolho", "4exter": "Dexter", "exter": "Dexter", "paparapas": "Paparapas", "miguelbigg": "MiguelBigG", "velos77": "Velos77", "brunoveloso": "Velos77", "haalkein": "HaalKein", "hallkein": "HaalKein", "gordinho_pt": "Gordinho_PT", "gordo_pt": "Gordinho_PT"}
                            if raw_input in KNOWN_ALIASES:
                                official_alias = KNOWN_ALIASES[raw_input]
                                res = supabase.table("bladers").select("*").eq("alias", official_alias).execute()
                        if res.data:
                            user_data = res.data[0]
                            pass_na_bd = user_data.get("password_hash")
                            input_pwd_md5 = hashlib.md5(blader_pwd.encode('utf-8')).hexdigest()
                            if pass_na_bd == input_pwd_md5:
                                st.session_state.blader_user = user_data["alias"]
                                st.rerun()
                            else: st.error("❌ Password incorreta para este Blader!")
                        else: st.error("❌ Blader não encontrado na base de dados!")
                    except Exception as e: st.error(f"❌ Erro na ligação: {e}")
    st.stop()

# ==========================================
# MÓDULO PRINCIPAL DE EXTRAÇÃO DE LOGS
# ==========================================
st.title("📋 Histórico & BattleLogs Oficiais")
st.markdown("Filtra, analisa e exporta as sequências de combates diretamente da base de dados no formato **BattleLogs**.")

PAGE_SIZE = 1000  # O Supabase devolve no máximo 1000 linhas por pedido: lemos por páginas

def fetch_all_pages(build_query):
    rows, start = [], 0
    while True:
        res = build_query().range(start, start + PAGE_SIZE - 1).execute()
        batch = res.data or []
        rows.extend(batch)
        if len(batch) < PAGE_SIZE: return rows
        start += PAGE_SIZE

@st.cache_data(ttl=60)
def fetch_event_names():
    """Só a coluna event_name (leve) para montar a lista de torneios."""
    try:
        rows = fetch_all_pages(lambda: supabase.table("match_logs").select("event_name").order("created_at", desc=True))
        return sorted({r["event_name"] for r in rows if r.get("event_name")})
    except Exception as e:
        st.error(f"Erro ao ligar ao Supabase: {e}")
        return []

@st.cache_data(ttl=15)
def fetch_logs_for_events(event_names):
    """As batalhas completas, mas só dos torneios escolhidos (None = todos)."""
    def query():
        q = supabase.table("match_logs").select("*")
        if event_names is not None: q = q.in_("event_name", list(event_names))
        return q.order("created_at", desc=True)
    try:
        return fetch_all_pages(query)
    except Exception as e:
        st.error(f"Erro ao ligar ao Supabase: {e}")
        return []

torneios_disponiveis = fetch_event_names()

if not torneios_disponiveis:
    st.info("ℹ️ Ainda não existem registos de batalhas guardados na tabela `match_logs` do Supabase.")
else:
    
    col_t1, col_t2 = st.columns([3, 1])
    with col_t2:
        st.write("") 
        todos_torneios_cb = st.checkbox("Selecionar todos os Torneios", value=False)
        
    with col_t1:
        if todos_torneios_cb:
            torneios_selecionados = torneios_disponiveis
            st.multiselect("1️⃣ Torneio(s) Selecionado(s):", torneios_disponiveis, default=torneios_disponiveis, disabled=True)
        else:
            torneios_selecionados = st.multiselect("1️⃣ Escolha um ou mais Torneios em simultâneo:", torneios_disponiveis)
            
    if todos_torneios_cb: raw_logs = fetch_logs_for_events(None)
    elif torneios_selecionados: raw_logs = fetch_logs_for_events(tuple(torneios_selecionados))
    else: raw_logs = []
    df_filtrado_torneio = pd.DataFrame(raw_logs, columns=None if raw_logs else ['event_name', 'player_1', 'player_2'])
    
    jogadores_unicos = set()
    if not df_filtrado_torneio.empty:
        jogadores_unicos.update(df_filtrado_torneio['player_1'].dropna().unique().tolist())
        jogadores_unicos.update(df_filtrado_torneio['player_2'].dropna().unique().tolist())
        
    lista_jogadores = ["Todos os Players"] + sorted(list(jogadores_unicos))
    
    default_player_idx = 0
    if st.session_state.blader_user and st.session_state.blader_user in lista_jogadores:
        default_player_idx = lista_jogadores.index(st.session_state.blader_user)
        
    jogador_selecionado = st.selectbox("2️⃣ Filtrar por um Player específico (Opcional):", lista_jogadores, index=default_player_idx)
    
    if not torneios_selecionados:
        st.info("💡 Seleciona pelo menos um torneio ou ativa a caixa 'Selecionar todos os Torneios' para ver os resultados.")
    else:
        df_final = df_filtrado_torneio.copy()
        
        if jogador_selecionado != "Todos os Players":
            df_final = df_final[(df_final['player_1'] == jogador_selecionado) | (df_final['player_2'] == jogador_selecionado)]
            
        if df_final.empty:
            st.warning("⚠️ Não foram encontrados registos de batalhas para os filtros selecionados.")
        else:
            cols_to_extract = ['created_at', 'event_name', 'battle_id', 'player_1', 'player_2', 'final_score', 'detailed_log']
            if 'combo_p1' in df_final.columns and 'combo_p2' in df_final.columns:
                cols_to_extract = ['created_at', 'event_name', 'battle_id', 'player_1', 'combo_p1', 'player_2', 'combo_p2', 'final_score', 'detailed_log']
            
            cols_to_extract = [c for c in cols_to_extract if c in df_final.columns]
            df_battle_logs = df_final[cols_to_extract].copy()
            
            rename_dict = {
                'created_at': 'Data_Hora', 'event_name': 'Evento', 'battle_id': 'Battle_ID', 
                'player_1': 'Jogador_1', 'combo_p1': 'Combo_P1', 'player_2': 'Jogador_2', 
                'combo_p2': 'Combo_P2', 'final_score': 'Score_Final', 'detailed_log': 'Log_Detalhado'
            }
            df_battle_logs.rename(columns=rename_dict, inplace=True)
            
            if 'Data_Hora' in df_battle_logs.columns:
                df_battle_logs['Data_Hora'] = pd.to_datetime(df_battle_logs['Data_Hora']).dt.strftime('%Y-%m-%d %H:%M:%S')
            
            st.success(f"📋 Encontrados {len(df_battle_logs)} combates registados!")
            st.dataframe(df_battle_logs, use_container_width=True, hide_index=True)
            
            st.markdown("---")
            csv_bytes = df_battle_logs.to_csv(index=False).encode('utf-8-sig')
            
            if jogador_selecionado != "Todos os Players": sufixo = f"Player_{jogador_selecionado}"
            elif todos_torneios_cb: sufixo = "Todos_Os_Torneios"
            else: sufixo = "Torneios_Selecionados"
                
            st.download_button(
                label="📥 Descarregar logs e exportar para CSV (BattleLogs)",
                data=csv_bytes,
                file_name=f"BattleLogs_{sufixo}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True
            )
