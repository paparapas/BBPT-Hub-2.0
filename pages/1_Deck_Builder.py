import streamlit as st
import pandas as pd
import random
import re
import base64
import os
import json
import hashlib
from db_connection import supabase

# ==========================================
# CONFIGURAÇÃO DE PÁGINA E CSS
# ==========================================
st.set_page_config(page_title="BBPT Deck Builder", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem !important; }
    .part-card { text-align: center; padding: 10px; background-color: #f8f9fa; border-radius: 8px; margin-bottom: 10px; color: black;}
    .part-card img { max-width: 100%; height: 80px; object-fit: contain; margin-bottom: 5px; }
    .part-name { font-size: 0.8rem; font-weight: bold; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .part-category { font-size: 0.65rem; color: #666; text-transform: uppercase; }
    
    .light-backdrop-icon {
        background-color: rgba(255, 255, 255, 0.85);
        padding: 3px 6px;
        border-radius: 6px;
    }
    
    .deck-summary-box {
        background-color: #0f111a;
        border-radius: 12px;
        padding: 30px;
        margin-top: 20px;
        color: white;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        box-shadow: 0px 8px 16px rgba(0,0,0,0.4);
    }
    .deck-summary-title {
        text-align: center;
        font-size: 32px;
        font-weight: 900;
        letter-spacing: 2px;
        margin-bottom: 30px;
        text-transform: uppercase;
        color: #ffffff;
    }
    .combo-row {
        display: flex;
        align-items: center;
        padding: 15px 0;
        border-bottom: 1px solid #1f2333;
    }
    .combo-row:last-child {
        border-bottom: none;
    }
    
    /* ---- AJUSTE DE IMAGENS BX/UX ---- */
    .combo-blade-img {
        width: 110px;
        height: 110px;
        flex-shrink: 0;
        object-fit: contain;
        margin-right: 20px;
        filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5));
    }
    
    /* ---- AJUSTE DE IMAGENS CX E CX EXPANDED ---- */
    .composite-blade-container {
        position: relative;
        width: 110px;
        height: 110px;
        flex-shrink: 0;
        margin-right: 20px;
    }
    .composite-layer {
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        object-fit: contain;
    }
    .layer-metal, .layer-main { 
        width: 100%; 
        height: 100%; 
        filter: drop-shadow(0px 4px 6px rgba(0,0,0,0.5)); 
    }
    .layer-metal { z-index: 1; }
    .layer-main { z-index: 2; }
    .layer-chip { 
        width: 42%; 
        height: 42%; 
        z-index: 3; 
    }

    .combo-info {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .combo-top-line {
        display: flex;
        align-items: center;
        margin-bottom: 8px;
    }
    .combo-line-img {
        height: 32px;
        margin-right: 15px;
        object-fit: contain;
    }
    .combo-bottom-line {
        display: flex;
        align-items: center;
    }
    .combo-icon {
        height: 30px;
        margin-right: 12px;
    }
    .combo-text {
        font-size: 22px;
        font-weight: 700;
        color: #f1f1f1;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# CARREGAMENTO DE ÍCONES E PEÇAS DO SUPABASE
# ==========================================
@st.cache_data(ttl=3600)
def load_categories():
    try:
        res = supabase.table("categories").select("*").execute()
        icons = {}
        line_logos = {}
        
        for c in res.data:
            name = c["name"]
            url = c["image_url"]
            
            # Mapeamento robusto
            if name in ["Right Spin", "Left Spin", "Attack", "Defense", "Stamina", "Balance"]:
                icons[name] = url
            
            # Procura o logo pela correspondência parcial
            if "Basic" in name: line_logos["Basic (BX)"] = url
            if "Unique" in name: line_logos["Unique (UX)"] = url
            if "Custom" in name: line_logos["Custom (CX)"] = url
            if "Expand" in name: line_logos["Expand (CXE)"] = url
            
        return icons, line_logos
    except Exception as e:
        st.error(f"Erro ao carregar Categorias: {e}")
        return {}, {}

ICONS, LINE_LOGOS = load_categories()

@st.cache_data(ttl=300)
def load_builder_data():
    parts_dict = {
        "bx_blades": [], "ux_blades": [], "ux_expanded_blades": [], 
        "cx_blades": [], "ratchets": [], "bits": [], 
        "assist_blades": [], "metal_blades": [], "over_blades": [], "lock_chips": []
    }
    images_dict = {}
    spin_dict = {}
    
    try:
        res = supabase.table("parts").select("*").execute()
        for p in res.data:
            name = str(p["name"]).strip()
            ptype = p["part_type"]
            sys = p.get("system_type", "")
            
            # Spin Direction
            spin_raw = str(p.get("spin_direction", "Right")).strip().title()
            spin_val = "Left" if spin_raw == "Left" else "Right"
            spin_dict[name] = f"{spin_val} Spin"
            
            # Image URL
            img_url = p.get("image_url")
            if img_url and str(img_url).startswith("http"):
                images_dict[name] = str(img_url)
                
            # Classificar
            if ptype == "Bit": parts_dict["bits"].append(name)
            elif ptype == "Ratchet": parts_dict["ratchets"].append(name)
            elif ptype == "Lock Chip": parts_dict["lock_chips"].append(name)
            elif ptype == "Assist Blade": parts_dict["assist_blades"].append(name)
            elif ptype == "Metal Blade": parts_dict["metal_blades"].append(name)
            elif ptype == "Over Blade": parts_dict["over_blades"].append(name)
            elif ptype == "Blade":
                if sys == "CX": parts_dict["cx_blades"].append(name)
                elif sys == "UX": parts_dict["ux_blades"].append(name)
                elif sys == "UX Expanded": parts_dict["ux_expanded_blades"].append(name)
                else: parts_dict["bx_blades"].append(name)

        return {k: sorted(list(set(v))) for k, v in parts_dict.items()}, images_dict, spin_dict
    except Exception as e:
        st.error(f"Erro ao carregar Peças: {e}")
        return parts_dict, {}, {}

parts, images_map, spin_map = load_builder_data()

# ==========================================
# LEITURA DA BASE DE DADOS SUPABASE (APENAS UMA VEZ E EM CACHE)
# ==========================================
@st.cache_data(ttl=600)
def load_builder_data():
    parts_dict = {
        "bx_blades": [], "ux_blades": [], "ux_expanded_blades": [], 
        "cx_blades": [], "ratchets": [], "bits": [], 
        "assist_blades": [], "metal_blades": [], "over_blades": [], "lock_chips": []
    }
    images_dict, spin_dict = {}, {}
    
    try:
        res = supabase.table("parts").select("*").execute()
        for p in res.data:
            name = str(p["name"]).strip()
            ptype = p["part_type"]
            sys = p.get("system_type", "")
            spin_raw = str(p.get("spin_direction", "Right")).strip().title()
            spin_val = "Left" if spin_raw == "Left" else "Right"
            spin_dict[name] = f"{spin_val} Spin"
            
            img_url = p.get("image_url")
            if img_url and str(img_url).startswith("http"): images_dict[name] = str(img_url)
                
            if ptype == "Bit": parts_dict["bits"].append(name)
            elif ptype == "Ratchet": parts_dict["ratchets"].append(name)
            elif ptype == "Lock Chip": parts_dict["lock_chips"].append(name)
            elif ptype == "Assist Blade": parts_dict["assist_blades"].append(name)
            elif ptype == "Metal Blade": parts_dict["metal_blades"].append(name)
            elif ptype == "Over Blade": parts_dict["over_blades"].append(name)
            elif ptype == "Blade":
                if sys == "CX": parts_dict["cx_blades"].append(name)
                elif sys == "UX": parts_dict["ux_blades"].append(name)
                elif sys == "UX Expanded": parts_dict["ux_expanded_blades"].append(name)
                else: parts_dict["bx_blades"].append(name)

        return {k: sorted(list(set(v))) for k, v in parts_dict.items()}, images_dict, spin_dict
    except Exception as e:
        return parts_dict, {}, {}

parts, images_map, spin_map = load_builder_data()

# ==========================================
# GESTOR DE ESTADO E LOGIN (SIDEBAR)
# ==========================================
if "deck_size" not in st.session_state: st.session_state.deck_size = 3
if "logged_in_user" not in st.session_state: st.session_state.logged_in_user = None
if "deck_name" not in st.session_state: st.session_state.deck_name = "" 
if "user_row" not in st.session_state: st.session_state.user_row = {}

for i in range(4):
    if f"b_c_{i}_type" not in st.session_state: st.session_state[f"b_c_{i}_type"] = "Basic (BX)"
    if f"b_c_{i}_spin" not in st.session_state: st.session_state[f"b_c_{i}_spin"] = "Right Spin"
    if f"b_c_{i}_bt" not in st.session_state: st.session_state[f"b_c_{i}_bt"] = "Attack"
    
    for k in ["main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
        if f"b_c_{i}_{k}" not in st.session_state:
            st.session_state[f"b_c_{i}_{k}"] = "--"

st.sidebar.title("🔐 Área Pessoal")

if st.session_state.logged_in_user is None:
    with st.sidebar.form("login_form"):
        st.write("Acede aos teus Decks Gravados:")
        user_input = st.text_input("Blader (Nome):")
        pass_input = st.text_input("Password:", type="password")
        if st.form_submit_button("Entrar"):
            pass_hash = hashlib.md5(pass_input.encode()).hexdigest()
            try:
                # Procura o utilizador e a password no Supabase
                res = supabase.table("bladers").select("*").ilike("alias", user_input.strip()).execute()
                if res.data:
                    user_data = res.data[0]
                    if user_data.get("password_hash") == pass_hash:
                        st.session_state.logged_in_user = user_data["alias"]
                        st.session_state.user_row = user_data
                        st.rerun()
                    else:
                        st.error("❌ Password incorreta!")
                else:
                    st.error("❌ Utilizador não encontrado.")
            except Exception as e:
                st.error(f"⚠️ Erro de ligação à BD: {e}")
else:
    st.sidebar.success(f"Bem-vindo, {st.session_state.logged_in_user}!")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in_user = None
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🗄️ Meus Decks")
    
    opcoes_slots = []
    for s in ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5"]:
        nome_display = s.replace("_", " ").title()
        if "user_row" in st.session_state and st.session_state.user_row.get(s):
            try:
                # Dependendo de como o Supabase envia o JSON, pode já ser um dict ou uma string
                slot_data = st.session_state.user_row[s]
                if isinstance(slot_data, str):
                    slot_data = json.loads(slot_data)
                
                if "name" in slot_data and slot_data["name"].strip():
                    nome_display = f"{nome_display} - {slot_data['name']}"
            except: pass
        opcoes_slots.append(nome_display)
        
    slot_choice_display = st.sidebar.selectbox("Escolher Slot:", opcoes_slots)
    slot_db_column = slot_choice_display.split(" - ")[0].replace(" ", "_").lower()
    
    deck_name_input = st.sidebar.text_input("Nome do Deck:", value=st.session_state.deck_name, max_chars=22, placeholder="Ex: Torneio Nacional")

    col_save, col_load = st.sidebar.columns(2)
    
    if col_save.button("💾 Gravar", use_container_width=True, type="primary"):
        deck_to_save = {"size": st.session_state.deck_size, "name": deck_name_input.strip(), "combos": []}
        for i in range(st.session_state.deck_size):
            combo = {
                "type": st.session_state[f"b_c_{i}_type"],
                "spin": st.session_state.get(f"b_c_{i}_spin", "Right Spin"),
                "bt": st.session_state.get(f"b_c_{i}_bt", "Attack"),
                "main_blade": st.session_state.get(f"b_c_{i}_main_blade", "--"),
                "ratchet": st.session_state.get(f"b_c_{i}_ratchet", "--"),
                "bit": st.session_state.get(f"b_c_{i}_bit", "--"),
                "lock_chip": st.session_state.get(f"b_c_{i}_lock_chip", "--"),
                "assist_blade": st.session_state.get(f"b_c_{i}_assist_blade", "--"),
                "metal_blade": st.session_state.get(f"b_c_{i}_metal_blade", "--"),
                "over_blade": st.session_state.get(f"b_c_{i}_over_blade", "--")
            }
            deck_to_save["combos"].append(combo)
            
        with st.spinner("A gravar..."):
            try:
                # Atualiza apenas a coluna do Slot no Supabase
                supabase.table("bladers").update({slot_db_column: deck_to_save}).eq("alias", st.session_state.logged_in_user).execute()
                st.session_state.user_row[slot_db_column] = deck_to_save
                st.session_state.deck_name = deck_name_input.strip()
                st.sidebar.success(f"Gravado no {slot_db_column.replace('_', ' ').title()}!")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

    if col_load.button("📥 Carregar", use_container_width=True):
        with st.spinner("A carregar..."):
            try:
                res = supabase.table("bladers").select(slot_db_column).eq("alias", st.session_state.logged_in_user).execute()
                if res.data and res.data[0].get(slot_db_column):
                    loaded_deck = res.data[0][slot_db_column]
                    if isinstance(loaded_deck, str):
                        loaded_deck = json.loads(loaded_deck)
                        
                    st.session_state.deck_size = loaded_deck.get("size", 3)
                    st.session_state.deck_name = loaded_deck.get("name", "")
                    for i, c in enumerate(loaded_deck["combos"]):
                        st.session_state[f"b_c_{i}_type"] = c.get("type", "Basic (BX)")
                        st.session_state[f"b_c_{i}_spin"] = c.get("spin", "Right Spin")
                        st.session_state[f"b_c_{i}_bt"] = c.get("bt", "Attack")
                        st.session_state[f"b_c_{i}_main_blade"] = c.get("main_blade", "--")
                        st.session_state[f"b_c_{i}_ratchet"] = c.get("ratchet", "--")
                        st.session_state[f"b_c_{i}_bit"] = c.get("bit", "--")
                        st.session_state[f"b_c_{i}_lock_chip"] = c.get("lock_chip", "--")
                        st.session_state[f"b_c_{i}_assist_blade"] = c.get("assist_blade", "--")
                        st.session_state[f"b_c_{i}_metal_blade"] = c.get("metal_blade", "--")
                        st.session_state[f"b_c_{i}_over_blade"] = c.get("over_blade", "--")
                    st.rerun()
                else:
                    st.sidebar.warning("Slot vazio!")
            except Exception as e:
                st.sidebar.error(f"Erro: {e}")

# ==========================================
# RANDOMIZER E UTILIDADES
# ==========================================
def clear_deck():
    st.session_state.deck_name = ""
    for i in range(4):
        st.session_state[f"b_c_{i}_type"] = "Basic (BX)"
        st.session_state[f"b_c_{i}_spin"] = "Right Spin"
        st.session_state[f"b_c_{i}_bt"] = "Attack"
        for k in ["main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
            st.session_state[f"b_c_{i}_{k}"] = "--"

def randomize_deck():
    st.session_state.deck_size = 3
    st.session_state.deck_name = ""
    used_blades, used_ratchets, used_bits, used_chips, used_assist, used_metal = set(), set(), set(), set(), set(), set()
    types = ["Basic (BX)", "Unique (UX)", "Custom (CX)", "Expand (CXE)", "UX Expanded"]
    b_types = ["Attack", "Defense", "Stamina", "Balance"]
    
    def pick_unique(pool, used_set):
        available = [p for p in pool if p not in used_set]
        if not available: return "--"
        choice = random.choice(available)
        used_set.add(re.sub(r'\s*\(.*?\)\s*', '', choice).strip().lower())
        return choice

    for i in range(st.session_state.deck_size):
        ctype = random.choice(types)
        st.session_state[f"b_c_{i}_type"] = ctype
        st.session_state[f"b_c_{i}_bt"] = random.choice(b_types)
        for k in ["main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
            st.session_state[f"b_c_{i}_{k}"] = "--"
            
        if ctype == "Basic (BX)":
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts["bx_blades"], used_blades)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
            is_int = st.session_state[f"b_c_{i}_bit"] in ["Turbo", "Operate"]
            st.session_state[f"b_c_{i}_ratchet"] = "Integrada" if is_int else pick_unique(parts["ratchets"], used_ratchets)
        elif ctype == "Unique (UX)":
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts["ux_blades"], used_blades)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
            is_int = st.session_state[f"b_c_{i}_bit"] in ["Turbo", "Operate"]
            st.session_state[f"b_c_{i}_ratchet"] = "Integrada" if is_int else pick_unique(parts["ratchets"], used_ratchets)
        elif ctype == "Custom (CX)":
            st.session_state[f"b_c_{i}_lock_chip"] = pick_unique(parts["lock_chips"], used_chips)
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts["cx_blades"], used_blades)
            st.session_state[f"b_c_{i}_assist_blade"] = pick_unique(parts["assist_blades"], used_assist)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
            is_int = st.session_state[f"b_c_{i}_bit"] in ["Turbo", "Operate"]
            st.session_state[f"b_c_{i}_ratchet"] = "Integrada" if is_int else pick_unique(parts["ratchets"], used_ratchets)
        elif ctype == "Expand (CXE)":
            st.session_state[f"b_c_{i}_lock_chip"] = pick_unique(parts["lock_chips"], used_chips)
            st.session_state[f"b_c_{i}_metal_blade"] = pick_unique(parts["metal_blades"], used_metal)
            st.session_state[f"b_c_{i}_over_blade"] = pick_unique(parts["over_blades"], used_blades)
            st.session_state[f"b_c_{i}_assist_blade"] = pick_unique(parts["assist_blades"], used_assist)
            st.session_state[f"b_c_{i}_bit"] = pick_unique(parts["bits"], used_bits)
            is_int = st.session_state[f"b_c_{i}_bit"] in ["Turbo", "Operate"]
            st.session_state[f"b_c_{i}_ratchet"] = "Integrada" if is_int else pick_unique(parts["ratchets"], used_ratchets)
        elif ctype == "UX Expanded":
            st.session_state[f"b_c_{i}_main_blade"] = pick_unique(parts.get("ux_expanded_blades", []), used_blades)
            bits_validos = [b for b in parts["bits"] if b not in ["Turbo", "Operate"]]
            st.session_state[f"b_c_{i}_bit"] = pick_unique(bits_validos, used_bits)
            st.session_state[f"b_c_{i}_ratchet"] = "Integrada na Blade"

# ==========================================
# TÍTULO E INTERFACE PRINCIPAL
# ==========================================
st.title("🛠️ Custom Deck Builder")
st.markdown("Constrói, testa e exporta os teus decks. Validação automática de regras BBPT ativada.")

col_size, col_clear, col_rand = st.columns([2, 1, 1])
with col_size:
    st.radio("Tamanho do Deck:", options=[3, 4], horizontal=True, key="deck_size")
with col_clear:
    st.button("🧹 Limpar Deck", use_container_width=True, on_click=clear_deck)
with col_rand:
    st.button("🎲 Gerar Aleatório", use_container_width=True, on_click=randomize_deck)

st.divider()

def render_part_card(part_name, category):
    if part_name == "--":
        st.markdown(f'<div class="part-card" style="opacity: 0.4;"><div style="height: 80px; display: flex; align-items: center; justify-content: center; color: #999;">?</div><div class="part-category">{category}</div><div class="part-name">---</div></div>', unsafe_allow_html=True)
        return
    img_url = images_map.get(part_name, "https://via.placeholder.com/150?text=No+Image")
    st.markdown(f'<div class="part-card"><img src="{img_url}" alt="{part_name}" referrerpolicy="no-referrer"><div class="part-category">{category}</div><div class="part-name" title="{part_name}">{part_name}</div></div>', unsafe_allow_html=True)

# ==========================================
# CONSTRUTOR DE COMBOS
# ==========================================
for i in range(st.session_state.deck_size):
    with st.container(border=True):
        c_title, c_type, c_spin, c_bt = st.columns([1.2, 2, 1, 1])
        with c_title:
            st.markdown(f"#### 🌀 Combo {i+1}")
        with c_type:
            ct = st.selectbox("Linha", ["Basic (BX)", "Unique (UX)", "Custom (CX)", "Expand (CXE)", "UX Expanded"], key=f"b_c_{i}_type", label_visibility="collapsed")
            if ct == "Expand (CXE)":
                st.markdown(f"<img src='{LINE_LOGOS['Custom (CX)']}' style='height: 24px; margin-top: 5px; margin-right: 5px;'><img src='{LINE_LOGOS['Expand (CXE)']}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
            elif ct == "UX Expanded":
                st.markdown(f"<img src='{LINE_LOGOS['Unique (UX)']}' style='height: 24px; margin-top: 5px; margin-right: 5px;'><img src='{LINE_LOGOS['Expand (CXE)']}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
            else:
                st.markdown(f"<img src='{LINE_LOGOS[ct]}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
        with c_spin:
            current_blade = st.session_state.get(f"b_c_{i}_over_blade", "--") if "Expand" in ct else st.session_state.get(f"b_c_{i}_main_blade", "--")
            sp = spin_map.get(current_blade, "Right Spin")
            st.session_state[f"b_c_{i}_spin"] = sp
            st.markdown(f"<img src='{ICONS[sp]}' class='light-backdrop-icon' style='height: 24px; margin-top: 5px;' title='{sp}'>", unsafe_allow_html=True)
        with c_bt:
            bt = st.selectbox("Tipo", ["Attack", "Defense", "Stamina", "Balance"], key=f"b_c_{i}_bt", label_visibility="collapsed")
            st.markdown(f"<img src='{ICONS[bt]}' style='height: 24px; margin-top: 5px;'>", unsafe_allow_html=True)
            
        st.write("") 
        
        is_int_bit = st.session_state.get(f"b_c_{i}_bit", "--") in ["Turbo", "Operate"]
        ratchet_opts = ["Integrada"] if is_int_bit else ["--"] + parts["ratchets"]
        
        if ct in ["Basic (BX)", "Unique (UX)"]:
            blade_list = parts["bx_blades"] if ct == "Basic (BX)" else parts["ux_blades"]
            c1, c2, c3 = st.columns([2, 1, 1])
            c1.selectbox("Blade", ["--"]+blade_list, key=f"b_c_{i}_main_blade")
            c3.selectbox("Bit", ["--"]+parts["bits"], key=f"b_c_{i}_bit")
            c2.selectbox("Ratchet", ratchet_opts, key=f"b_c_{i}_ratchet", disabled=is_int_bit)
            
            g1, g2, g3 = st.columns(3)
            with g1: render_part_card(st.session_state[f"b_c_{i}_main_blade"], "Blade")
            with g2: render_part_card(st.session_state[f"b_c_{i}_ratchet"], "Ratchet")
            with g3: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")
            
        elif ct == "Custom (CX)":
            c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 1.2, 1.2])
            c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"b_c_{i}_lock_chip")
            c2.selectbox("Main", ["--"]+parts["cx_blades"], key=f"b_c_{i}_main_blade")
            c3.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"b_c_{i}_assist_blade")
            c5.selectbox("Bit", ["--"]+parts["bits"], key=f"b_c_{i}_bit")
            c4.selectbox("Ratchet", ratchet_opts, key=f"b_c_{i}_ratchet", disabled=is_int_bit)
            
            g1, g2, g3, g4, g5 = st.columns(5)
            with g1: render_part_card(st.session_state[f"b_c_{i}_lock_chip"], "Lock Chip")
            with g2: render_part_card(st.session_state[f"b_c_{i}_main_blade"], "Main Blade")
            with g3: render_part_card(st.session_state[f"b_c_{i}_assist_blade"], "Assist Blade")
            with g4: render_part_card(st.session_state[f"b_c_{i}_ratchet"], "Ratchet")
            with g5: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")
            
        elif ct == "Expand (CXE)":
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 2, 2, 1.2, 1.2])
            c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"b_c_{i}_lock_chip")
            c2.selectbox("Metal", ["--"]+parts["metal_blades"], key=f"b_c_{i}_metal_blade")
            c3.selectbox("Over", ["--"]+parts["over_blades"], key=f"b_c_{i}_over_blade")
            c4.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"b_c_{i}_assist_blade")
            c6.selectbox("Bit", ["--"]+parts["bits"], key=f"b_c_{i}_bit")
            c5.selectbox("Ratchet", ratchet_opts, key=f"b_c_{i}_ratchet", disabled=is_int_bit)
            
            g1, g2, g3, g4, g5, g6 = st.columns(6)
            with g1: render_part_card(st.session_state[f"b_c_{i}_lock_chip"], "Lock Chip")
            with g2: render_part_card(st.session_state[f"b_c_{i}_metal_blade"], "Metal Blade")
            with g3: render_part_card(st.session_state[f"b_c_{i}_over_blade"], "Over Blade")
            with g4: render_part_card(st.session_state[f"b_c_{i}_assist_blade"], "Assist Blade")
            with g5: render_part_card(st.session_state[f"b_c_{i}_ratchet"], "Ratchet")
            with g6: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")

        elif ct == "UX Expanded":
            c1, c2 = st.columns([2, 1])
            c1.selectbox("Blade", ["--"]+parts.get("ux_expanded_blades", []), key=f"b_c_{i}_main_blade")
            bits_validos = [b for b in parts["bits"] if b not in ["Turbo", "Operate"]]
            c2.selectbox("Bit", ["--"]+bits_validos, key=f"b_c_{i}_bit")
            st.session_state[f"b_c_{i}_ratchet"] = "Integrada na Blade" 
            
            g1, g2 = st.columns(2)
            with g1: render_part_card(st.session_state[f"b_c_{i}_main_blade"], "Blade")
            with g2: render_part_card(st.session_state[f"b_c_{i}_bit"], "Bit")

st.divider()

has_duplicates = False
dup_error_msg = ""
missing_parts = False

used_blades, used_ratchets, used_bits, used_chips, used_assist, used_metal = set(), set(), set(), set(), set(), set()
deck_text_export = "🛡️ **O Meu Deck BBPT**\n"
combo_data_for_visual = []

for i in range(st.session_state.deck_size):
    ct = st.session_state[f"b_c_{i}_type"]
    sp = st.session_state[f"b_c_{i}_spin"]
    bt = st.session_state[f"b_c_{i}_bt"]
    
    ks = ["main_blade", "ratchet", "bit"] if ct in ["Basic (BX)", "Unique (UX)", "UX Expanded"] else ["lock_chip", "main_blade", "assist_blade", "ratchet", "bit"] if ct == "Custom (CX)" else ["lock_chip", "metal_blade" , "over_blade" , "assist_blade", "ratchet", "bit"]
    
    combo_str_parts = []
    for k in ks:
        v = st.session_state.get(f"b_c_{i}_{k}", "--")
        if ct == "UX Expanded" and k == "ratchet": 
            v = "Integrada na Blade"
        elif k == "ratchet" and st.session_state.get(f"b_c_{i}_bit", "--") in ["Turbo", "Operate"]: 
            v = "Integrada"
            
        if v not in ["Integrada na Blade", "Integrada"]: 
            combo_str_parts.append(v)
            
        if v == "--": missing_parts = True
        
    deck_text_export += f"🔹 **Combo {i+1}:** [{sp}] [{bt}] {' | '.join(combo_str_parts)}\n"

    if not missing_parts and not has_duplicates:
        b = st.session_state[f"b_c_{i}_over_blade"] if "Expand" in ct and ct != "UX Expanded" else st.session_state.get(f"b_c_{i}_main_blade", "--")
        if b != '--':
            base = re.sub(r'\s*\(.*?\)\s*', '', str(b)).strip().lower()
            if base in used_blades: has_duplicates = True; dup_error_msg = f"A Blade '{b}' está repetida!"
            used_blades.add(base)
            
        r = st.session_state.get(f"b_c_{i}_ratchet", '--')
        if ct == "UX Expanded": r = "Integrada na Blade"
        elif st.session_state.get(f"b_c_{i}_bit", "--") in ["Turbo", "Operate"]: r = "Integrada"
        
        if r != '--' and "Integrada" not in r:
            if r in used_ratchets: has_duplicates = True; dup_error_msg = f"A Ratchet '{r}' está repetida!"
            used_ratchets.add(r)
            
        bt_val = st.session_state.get(f"b_c_{i}_bit", '--')
        if bt_val != '--':
            if bt_val in used_bits: has_duplicates = True; dup_error_msg = f"A Bit '{bt_val}' está repetida!"
            used_bits.add(bt_val)
            
        a = st.session_state.get(f"b_c_{i}_assist_blade", '--')
        if a != '--':
            if a in used_assist: has_duplicates = True; dup_error_msg = f"A Assist Blade '{a}' está repetida!"
            used_assist.add(a)
            
        m = st.session_state.get(f"b_c_{i}_metal_blade", '--')
        if m != '--':
            if m in used_metal: has_duplicates = True; dup_error_msg = f"A Metal Blade '{m}' está repetida!"
            used_metal.add(m)
            
        c = st.session_state.get(f"b_c_{i}_lock_chip", '--')
        if c != '--':
            c_low = c.strip().lower()
            if c_low in used_chips: has_duplicates = True; dup_error_msg = f"O Lock Chip '{c}' está repetido!"
            used_chips.add(c_low)

        img_html = ""
        if ct in ["Basic (BX)", "Unique (UX)", "UX Expanded"]:
            hero_blade = st.session_state[f"b_c_{i}_main_blade"]
            url_blade = images_map.get(hero_blade, "https://via.placeholder.com/150")
            img_html = f'<img class="combo-blade-img" src="{url_blade}" alt="Blade" referrerpolicy="no-referrer">'
        elif ct == "Custom (CX)":
            m_blade = st.session_state[f"b_c_{i}_main_blade"]
            l_chip = st.session_state[f"b_c_{i}_lock_chip"]
            url_main = images_map.get(m_blade, "https://via.placeholder.com/150")
            url_chip = images_map.get(l_chip, "https://via.placeholder.com/150")
            img_html = f'<div class="composite-blade-container"><img class="composite-layer layer-main" src="{url_main}" alt="Main" referrerpolicy="no-referrer"><img class="composite-layer layer-chip" src="{url_chip}" alt="Chip" referrerpolicy="no-referrer"></div>'
        else: # Expand (CXE)
            o_blade = st.session_state[f"b_c_{i}_over_blade"]
            mt_blade = st.session_state[f"b_c_{i}_metal_blade"]
            l_chip = st.session_state[f"b_c_{i}_lock_chip"]
            url_over = images_map.get(o_blade, "https://via.placeholder.com/150")
            url_metal = images_map.get(mt_blade, "https://via.placeholder.com/150")
            url_chip = images_map.get(l_chip, "https://via.placeholder.com/150")
            img_html = f'<div class="composite-blade-container"><img class="composite-layer layer-metal" src="{url_metal}" alt="Metal" referrerpolicy="no-referrer"><img class="composite-layer layer-main" src="{url_over}" alt="Over" referrerpolicy="no-referrer"><img class="composite-layer layer-chip" src="{url_chip}" alt="Chip" referrerpolicy="no-referrer"></div>'

        logos_html = ""
        if ct == "Basic (BX)": 
            logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Basic (BX)"]}" alt="Basic">'
        elif ct == "Unique (UX)": 
            logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Unique (UX)"]}" alt="Unique">'
        elif ct == "Custom (CX)": 
            logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Custom (CX)"]}" alt="Custom">'
        elif ct == "Expand (CXE)": 
            logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Custom (CX)"]}" alt="Custom"><img class="combo-line-img" src="{LINE_LOGOS["Expand (CXE)"]}" alt="Expand">'
        elif ct == "UX Expanded": 
            logos_html += f'<img class="combo-line-img" src="{LINE_LOGOS["Unique (UX)"]}" alt="Unique"><img class="combo-line-img" src="{LINE_LOGOS["Expand (CXE)"]}" alt="Expand">'

        combo_data_for_visual.append({
            "image_html": img_html,
            "logos_html": logos_html,
            "spin": ICONS[sp],
            "type": ICONS[bt],
            "name": " ".join(combo_str_parts).replace("--", "")
        })

col_status, col_export = st.columns([2, 1])

with col_status:
    if missing_parts:
        st.warning("⚠️ O Deck está incompleto. Seleciona todas as peças para validar.")
    elif has_duplicates:
        st.error(f"❌ **Deck Ilegal:** {dup_error_msg}")
    else:
        st.success("✅ **Deck Legal e Válido para Torneios!**")

with col_export:
    st.info("Copia o texto abaixo ou tira um Print Screen do Cartão Visual!")
    st.code(deck_text_export, language="markdown")

if not missing_parts and not has_duplicates:
    html_rows = ""
    for c in combo_data_for_visual:
        html_rows += f'<div class="combo-row">{c["image_html"]}<div class="combo-info"><div class="combo-top-line">{c["logos_html"]}<img class="combo-icon light-backdrop-icon" src="{c["spin"]}" alt="Spin"></div><div class="combo-bottom-line"><img class="combo-icon" src="{c["type"]}" alt="Type"><span class="combo-text">{c["name"]}</span></div></div></div>'
    
    display_title = st.session_state.deck_name.upper() if st.session_state.get("deck_name", "").strip() else "DECK SUMMARY"
    visual_report_html = f'<div class="deck-summary-box"><div class="deck-summary-title">{display_title}</div>{html_rows}</div>'
    st.markdown(visual_report_html, unsafe_allow_html=True)
