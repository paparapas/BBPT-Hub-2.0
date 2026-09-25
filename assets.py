import os
import base64
import streamlit as st

# ==========================================
# 🖼️ IMAGENS RÁPIDAS (Static Serving)
# ==========================================
# Se a imagem existir na pasta "static/", o telemóvel descarrega-a UMA vez e guarda-a em cache.
# Se não existir, volta ao método antigo (base64 dentro da página), por isso nada parte.
STATIC_DIR = "static"
_MIMES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif"}


@st.cache_data(show_spinner=False)
def _b64(path, mtime):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def img_src(static_name, local_fallback=None):
    """Devolve o valor para <img src="...">.
    static_name: nome do ficheiro dentro de static/
    local_fallback: nome do ficheiro antigo na raiz (se for diferente)."""
    if os.path.exists(os.path.join(STATIC_DIR, static_name)):
        return f"app/static/{static_name}"
    for name in (local_fallback, static_name):
        if not name: continue
        for path in (name, f"../{name}"):
            if os.path.exists(path):
                mime = _MIMES.get(os.path.splitext(path)[1].lower(), "image/png")
                return f"data:{mime};base64,{_b64(path, os.path.getmtime(path))}"
    return ""
