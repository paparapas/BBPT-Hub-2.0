import streamlit as st
from db_connection import supabase

st.set_page_config(page_title="Gestão Inventário", page_icon="logo.png")

# ==========================================
# 🔐 AUTENTICAÇÃO ESTÁTICA & PERSISTENTE
# ==========================================
if "is_admin" not in st.session_state: st.session_state.is_admin = False
secret_admin_pass = st.secrets.get("PASSWORDS", {}).get("ADMIN", "bbpt-paparapas")

if st.query_params.get("admin") == secret_admin_pass:
    st.session_state.is_admin = True

if st.session_state.is_admin and st.query_params.get("admin") != secret_admin_pass:
    st.query_params["admin"] = secret_admin_pass

if not st.session_state.is_admin:
    st.warning("🔒 Acesso Exclusivo à Administração BBPT.")
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
        sys = st.selectbox("Sistema:", ["BX", "UX", "CX", "CX Expanded", "UX Expanded", ""])
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
