import streamlit as st
import base64
import os
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
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-bottom:20px;'></div>", unsafe_allow_html=True)
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
                    st.session_state.is_admin = True
                    st.session_state.auth_token = pwd_input.strip()
                    st.query_params["admin"] = pwd_input.strip()
                    st.rerun()
                else: 
                    st.error("Password Incorreta!")

# ==========================================
# PAINEL DA NOVA TEMPORADA (HOMEPAGE)
# ==========================================

# 1. Função auxiliar para carregar imagens em Base64 (à prova de falhas)
def get_image_b64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f: return base64.b64encode(f.read()).decode()
    for ext in ['.jpg', '.png', '.jpeg', '.JPG', '.PNG']:
        if os.path.exists(filepath + ext):
            with open(filepath + ext, "rb") as f: return base64.b64encode(f.read()).decode()
    # Pixel transparente de fallback caso a imagem falhe
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# Carregar as imagens baseadas nos nomes exatos
logo_b64 = get_image_b64("logo.png")
foto1_b64 = get_image_b64("parceiro_beybladenexus_oficial.png")
foto2_b64 = get_image_b64("foto2")

fenix_b64 = get_image_b64("fenix.png")
deck_b64 = get_image_b64("deck_build_image")
bp_b64 = get_image_b64("BBPT_BP_Format.PNG")

# 2. RENDERIZAR O "HERO BANNER" (Inspirado na Pokebox)
st.markdown(f"""
<style>
.hero-container {{
    display: flex; flex-direction: row; gap: 15px; align-items: stretch; margin-bottom: 40px; height: 350px;
}}
.hero-side {{
    flex: 1; border-radius: 12px; overflow: hidden; box-shadow: 0 6px 12px rgba(0,0,0,0.3); border: 2px solid rgba(255,255,255,0.05);
}}
.hero-side img {{
    width: 100%; height: 100%; object-fit: cover;
}}
.hero-center {{
    flex: 1.8; background: linear-gradient(135deg, #161925 0%, #1f2333 100%); border-radius: 12px; padding: 20px; 
    text-align: center; box-shadow: 0 6px 12px rgba(0,0,0,0.3); display: flex; flex-direction: column; 
    justify-content: center; align-items: center; border: 2px solid rgba(255,255,255,0.05);
}}
.hero-title {{
    color: #ffffff; margin: 0 0 15px 0; font-size: 2.2rem; font-weight: 900; letter-spacing: 2px; text-transform: uppercase;
}}
.hero-logo {{
    max-width: 80%; max-height: 200px; object-fit: contain; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.4));
}}

/* Ad Banners Hover Effect */
.ad-card {{
    border-radius: 12px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.3); transition: transform 0.2s ease, box-shadow 0.2s ease;
    background-color: #1f2333; cursor: pointer; text-decoration: none; display: block; border: 1px solid rgba(255,255,255,0.05);
}}
.ad-card:hover {{
    transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.5); text-decoration: none;
}}
.ad-img {{
    width: 100%; height: 200px; object-fit: cover; border-bottom: 3px solid #7a161c;
}}
.ad-title {{
    color: white; text-align: center; padding: 15px 10px; font-weight: 700; font-size: 1.1rem; text-decoration: none;
}}
</style>

<div class="hero-container">
    <div class="hero-side"><img src="data:image/png;base64,{foto1_b64}" alt="Parceiro Nexus"></div>
    <div class="hero-center">
        <h2 class="hero-title">BEM-VINDOS AO HUB</h2>
        <img class="hero-logo" src="data:image/png;base64,{logo_b64}" alt="BBPT Logo">
    </div>
    <div class="hero-side"><img src="data:image/jpeg;base64,{foto2_b64}" alt="BBPT Foto 2"></div>
</div>
""", unsafe_allow_html=True)

# 3. RENDERIZAR OS "ANÚNCIOS" INTERATIVOS (Links por imagem)
st.subheader("🎯 Acesso Rápido")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    <a href="Liga_Scoreboard" target="_self" class="ad-card">
        <img class="ad-img" src="data:image/png;base64,{fenix_b64}">
        <div class="ad-title">🏆 Scoreboard Liga Fénix</div>
    </a>
    """, unsafe_allow_html=True)
    
with col2:
    st.markdown(f"""
    <a href="Deck_Builder" target="_self" class="ad-card">
        <img class="ad-img" src="data:image/png;base64,{deck_b64}" style="object-position: top;">
        <div class="ad-title">⚙️ Construir o teu Deck</div>
    </a>
    """, unsafe_allow_html=True)
    
with col3:
    st.markdown(f"""
    <a href="Documentos" target="_self" class="ad-card">
        <img class="ad-img" src="data:image/png;base64,{bp_b64}" style="object-fit: contain; background: white;">
        <div class="ad-title">📋 Lista BP & Calendário</div>
    </a>
    """, unsafe_allow_html=True)
