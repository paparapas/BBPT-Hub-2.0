import streamlit as st
import base64
import os
from assets import img_src

st.set_page_config(page_title="Contactos & Organização", page_icon="logo.png", layout="wide")

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

# ==========================================
# GESTÃO GLOBAL DA SIDEBAR
# ==========================================
logo_src = img_src("logo.png")
if logo_src:
    with st.sidebar:
        st.markdown(f"<div><img src='{logo_src}' width='150' style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

if st.session_state.is_admin: st.sidebar.success("🔓 ADMIN")
elif st.session_state.is_judge: st.sidebar.success("⚖️ JUIZ")
else: st.sidebar.info("👤 PLAYER")

def load_communications(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f: return f.read().strip()
    return None

# ==========================================
# INTERFACE DOS CONTACTOS
# ==========================================
st.title("📞 Contactos & Redes Sociais")
st.markdown("Junta-te à comunidade oficial BBPT!")
st.write("")

def render_social_button(link, img_file, text):
    src = img_src(img_file)
    img_tag = ""
    if src:
        img_tag = f"<img src='{src}' style='height: 22px; margin-right: 10px; object-fit: contain;'>"
        
    return f"""
    <a href="{link}" target="_blank" style="
        display: flex; align-items: center; justify-content: center;
        background-color: #1f2333; color: white; text-decoration: none;
        padding: 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.1);
        font-size: 16px; font-weight: 600; width: 100%; box-sizing: border-box;
        box-shadow: 0 2px 4px rgba(0,0,0,0.2);
    ">
        {img_tag}{text}
    </a>
    """

c1, c2, c3, c4 = st.columns(4) 
with c1: st.markdown(render_social_button("https://www.instagram.com/beyblade_pt", "instagram.png", "Instagram"), unsafe_allow_html=True)
with c2: st.markdown(render_social_button("https://chat.whatsapp.com/GCLf0RjTFjFHzc1yK2VjPo", "whatsapp.png", "WhatsApp"), unsafe_allow_html=True)
with c3: st.markdown(render_social_button("https://www.youtube.com/@BeybladePortugal", "youtube.png", "YouTube"), unsafe_allow_html=True)
with c4: st.markdown(render_social_button("https://discord.com/invite/KssWPXxFnq", "discord.png", "Discord"), unsafe_allow_html=True)

st.divider()

st.subheader("👥 Quadro da Organização e Gestão")
conteudo_org = load_communications("organizacao.txt")
if conteudo_org:
    for seccao in conteudo_org.split("==="):
        if seccao.strip():
            with st.container(border=True): st.markdown(seccao.strip())