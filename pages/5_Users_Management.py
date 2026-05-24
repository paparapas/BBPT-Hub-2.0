import streamlit as st
import pandas as pd
import hashlib
import os
import base64
from streamlit_cookies_controller import CookieController
from db_connection import supabase

st.set_page_config(page_title="Gestão de Utilizadores", page_icon="👥", layout="wide")

# --- SINALIZAR COMPATIBILIDADE COM A SIDEBAR GLOBAL ---
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# ==========================================
# GESTÃO DA SIDEBAR E SEGURANÇA DE COOKIES
# ==========================================
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
        st.markdown(
            f"""
            <div style="display: flex; align-items: center; margin-bottom: 20px;">
                <img src="data:image/png;base64,{encoded_logo}" width="150" style="margin-right: 10px;">
                <h1 style="margin: 0; padding: 0; font-size: 1.8rem;"></h1>
            </div>
            """, unsafe_allow_html=True
        )
    st.divider()
    
    if st.session_state.user_role:
        st.success(f"🔓 Modo {st.session_state.user_role.upper()} Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            # 1. Limpa a memória RAM do Streamlit
            st.session_state.user_role = None
            if "finance_auth" in st.session_state:
                st.session_state.finance_auth = False
            
            # 2. Verifica se os cookies existem ANTES de os tentar apagar
            if controller.get('user_role') is not None:
                controller.remove('user_role')
                
            if controller.get('finance_auth') is not None:
                controller.remove('finance_auth')
                
            # 3. Recarrega a página
            st.rerun()

# --- BLOQUEIO ABSOLUTO DE ACESSO AO ECRÃ ---
if st.session_state.user_role != "owner":
    st.warning("🔒 Acesso Exclusivo ao Owner do Ecossistema BBPT.")
    owner_pwd_input = st.text_input("Introduz a Password de Owner para prosseguir:", type="password")
    if st.button("Autenticar Owner 🔑", type="primary"):
        if owner_pwd_input.strip() == st.secrets["PASSWORDS"]["OWNER"]:
            st.session_state.user_role = "owner"
            controller.set('user_role', 'owner', max_age=43200)
            st.success("Autenticado!")
            st.rerun()
        else:
            st.error("Password de Owner incorreta!")
    st.stop()

# ==========================================
# CÓDIGO OPERACIONAL DE GESTÃO DE BLADERS
# ==========================================
st.title("👥 Painel de Controlo de Utilizadores (Owner)")
st.markdown("Cria novas contas de Bladers ou redefine credenciais de acesso em tempo real.")

@st.cache_data(ttl=5)
def get_all_bladers():
    res = supabase.table("bladers").select("id, alias").order("alias").execute()
    return res.data

bladers_list = get_all_bladers()

tab1, tab2 = st.tabs(["🔄 Redefinir Password de Blader", "➕ Criar Novo Blader"])

# --- TAB 1: REDEFINIR PASSWORD ---
with tab1:
    st.subheader("Alterar Password Existente")
    if bladers_list:
        selected_blader = st.selectbox("Seleciona o Blader:", [b["alias"] for b in bladers_list])
        new_pwd = st.text_input("Nova Password:", type="password", key="pwd_reset")
        
        if st.button("Confirmar Nova Password 💾", type="primary"):
            if new_pwd.strip():
                new_hash = hashlib.md5(new_pwd.encode()).hexdigest()
                try:
                    supabase.table("bladers").update({"password_hash": new_hash}).eq("alias", selected_blader).execute()
                    st.success(f"✅ A password de **{selected_blader}** foi redefinida com sucesso com criptografia MD5.")
                except Exception as e:
                    st.error(f"Erro ao atualizar na base de dados: {e}")
            else:
                st.warning("A password não pode estar vazia!")
    else:
        st.info("Nenhum Blader encontrado na base de dados.")

# --- TAB 2: CRIAR NOVO UTILIZADOR ---
with tab2:
    st.subheader("Registar Novo Blader no Sistema")
    new_alias = st.text_input("Nickname do Blader (Único):", key="new_alias_input")
    new_user_pwd = st.text_input("Password Inicial:", type="password", key="new_pwd_input")
    
    if st.button("Criar Conta de Blader 🚀"):
        if new_alias.strip() and new_user_pwd.strip():
            # Verificar se o nome já existe
            duplicado = any(b["alias"].lower() == new_alias.strip().lower() for b in bladers_list)
            if duplicado:
                st.error("❌ Esse Nickname já está registado na base de dados!")
            else:
                user_hash = hashlib.md5(new_user_pwd.encode()).hexdigest()
                try:
                    supabase.table("bladers").insert({
                        "alias": new_alias.strip(),
                        "password_hash": user_hash
                    }).execute()
                    st.success(f"🎉 **{new_alias.strip()}** foi registado com sucesso! Já pode aceder ao Deck Builder.")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao inserir na base de dados: {e}")
        else:
            st.warning("Preenche o Nickname e a Password!")