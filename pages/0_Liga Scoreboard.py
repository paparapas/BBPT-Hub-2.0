import streamlit as st
import pandas as pd
import json
import base64
import os
from assets import img_src

st.set_page_config(page_title="Liga Scoreboard", page_icon="logo.png", layout="wide")

# ==========================================
# GESTÃO GLOBAL DA SIDEBAR
# ==========================================
logo_src = img_src("logo.png")
if logo_src:
    with st.sidebar:
        st.markdown(f"<div><img src='{logo_src}' width='150' style='margin-bottom:20px;'></div>", unsafe_allow_html=True)

# ==========================================
# CARREGAR DADOS DA SEASON 2 (Isolado)
# ==========================================
@st.cache_data
def load_season2_data():
    try:
        with open('bbpt_master_db_season2.json', 'r', encoding='utf-8') as f: return json.load(f)
    except FileNotFoundError: return None

db = load_season2_data()

st.title("📈 Liga Scoreboard")
st.markdown("Acompanha aqui a pontuação da temporada corrente.")

# Dropdown de Ligas Ativas
liga_selecionada = st.selectbox("Escolhe a Liga Corrente:", ["Liga Fénix Negra - Season 2"])
st.divider()

# ==========================================
# RENDERIZAÇÃO DA LIGA FÉNIX
# ==========================================
if liga_selecionada == "Liga Fénix Negra - Season 2":
    
    if not db or "nova_liga" not in db:
        st.warning("⚠️ Ainda não há dados processados para a Nova Liga (executa o script de sincronização).")
        st.stop()

    nova_liga_data = db["nova_liga"]
    metrics = nova_liga_data.get("advanced_metrics", {})
    
    # --- CABEÇALHO PERSONALIZADO: LOGÓTIPO + TÍTULO VERMELHO GIGANTE ---
    # NOTA: o código procurava "fenix.jpg", que não existe no repositório. Agora usa fenix.png.
    fenix_src = img_src("fenix.png")
    if fenix_src:
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 25px;">
            <img src="{fenix_src}" width="85" style="margin-right: 20px; object-fit: contain;">
            <h1 style="margin: 0; padding: 0; font-size: 3rem; color: #7a161c; font-weight: 900; text-transform: uppercase; letter-spacing: 1px;">Liga Fénix Negra</h1>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("<h1 style='font-size: 3rem; color: #7a161c; font-weight: 900; text-transform: uppercase;'>Liga Fénix Negra</h1>", unsafe_allow_html=True)
    
    # 🏆 QUADRO DE MÉTRICAS (KINGS)
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.subheader("👑 King of the League")
            st.markdown("*(Torneios Ganhos)*")
            for king in metrics.get("kings", []):
                st.write(king)
    with c2:
        with st.container(border=True):
            st.subheader("🎯 Swiss King")
            st.markdown("*(Mais Vitórias na Fase Suíça)*")
            st.success(metrics.get("swiss_king", "N/A"))
            
    st.write("")
    
    # 📊 CLASSIFICAÇÃO GERAL
    st.subheader("📊 Classificação da Liga (Soma dos 8 Melhores Resultados)")
    df_standings = pd.DataFrame(nova_liga_data.get('standings_league', []))
    if not df_standings.empty: 
        df_standings.set_index('Rank', inplace=True)
        st.dataframe(df_standings, use_container_width=True)
    else:
        st.write("Sem jogadores classificados.")

    st.divider()

    # 📋 AUDIT LOG
    st.subheader("📋 Audit Log de Torneios Processados")
    df_audit = pd.DataFrame(nova_liga_data.get('audit_log', []))
    if not df_audit.empty:
        df_audit.index += 1
        df_audit.index.name = "#"
        st.dataframe(df_audit, use_container_width=True)
    else:
        st.write("Nenhum evento registado.")
