import streamlit as st
import pandas as pd
import hashlib
import os
import base64
from db_connection import supabase

st.set_page_config(page_title="Gestão de Utilizadores", page_icon="logo.png", layout="wide")

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

# (No Users_Management podes manter a sidebar se quiseres, no Inventário não havia sidebar)

# --- BLOQUEIO ABSOLUTO (APENAS ADMIN ENTRA, JUÍZES SÃO BLOQUEADOS) ---
if not st.session_state.is_admin:
    st.warning("🔒 Acesso Exclusivo à Administração BBPT.")
    if st.session_state.is_judge:
        st.info("⚖️ Como Juiz, tens acesso ao Battle Logger. Esta página está restrita.")
    else:
        admin_pwd_input = st.text_input("Chave de Acesso Admin:", type="password")
        if st.button("Autenticar 🔑", type="primary"):
            if admin_pwd_input.strip() in admin_passwords:
                st.session_state.is_admin = True
                st.session_state.auth_token = admin_pwd_input.strip()
                st.query_params["admin"] = admin_pwd_input.strip()
                st.rerun()
            else:
                st.error("Chave incorreta ou sem privilégios de Admin!")
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
