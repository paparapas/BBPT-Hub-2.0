import streamlit as st
import base64
import os
from db_connection import supabase
from streamlit_javascript import st_javascript

# 1. Configuração da Página
st.set_page_config(page_title="BBPT Hub", page_icon="logo.png", layout="wide")

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
# PAINEL DA NOVA TEMPORADA (HOMEPAGE)
# ==========================================

def get_image_b64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as f: return base64.b64encode(f.read()).decode()
    for ext in ['.jpg', '.png', '.jpeg', '.JPG', '.PNG']:
        if os.path.exists(filepath + ext):
            with open(filepath + ext, "rb") as f: return base64.b64encode(f.read()).decode()
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

# DETEÇÃO DE TEMA (CLARO/ESCURO)
try:
    from streamlit_javascript import st_javascript
    theme = st_javascript("""window.getComputedStyle(window.parent.document.getElementsByTagName("body")[0]).getPropertyValue("color-scheme")""")
except Exception:
    theme = "dark" # Default fallback

if theme == "light":
    logo_b64 = get_image_b64("logo.png")
else:
    logo_b64 = get_image_b64("logodark.png") if os.path.exists("logodark.png") else get_image_b64("logo.png")

# VARIÁVEIS DAS IMAGENS
nexus_b64 = get_image_b64("parceiro_beybladenexus_oficial.png")
foto2_b64 = get_image_b64("foto2")

fenix_b64 = get_image_b64("fenix.png")
deck_b64 = get_image_b64("deck_build_image")
bp_b64 = get_image_b64("BBPT_BP_Format.PNG")

# RENDERIZAR O HTML E CSS RESPONSIVO
html_content = f"""
<style>
:root {{
    --card-bg: var(--secondary-background-color);
    --border-col: rgba(122, 22, 28, 0.4);
}}

/* === HERO BANNER === */
.hero-container {{
    display: flex; flex-direction: row; gap: 15px; align-items: stretch; margin-bottom: 40px; min-height: 350px;
}}
.hero-side {{
    flex: 1; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border: none;
}}
.hero-side-left {{
    background: white; display: flex; justify-content: center; align-items: center; padding: 20px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.hero-side-left:hover {{
    transform: translateY(-3px); box-shadow: 0 6px 14px rgba(0,0,0,0.3);
}}
.hero-side-left img {{
    max-width: 100%; max-height: 100%; object-fit: contain;
}}
.hero-side-right img {{
    width: 100%; height: 100%; object-fit: cover;
}}
.hero-center {{
    flex: 1.8; background-color: var(--background-color); border-radius: 12px; padding: 20px; 
    text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2); display: flex; flex-direction: column; 
    justify-content: center; align-items: center; border: none; position: relative;
}}
.hero-title {{
    color: var(--text-color); margin: 0 0 5px 0; font-size: 2rem; font-weight: 900; letter-spacing: 1px; text-transform: uppercase;
}}
.hero-hub-text {{
    color: var(--text-color); margin: 5px 0 0 0; font-size: 2.5rem; font-weight: 900; letter-spacing: 4px; text-transform: uppercase;
}}
.hero-logo {{
    max-width: 85%; max-height: 180px; object-fit: contain; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.2));
}}

/* === AD GRID (ACESSO RÁPIDO) === */
.ad-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 15px;
}}
.ad-card {{
    border-radius: 12px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.15); 
    transition: transform 0.2s ease, box-shadow 0.2s ease; background-color: var(--card-bg); 
    cursor: pointer; text-decoration: none; display: flex; flex-direction: column; border: none;
}}
.ad-card:hover {{
    transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.3); text-decoration: none;
}}
.ad-img {{
    width: 100%; height: 180px; object-fit: cover; border-bottom: none;
}}
.ad-img.contain-bg-white {{
    object-fit: contain; background-color: white;
}}
.ad-img.pos-top {{
    object-position: top;
}}
.ad-title {{
    color: var(--text-color); text-align: center; padding: 15px 10px; font-weight: 700; 
    font-size: 1.1rem; text-decoration: none; flex-grow: 1; display: flex; align-items: center; justify-content: center;
}}

/* === MOBILE RESPONSIVENESS === */
@media (max-width: 800px) {{
    .hero-container {{ flex-direction: column; height: auto; }}
    .hero-side, .hero-center {{ min-height: 200px; width: 100%; }}
    .ad-grid {{ grid-template-columns: 1fr; }}
    .hero-title {{ font-size: 1.5rem; }}
    .hero-hub-text {{ font-size: 2rem; }}
}}
</style>

<div class="hero-container">
<!-- Lado Esquerdo: Logo da Beyblade Nexus com link interativo -->
<a href="https://www.beybladenexus.com/" target="_blank" class="hero-side hero-side-left" title="Visitar Beyblade Nexus">
<img src="data:image/png;base64,{nexus_b64}" alt="Parceiro Nexus">
</a>

<!-- Centro: Jogo de palavras com o Logo do Hub -->
<div class="hero-center">
<h2 class="hero-title">BEM-VINDOS AO</h2>
<img class="hero-logo" src="data:image/png;base64,{logo_b64}" alt="BBPT Logo">
<h2 class="hero-hub-text">HUB</h2>
</div>

<!-- Lado Direito: Foto 2 -->
<div class="hero-side hero-side-right">
<img src="data:image/jpeg;base64,{foto2_b64}" alt="BBPT Foto 2">
</div>
</div>

<h3 style="margin-top: 30px; margin-bottom: 10px;">🎯 Acesso Rápido</h3>

<div class="ad-grid">
<a href="Liga_Scoreboard" target="_self" class="ad-card">
<img class="ad-img contain-bg-white" src="data:image/png;base64,{fenix_b64}">
<div class="ad-title">Scoreboard Liga Fénix</div>
</a>
<a href="Deck_Builder" target="_self" class="ad-card">
<img class="ad-img pos-top" src="data:image/png;base64,{deck_b64}">
<div class="ad-title">Construir o teu Deck</div>
</a>
<a href="Documentos" target="_self" class="ad-card">
<img class="ad-img contain-bg-white" src="data:image/png;base64,{bp_b64}">
<div class="ad-title">Lista BP & Calendário</div>
</a>
</div>
"""

st.markdown(html_content, unsafe_allow_html=True)
