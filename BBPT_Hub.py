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

# ==========================================
# RENDERIZAÇÃO DOS MÓDULOS
# ==========================================
if page is None:
    st.title("🏆 BBPT Hub")
    st.info("A Nova Temporada está a chegar. Explora os menus na barra lateral e superior!")
