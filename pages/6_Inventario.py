import streamlit as st
from streamlit_cookies_controller import CookieController
from db_connection import supabase

# Configuração da Página
st.set_page_config(page_title="Gestão Inventário", page_icon="logo.png")

# INICIALIZAÇÃO DO CONTROLLER (Fora de qualquer função cacheada para evitar o Warning)
controller = CookieController()

# ==========================================
# GESTÃO DE ESTADO E AUTENTICAÇÃO
# ==========================================
if "user_role" not in st.session_state:
    st.session_state.user_role = controller.get('user_role')

# ==========================================
# 🔐 VERIFICAÇÃO DE AUTENTICAÇÃO (OWNER ONLY)
# ==========================================
if st.session_state.user_role != "owner":
    st.warning("🔒 Acesso Exclusivo ao Owner do Ecossistema BBPT.")
    
    owner_pwd_input = st.text_input("Introduz a Password de Owner:", type="password")
    
    if st.button("Autenticar Owner 🔑", type="primary"):
        # Lemos a password de forma segura dos secrets
        pwd_owner = st.secrets.get("PASSWORDS", {}).get("OWNER", "bbpt-owner123")
        
        if owner_pwd_input.strip() == pwd_owner:
            st.session_state.user_role = "owner"
            try:
                controller.set('user_role', 'owner', max_age=43200)
            except:
                pass
            st.success("Autenticado!")
            st.rerun()
        else:
            st.error("Password de Owner incorreta!")
    st.stop() 

# ==========================================
# 🧩 GESTÃO DE INVENTÁRIO (SÓ CHEGA AQUI SE FOR OWNER)
# ==========================================
st.title("🧩 Registar Nova Peça")
st.markdown("Bem-vindo, Owner. Adiciona novas peças diretamente ao Supabase.")

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