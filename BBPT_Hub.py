import streamlit as st
import base64
import os
from db_connection import supabase
from streamlit_javascript import st_javascript

# 1. Configuração da Página
st.set_page_config(page_title="BBPT Hub", page_icon="logo.png", layout="wide")

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

# FOTOS LATERAIS E PARCEIRO
foto1_b64 = get_image_b64("foto1")
foto2_b64 = get_image_b64("foto2")
nexus_b64 = get_image_b64("parceiro_beybladenexus_oficial.png")

# ÍCONES DE ACESSO RÁPIDO
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
    flex: 1; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 10px rgba(0,0,0,0.2); border: 1px solid var(--card-bg);
}}
.hero-side img {{
    width: 100%; height: 100%; object-fit: cover;
}}
.hero-center {{
    flex: 1.8; background-color: var(--background-color); border-radius: 12px; padding: 20px; 
    text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.2); display: flex; flex-direction: column; 
    justify-content: center; align-items: center; border: 2px solid var(--border-col); position: relative;
}}
.hero-title {{
    color: var(--text-color); margin: 0 0 5px 0; font-size: 2rem; font-weight: 900; letter-spacing: 1px; text-transform: uppercase;
}}
.hero-hub-text {{
    color: var(--text-color); margin: 5px 0 15px 0; font-size: 2.5rem; font-weight: 900; letter-spacing: 4px; text-transform: uppercase;
}}
.hero-logo {{
    max-width: 85%; max-height: 160px; object-fit: contain; filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.2));
}}
.nexus-logo {{
    max-width: 150px; max-height: 60px; object-fit: contain; margin-top: 10px; filter: drop-shadow(0px 2px 4px rgba(0,0,0,0.3));
}}

/* === AD GRID (ACESSO RÁPIDO) === */
.ad-grid {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-top: 15px;
}}
.ad-card {{
    border-radius: 12px; overflow: hidden; box-shadow: 0 4px 8px rgba(0,0,0,0.15); 
    transition: transform 0.2s ease, box-shadow 0.2s ease; background-color: var(--card-bg); 
    cursor: pointer; text-decoration: none; display: flex; flex-direction: column; border: 1px solid var(--border-col);
}}
.ad-card:hover {{
    transform: translateY(-5px); box-shadow: 0 8px 16px rgba(0,0,0,0.3); text-decoration: none;
}}
.ad-img {{
    width: 100%; height: 180px; object-fit: cover; border-bottom: 3px solid #7a161c;
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
<div class="hero-side">
<img src="data:image/jpeg;base64,{foto1_b64}" alt="BBPT Foto 1">
</div>
<div class="hero-center">
<h2 class="hero-title">BEM-VINDOS AO</h2>
<img class="hero-logo" src="data:image/png;base64,{logo_b64}" alt="BBPT Logo">
<h2 class="hero-hub-text">HUB</h2>
<img class="nexus-logo" src="data:image/png;base64,{nexus_b64}" alt="Parceiro Nexus">
</div>
<div class="hero-side">
<img src="data:image/jpeg;base64,{foto2_b64}" alt="BBPT Foto 2">
</div>
</div>

<h3 style="margin-top: 30px; margin-bottom: 10px;">🎯 Acesso Rápido</h3>

<div class="ad-grid">
<a href="Liga_Scoreboard" target="_self" class="ad-card">
<img class="ad-img contain-bg-white" src="data:image/png;base64,{fenix_b64}">
<div class="ad-title">🏆 Scoreboard Liga Fénix</div>
</a>
<a href="Deck_Builder" target="_self" class="ad-card">
<img class="ad-img pos-top" src="data:image/png;base64,{deck_b64}">
<div class="ad-title">⚙️ Construir o teu Deck</div>
</a>
<a href="Documentos" target="_self" class="ad-card">
<img class="ad-img contain-bg-white" src="data:image/png;base64,{bp_b64}">
<div class="ad-title">📋 Lista BP & Calendário</div>
</a>
</div>
"""

st.markdown(html_content, unsafe_allow_html=True)
