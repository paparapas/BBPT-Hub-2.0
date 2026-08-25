import streamlit as st
import pandas as pd
import hashlib
import os
import base64
from db_connection import supabase

st.set_page_config(page_title="Gestão de Utilizadores", page_icon="logo.png", layout="wide")

# ==========================================
# 🔐 AUTENTICAÇÃO ESTÁTICA & PERSISTENTE
# ==========================================
if "is_admin" not in st.session_state: st.session_state.is_admin = False
secret_admin_pass = st.secrets.get("PASSWORDS", {}).get("ADMIN", "bbpt-paparapas")

if st.query_params.get("admin") == secret_admin_pass:
    st.session_state.is_admin = True

if st.session_state.is_admin and st.query_params.get("admin") != secret_admin_pass:
    st.query_params["admin"] = secret_admin_pass
    
# Gestão visual da Sidebar
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
            </div>
            """, unsafe_allow_html=True
        )
    st.divider()
    
    if st.session_state.is_admin:
        st.success("🔓 Modo ADMIN Ativo")
    else:
        st.info("Acesso Restrito")

# --- BLOQUEIO ABSOLUTO DE ACESSO AO ECRÃ ---
if not st.session_state.is_admin:
    st.warning("🔒 Acesso Exclusivo à Administração BBPT.")
    st.info("Deves aceder a esta página através do teu link de Admin seguro.")
    st.stop()

# ==========================================
# CÓDIGO OPERACIONAL DE GESTÃO DE BLADERS
# ==========================================
st.title("👥 Painel de Controlo de Utilizadores")
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
