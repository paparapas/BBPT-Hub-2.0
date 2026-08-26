import streamlit as st
from db_connection import supabase

st.set_page_config(page_title="Gestão Inventário", page_icon="logo.png")

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
# 🔐 VERIFICAÇÃO DE AUTENTICAÇÃO
# ==========================================
if not st.session_state.is_admin:
    st.warning("🔒 Acesso Exclusivo à Administração BBPT.")
    
    # Mantivemos a caixa estética para caso acedam sem o link
    admin_pwd_input = st.text_input("Introduz a Password de Admin:", type="password")
    
    if st.button("Autenticar 🔑", type="primary"):
        if admin_pwd_input.strip() == secret_admin_pass:
            st.session_state.is_admin = True
            st.query_params["admin"] = secret_admin_pass
            st.success("Autenticado!")
            st.rerun()
        else:
            st.error("Password incorreta!")
    st.stop() 

# ==========================================
# 🧩 GESTÃO DE INVENTÁRIO
# ==========================================
st.title("🧩 Registar Nova Peça")
st.markdown("Bem-vindo, Admin. Adiciona novas peças diretamente ao Supabase.")

with st.form("nova_peca", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        nome = st.text_input("Nome da Peça:")
        ptype = st.selectbox("Tipo:", ["Blade", "Ratchet", "Bit", "Lock Chip", "Assist Blade", "Metal Blade", "Over Blade"])
        spin = st.selectbox("Rotação:", ["Right", "Left", "Dual"])
    
    with col2:
        sys = st.selectbox("Sistema:", ["BX", "UX", "CX", "CX Expanded", "UX Expanded", "BX Expanded", ""])
        img_url = st.text_input("URL da Imagem (ImgBB - Link Direto):")
    
    submit = st.form_submit_button("Gravar no Supabase 🚀")
    
    if submit:
        if not nome or not img_url:
            st.error("Preenche o Nome e o URL da imagem!")
        else:
            try:
                supabase.table("parts").insert({
                    "name": nome,
                    "part_type": ptype,
                    "system_type": sys,
                    "image_url": img_url,
                    "spin_direction": spin
                }).execute()
                
                st.success(f"✅ Peça '{nome}' registada com sucesso na nuvem!")
            except Exception as e:
                st.error(f"Erro ao comunicar com Supabase: {e}")
