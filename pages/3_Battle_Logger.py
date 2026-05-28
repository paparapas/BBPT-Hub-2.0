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
# GESTÃO GLOBAL DE LOGIN (BLINDADA CONTRA QUEDAS)
# ==========================================
if "user_role" not in st.session_state:
    st.session_state.user_role = None

controller = CookieController()
cookie_role = controller.get('user_role')

if cookie_role in ["owner", "admin", "judge"]:
    st.session_state.user_role = cookie_role

logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"
has_logo = os.path.exists(logo_path)

with st.sidebar:
    if has_logo:
        with open(logo_path, "rb") as image_file: 
            encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-right:10px;'><h1 style='display:inline;font-size:1.8rem;'></h1></div>", unsafe_allow_html=True)
    else: 
        st.title("🛡️ BBPT App")
    st.divider()
    
    if not st.session_state.user_role:
        with st.expander("🔐 Acesso Organização / Judges"):
            pwd = st.text_input("Password:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                if pwd.strip() == st.secrets.get("PASSWORDS", {}).get("OWNER", "bbpt-owner123"):
                    st.session_state.user_role = "owner"
                    controller.set('user_role', 'owner', max_age=43200)
                    st.rerun()
                elif pwd.strip() == ADMIN_PASSWORD:
                    st.session_state.user_role = "admin"
                    controller.set('user_role', 'admin', max_age=43200)
                    st.rerun()
                elif pwd.strip() == JUDGE_PASSWORD:
                    st.session_state.user_role = "judge"
                    controller.set('user_role', 'judge', max_age=43200)
                    st.rerun()
                else: 
                    st.error("Incorreta!")
    else:
        st.success(f"🔓 Modo {st.session_state.user_role.upper()} Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.user_role = None
            try: controller.remove('user_role')
            except: pass
            st.rerun()

if st.session_state.user_role not in ["admin", "owner", "judge"]:
    st.error("🛑 Acesso Restrito: Apenas a Organização e os Judges oficiais podem aceder ao Battle Logger.")
    st.stop()

# ==========================================
# LÓGICA DE DADOS (JSON LOCAL E SUPABASE)
# ==========================================
def load_db():
    if os.path.exists('bbpt_master_db.json'):
        with open('bbpt_master_db.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_db(db):
    with open('bbpt_master_db.json', 'w', encoding='utf-8') as f:
        json.dump(db, f, indent=4)

def archive_match_to_supabase(evento, battle_id, p1, p2, score1, score2, log_list):
    try:
        log_str = " | ".join(log_list)
        score_final = f"{score1}-{score2}"
        
        # Envia os dados exatamente no formato do MatchLogs para a nova tabela
        supabase.table("match_logs").insert({
            "event_name": evento,
            "battle_id": battle_id,
            "player_1": p1,
            "player_2": p2,
            "final_score": score_final,
            "detailed_log": log_str
        }).execute()
    except Exception as e:
        st.error(f"⚠️ Erro ao arquivar log na base de dados: {e}")

# ==========================================
# INTERFACE
# ==========================================
# Criar 4 abas (Aba extra para Exportar os Logs)
tabs = st.tabs(["🤺 Emparceiramento", "⚔️ Combate em Curso", "📋 Histórico Temporário", "📥 Exportar MatchLogs"])

# --- TAB 1: CRIAR O MATCH ---
with tabs[0]:
    st.subheader("Configurar Novo Combate")
    db = load_db()
    
    eventos_disponiveis = list(set([data.get("Event", "") for battle_id, data in db.items() if "Event" in data]))
    
    if not eventos_disponiveis:
        st.warning("Não há batalhas pendentes no JSON. (Usa o gerador de brackets do Challonge se aplicável)")
    else:
        evento_selecionado = st.selectbox("Torneio Ativo:", eventos_disponiveis)
        
        batalhas_torneio = {k: v for k, v in db.items() if v.get("Event") == evento_selecionado and v.get("Status") == "Pendente"}
        
        if not batalhas_torneio:
            st.success("Não existem batalhas pendentes neste torneio!")
        else:
            opcoes = [f"{k} - {v['Player 1']} vs {v['Player 2']}" for k, v in batalhas_torneio.items()]
            batalha_escolhida = st.selectbox("Escolher Combate:", opcoes)
            
            if st.button("Iniciar Batalha Oficial 🚀", use_container_width=True, type="primary"):
                b_id = batalha_escolhida.split(" - ")[0]
                b_data = db[b_id]
                
                # INICIALIZAR ESTADO
                st.session_state.active_event = evento_selecionado
                st.session_state.battle_id = b_id
                st.session_state.p1_name = b_data["Player 1"]
                st.session_state.p2_name = b_data["Player 2"]
                st.session_state.p1_score = 0
                st.session_state.p2_score = 0
                st.session_state.match_log = []
                st.session_state.history = []
                if 'arquivado' in st.session_state:
                    del st.session_state.arquivado
                
                st.success(f"Combate Ativado! Muda para a aba 'Combate em Curso'.")

# --- TAB 2: PAINEL DE COMBATE ---
with tabs[1]:
    if 'battle_id' not in st.session_state:
        st.info("Nenhuma batalha ativa no momento. Inicia um combate na aba anterior.")
    else:
        @st.fragment
        def painel_de_combate_dinamico():
            # Apanha Sugestões de Combos do Supabase
            @st.cache_data(ttl=60)
            def get_combo_from_db(event_name, player_name):
                try:
                    res = supabase.table("tournament_registrations").select("*, bladers!inner(alias), tournaments!inner(name)").eq("tournaments.name", event_name).eq("bladers.alias", player_name).execute()
                    if res.data:
                        reg = res.data[0]
                        combos = [reg.get(f"combo_{i}") for i in range(1, 5) if reg.get(f"combo_{i}")]
                        return " / ".join(combos) if combos else ""
                except:
                    pass
                return ""

            p1_combo_sug = get_combo_from_db(st.session_state.active_event, st.session_state.p1_name)
            p2_combo_sug = get_combo_from_db(st.session_state.active_event, st.session_state.p2_name)

            col_p1, col_p2 = st.columns(2)
            c_p1 = col_p1.text_input(f"Combo de {st.session_state.p1_name} (Opcional):", value=p1_combo_sug, key="combo_p1_input")
            c_p2 = col_p2.text_input(f"Combo de {st.session_state.p2_name} (Opcional):", value=p2_combo_sug, key="combo_p2_input")
            
            st.markdown(f"<h2 style='text-align: center; margin-bottom: 0;'>{st.session_state.p1_name} 🆚 {st.session_state.p2_name}</h2>", unsafe_allow_html=True)
            
            c_score1, c_score2 = st.columns(2)
            c_score1.markdown(f"<div style='text-align:center; background-color:#ff4b4b; padding:15px; border-radius:10px; color:white;'><h1 style='font-size:70px; margin:0;'>{st.session_state.p1_score}</h1></div>", unsafe_allow_html=True)
            c_score2.markdown(f"<div style='text-align:center; background-color:#1f77b4; padding:15px; border-radius:10px; color:white;'><h1 style='font-size:70px; margin:0;'>{st.session_state.p2_score}</h1></div>", unsafe_allow_html=True)
            
            st.write("")
            
            def register_action(player, action, points):
                st.session_state.history.append({
                    "p1": st.session_state.p1_score,
                    "p2": st.session_state.p2_score,
                    "log_len": len(st.session_state.match_log)
                })
                
                if player == 1:
                    st.session_state.p1_score += points
                    player_name = st.session_state.p1_name
                    combo_used = c_p1 if c_p1 else "Desconhecido"
                    combo_adv = c_p2 if c_p2 else "Desconhecido"
                else:
                    st.session_state.p2_score += points
                    player_name = st.session_state.p2_name
                    combo_used = c_p2 if c_p2 else "Desconhecido"
                    combo_adv = c_p1 if c_p1 else "Desconhecido"
                    
                log_entry = f"⚔️ {player_name} ({combo_used}) venceu por {action} (+{points}) contra {combo_adv}"
                st.session_state.match_log.append(log_entry)

            def undo_last_action():
                if st.session_state.history:
                    last_state = st.session_state.history.pop()
                    st.session_state.p1_score = last_state["p1"]
                    st.session_state.p2_score = last_state["p2"]
                    st.session_state.match_log = st.session_state.match_log[:last_state["log_len"]]

            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("🌪️ Spin (+1)", key="p1_s", use_container_width=True): register_action(1, "Spin Finish", 1); st.rerun()
                if st.button("💥 Over (+2)", key="p1_o", use_container_width=True): register_action(1, "Over Finish", 2); st.rerun()
                if st.button("💣 Burst (+2)", key="p1_b", use_container_width=True): register_action(1, "Burst Finish", 2); st.rerun()
                if st.button("⚡ Xtreme (+3)", key="p1_x", use_container_width=True): register_action(1, "Xtreme Finish", 3); st.rerun()
                
            with col_b2:
                if st.button("🌪️ Spin (+1)", key="p2_s", use_container_width=True): register_action(2, "Spin Finish", 1); st.rerun()
                if st.button("💥 Over (+2)", key="p2_o", use_container_width=True): register_action(2, "Over Finish", 2); st.rerun()
                if st.button("💣 Burst (+2)", key="p2_b", use_container_width=True): register_action(2, "Burst Finish", 2); st.rerun()
                if st.button("⚡ Xtreme (+3)", key="p2_x", use_container_width=True): register_action(2, "Xtreme Finish", 3); st.rerun()

            st.write("")
            col_undo, col_new = st.columns(2)
            
            with col_undo:
                if st.session_state.history:
                    if st.button("↩️ Desfazer Último Ponto", use_container_width=True):
                        if 'arquivado' in st.session_state: del st.session_state['arquivado']
                        undo_last_action()
                        st.rerun()
                    
            with col_new:
                if st.button("✅ Confirmar o Resultado", use_container_width=True, type="primary"):
                    if 'arquivado' not in st.session_state:
                        # 1. Grava no Supabase (Estrutura MatchLogs)
                        archive_match_to_supabase(
                            st.session_state.active_event, 
                            st.session_state.battle_id, 
                            st.session_state.p1_name, 
                            st.session_state.p2_name, 
                            st.session_state.p1_score, 
                            st.session_state.p2_score, 
                            st.session_state.match_log
                        )
                        st.session_state.arquivado = True
                        
                        # 2. Marca no JSON temporário como terminado
                        db_local = load_db()
                        if st.session_state.battle_id in db_local:
                            db_local[st.session_state.battle_id]["Status"] = "Terminada" 
                            save_db(db_local)

                    # 3. LIMPEZA CIRÚRGICA (Não usa .clear() para não apagar o login)
                    keys_to_clear = ['active_event', 'battle_id', 'p1_name', 'p2_name', 'p1_score', 'p2_score', 'match_log', 'history', 'arquivado']
                    for k in keys_to_clear:
                        if k in st.session_state:
                            del st.session_state[k]
                            
                    st.rerun()

        painel_de_combate_dinamico()

# --- TAB 3: RESULTADOS E HISTÓRICO ---
with tabs[2]:
    st.subheader("Resumo do JSON (Combates Terminados)")
    db = load_db()
    terminadas = {k: v for k, v in db.items() if v.get("Status") == "Terminada"}
    
    if not terminadas:
        st.info("Ainda não finalizaste nenhum combate nesta sessão.")
    else:
        for k, v in terminadas.items():
            st.markdown(f"✅ **{v['Event']}** | {v['Player 1']} vs {v['Player 2']}")

# --- TAB 4: MÓDULO EXPORTADOR DE ZERO LOGS ---
with tabs[3]:
    st.subheader("📥 Extração Oficial (Logs)")
    st.markdown("Descarrega todos os detalhes e sequências dos combates gravados na Base de Dados.")
    
    # Busca a tabela mágica que criámos no Supabase
    @st.cache_data(ttl=30)
    def fetch_all_match_logs():
        try:
            res = supabase.table("match_logs").select("*").order("created_at", desc=True).execute()
            return res.data
        except:
            return []
            
    logs_data = fetch_all_match_logs()
    
    if not logs_data:
        st.info("Ainda não existem registos de MatchLogs na Base de Dados do Supabase.")
    else:
        df_logs = pd.DataFrame(logs_data)
        
        # Filtros de Evento
        eventos_unicos = df_logs['event_name'].dropna().unique().tolist()
        eventos_disponiveis = ["Todos os Torneios"] + sorted(eventos_unicos)
        
        filtro_evento = st.selectbox("Qual o torneio que queres extrair?", eventos_disponiveis)
        
        if filtro_evento != "Todos os Torneios":
            df_logs = df_logs[df_logs['event_name'] == filtro_evento]
            
        # Reordenar e renomear colunas para bater EXATAMENTE com o teu Excel antigo
        df_export = df_logs[['created_at', 'event_name', 'battle_id', 'player_1', 'player_2', 'final_score', 'detailed_log']]
        df_export.columns = ['Data_Hora', 'Evento', 'Battle_ID', 'Jogador_1', 'Jogador_2', 'Score_Final', 'Log_Detalhado']
        
        # Formatar a data para ficar limpa
        df_export['Data_Hora'] = pd.to_datetime(df_export['Data_Hora']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        st.dataframe(df_export, use_container_width=True, hide_index=True)
        
        # Gerar Ficheiro CSV para Download
        csv_bytes = df_export.to_csv(index=False).encode('utf-8-sig')
        nome_ficheiro = f"MatchLogs_{filtro_evento.replace(' ', '_')}.csv" if filtro_evento != "Todos os Torneios" else "MatchLogs_Todos_Os_Torneios.csv"
        
        st.download_button(
            label=f"📥 Descarregar Excel (CSV) - {filtro_evento}",
            data=csv_bytes,
            file_name=nome_ficheiro,
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
