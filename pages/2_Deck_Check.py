import streamlit as st
import pandas as pd
import json
import os
import re
import difflib
from datetime import datetime
import logging
import requests
import base64
from st_keyup import st_keyup
import tempfile
import io
import hashlib # ADICIONADO PARA VERIFICAR A PASSWORD
from PIL import Image   
from fpdf import FPDF
from streamlit_cookies_controller import CookieController
from db_connection import supabase

st.set_page_config(page_title="Deck Check & Admin", page_icon="📝", layout="wide")
logging.basicConfig(level=logging.ERROR, format='%(asctime)s [%(levelname)s] %(message)s')

# --- PASSWORDS DE ACESSO ---
ADMIN_PASSWORD = "bbpt-paparapas" 
JUDGE_PASSWORD = "bbpt-judge"

# ==========================================
# GESTÃO GLOBAL DE LOGIN (SIDEBAR AJUSTADA)
# ==========================================
from streamlit_cookies_controller import CookieController
import hashlib

controller = CookieController()
cookie_role = controller.get('user_role')

if cookie_role in ["owner", "admin", "judge"]:
    st.session_state.user_role = cookie_role
elif "user_role" not in st.session_state:
    st.session_state.user_role = None

logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"
has_logo = os.path.exists(logo_path)

with st.sidebar:
    if has_logo:
        with open(logo_path, "rb") as image_file: encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-right:10px;'><h1 style='display:inline;font-size:1.8rem;'></h1></div>", unsafe_allow_html=True)
    else: st.title("🛡️ BBPT App")
    st.divider()

    # Menu Dinâmico Hierárquico
    opcoes_menu = ["📝 Formulário Público", "🔍 Consulta Pública"]
    if st.session_state.user_role in ["admin", "owner"]:
        opcoes_menu.append("⚙️ Painel de Organização")
    if st.session_state.user_role == "owner":
        opcoes_menu.append("👥 Gestão de Utilizadores")

    menu = st.radio("Navegação:", opcoes_menu)
    st.divider()
    
    # Sistema Unificado de Input de Chaves
    if not st.session_state.user_role:
        with st.expander("🔐 Acesso Organização / Judges"):
            pwd = st.text_input("Password:", type="password", key="login_global")
            if st.button("Entrar 🔑", use_container_width=True):
                # AGORA LÊ DO SECRETS.TOML COM SEGURANÇA
                if pwd.strip() == st.secrets["PASSWORDS"]["OWNER"]:
                    st.session_state.user_role = "owner"
                    controller.set('user_role', 'owner', max_age=43200)
                    st.rerun()
                elif pwd.strip() == st.secrets["PASSWORDS"]["ADMIN"]:
                    st.session_state.user_role = "admin"
                    controller.set('user_role', 'admin', max_age=43200)
                    st.rerun()
                elif pwd.strip() == st.secrets["PASSWORDS"]["JUDGE"]:
                    st.session_state.user_role = "judge"
                    controller.set('user_role', 'judge', max_age=43200)
                    st.rerun()
                else: st.error("Incorreta!")
    else:
        st.success(f"🔓 Modo {st.session_state.user_role.upper()} Ativo")
        if st.button("Sair (Logout) 🔒", use_container_width=True):
            st.session_state.user_role = None
            st.session_state.finance_auth = False # Garante que limpa a RAM
            
            # Tenta apagar os cookies de forma segura, ignorando se não existirem
            try: controller.remove('user_role')
            except: pass
            
            try: controller.remove('finance_auth')
            except: pass
            
            st.rerun()

# ==========================================
# INTEGRAÇÃO SUPABASE E LEITURAS 
# ==========================================
@st.cache_data(ttl=2)
def get_active_tournaments():
    try:
        res = supabase.table("tournaments").select("*").eq("is_active", True).execute()
        return [{"id": t["id"], "event_name": t["name"], "checkin_open": t.get("checkin_open", True)} for t in res.data]
    except Exception as e:
        return []

def set_active_tournament(event_name):
    try:
        res_count = supabase.table("tournaments").select("id", count="exact").eq("is_active", True).execute()
        if res_count.count >= 3:
            st.error("🚨 Limite máximo atingido! Já tens 3 torneios ativos em simultâneo. Por favor, arquiva um deles antes de abrir outro.")
            return False
            
        res = supabase.table("tournaments").select("id").eq("name", event_name).execute()
        if res.data:
            supabase.table("tournaments").update({"is_active": True, "checkin_open": True}).eq("id", res.data[0]["id"]).execute()
        else:
            supabase.table("tournaments").insert({"name": event_name, "is_active": True, "checkin_open": True}).execute()
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar status do evento: {e}")
        return False

def toggle_checkin(t_id, status):
    supabase.table("tournaments").update({"checkin_open": status}).eq("id", t_id).execute()
    st.cache_data.clear()

def archive_tournament(t_id):
    supabase.table("tournaments").update({"is_active": False, "checkin_open": False}).eq("id", t_id).execute()
    st.cache_data.clear()

@st.cache_data(ttl=5) 
def get_all_records_cached(event_name):
    try:
        res_t = supabase.table("tournaments").select("id").eq("name", event_name).execute()
        if not res_t.data: return []
        t_id = res_t.data[0]["id"]
        res_reg = supabase.table("tournament_registrations").select("*, bladers(alias)").eq("tournament_id", t_id).execute()
        
        records = []
        for r in res_reg.data:
            records.append({
                "id": r["id"],
                "Event_Name": event_name,
                "Player": r["bladers"]["alias"] if r.get("bladers") else "Desconhecido",
                "Combo_1": r.get("combo_1", ""),
                "Combo_2": r.get("combo_2", ""),
                "Combo_3": r.get("combo_3", ""),
                "Combo_4": r.get("combo_4", ""),
                "Image_URL": r.get("image_url", "")
            })
        return records
    except Exception as e: 
        return []

@st.cache_data(ttl=5) 
def get_past_events_list():
    try:
        res = supabase.table("tournaments").select("name").execute()
        return sorted(list(set([t["name"] for t in res.data if t["name"]])))
    except: 
        return []

def upload_to_imgbb(image_file):
    url = "https://api.imgbb.com/1/upload"
    
    # 👇 AQUI ESTÁ A CORREÇÃO: Lê a nova estrutura [IMGBB] DECKS_KEY
    api_key = st.secrets["IMGBB"]["DECKS_KEY"]
    
    res = requests.post(
        url, 
        data={
            "key": api_key, 
            "image": base64.b64encode(image_file.getvalue()).decode("utf-8")
        }
    )
    if res.status_code == 200: 
        return res.json()["data"]["url"]
    raise Exception("Erro ImgBB")

def save_submission_cloud(player_name, combos, img_file, event_name):
    img_url = upload_to_imgbb(img_file)
    c_strs = []
    for c in combos:
        if c['type'] == 'Standard (BX / UX)': keys = ['main_blade', 'ratchet', 'bit']
        elif c['type'] == 'UX Expanded': keys = ['main_blade', 'bit']
        elif c['type'] == 'CX': keys = ['lock_chip', 'main_blade', 'assist_blade', 'ratchet', 'bit']
        else: keys = ['lock_chip', 'metal_blade', 'over_blade', 'assist_blade', 'ratchet', 'bit']
        parts = [str(c.get(k, '')) for k in keys if c.get(k, '') not in ["Integrada", "Integrada na Blade"]]
        c_strs.append(" | ".join(parts))
        
    while len(c_strs) < 4: c_strs.append("")
    
    try:
        res_b = supabase.table("bladers").select("id").eq("alias", player_name).execute()
        if res_b.data: blader_id = res_b.data[0]["id"]
        else:
            res_ins = supabase.table("bladers").insert({"alias": player_name}).execute()
            blader_id = res_ins.data[0]["id"]
            
        res_t = supabase.table("tournaments").select("id").eq("name", event_name).execute()
        if not res_t.data: raise Exception("Torneio não encontrado na DB")
        tourney_id = res_t.data[0]["id"]
        
        reg_data = {"tournament_id": tourney_id, "blader_id": blader_id, "combo_1": c_strs[0], "combo_2": c_strs[1], "combo_3": c_strs[2], "combo_4": c_strs[3], "image_url": img_url}
        supabase.table("tournament_registrations").upsert(reg_data, on_conflict="tournament_id, blader_id").execute()
        st.cache_data.clear()
    except Exception as e: raise Exception(f"Erro ao salvar na DB: {e}")

# ==========================================
# LÓGICA DE PEÇAS E ALGORITMOS
# ==========================================
if "num_combos" not in st.session_state: st.session_state.num_combos = 3
if "smart_val" not in st.session_state: st.session_state.smart_val = ""
if "keyup_key" not in st.session_state: st.session_state.keyup_key = 0

for i in range(4):
    for k in ["type", "main_blade", "ratchet", "bit", "lock_chip", "assist_blade", "metal_blade", "over_blade"]:
        if f"c_{i}_{k}" not in st.session_state: st.session_state[f"c_{i}_{k}"] = "Standard (BX / UX)" if k == "type" else "--"

@st.cache_data(ttl=300) 
def load_parts():
    try:
        res = supabase.table("parts").select("*").execute()
        p_dict = {"bx_ux_blades": [], "ux_expanded_blades": [], "cx_blades": [], "ratchets": [], "bits": [], "assist_blades": [], "metal_blades": [], "over_blades": [], "lock_chips": []}
        for p in res.data:
            name, ptype, sys = str(p["name"]).strip(), p["part_type"], p["system_type"]
            if ptype == "Bit": p_dict["bits"].append(name)
            elif ptype == "Ratchet": p_dict["ratchets"].append(name)
            elif ptype == "Lock Chip": p_dict["lock_chips"].append(name)
            elif ptype == "Assist Blade": p_dict["assist_blades"].append(name)
            elif ptype == "Metal Blade": p_dict["metal_blades"].append(name)
            elif ptype == "Over Blade": p_dict["over_blades"].append(name)
            elif ptype == "Blade":
                if sys == "CX": p_dict["cx_blades"].append(name)
                else: p_dict["bx_ux_blades"].append(name)
        return {k: sorted(list(set(v))) for k, v in p_dict.items()}, {}
    except: return {k: [] for k in ["bx_ux_blades", "ux_expanded_blades", "cx_blades", "ratchets", "bits", "assist_blades", "metal_blades", "over_blades", "lock_chips"]}, {}

@st.cache_data(ttl=5) 
def get_dynamic_player_list():
    try:
        res = supabase.table("bladers").select("alias").execute()
        return sorted(list(set([b["alias"] for b in res.data if b["alias"]])))
    except: return []

def load_players(): return ["-- Selecionar Jogador --"] + get_dynamic_player_list() + ["Outro (Novo Jogador)"]

def parse_smart_combo(text, parts_dict, alias_map):
    parsed = {"type": "Standard (BX / UX)", "main_blade": "--", "over_blade": "--", "metal_blade": "--", "assist_blade": "--", "lock_chip": "--", "ratchet": "--", "bit": "--"}
    words, text_cl = text.split(), "".join([re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in text.split()])
    words_cl = [re.sub(r'[^a-zA-Z0-9]', '', w).lower() for w in words]
    temp_dict = parts_dict.copy()
    temp_dict["all_main_blades"] = parts_dict.get("bx_ux_blades", []) + parts_dict.get("cx_blades", []) + parts_dict.get("ux_expanded_blades", [])
    cats = [("over_blades", "over_blade"), ("metal_blades", "metal_blade"), ("all_main_blades", "main_blade"), ("assist_blades", "assist_blade"), ("ratchets", "ratchet"), ("bits", "bit"), ("lock_chips", "lock_chip")]
    
    for cat, key in cats:
        best, r_max = "--", 0
        for p in sorted(temp_dict.get(cat, []), key=len, reverse=True):
            p_cl = re.sub(r'[^a-zA-Z0-9]', '', p).lower()
            if p_cl and p_cl in text_cl: best = p; break 
            p_words = re.sub(r'[^a-zA-Z0-9\s]', '', p).lower().split()
            if not p_words: continue
            match_score = 0
            for pw in p_words:
                best_w_score = 0
                for w in words_cl:
                    score = difflib.SequenceMatcher(None, pw, w).ratio()
                    if score > best_w_score: best_w_score = score
                match_score += best_w_score
            if (match_score / len(p_words)) > 0.85 and (match_score / len(p_words)) > r_max:
                r_max = match_score / len(p_words); best = p
        parsed[key] = best

    if parsed["over_blade"] != "--" or parsed["metal_blade"] != "--": parsed["type"] = "CX Expanded"
    elif parsed["main_blade"] in temp_dict.get("ux_expanded_blades", []): parsed["type"] = "UX Expanded"
    elif parsed["assist_blade"] != "--" or parsed["main_blade"] in parts_dict.get("cx_blades", []): parsed["type"] = "CX" 
    else: parsed["type"] = "Standard (BX / UX)"
    if parsed["type"] in ["CX", "CX Expanded"] and parsed["lock_chip"] == "--" and words: parsed["lock_chip"] = words[0].capitalize()
    return parsed

def apply_smart_combo(slot, data):
    st.session_state[f"c_{slot}_type"] = data.get("type")
    for k in ["lock_chip", "main_blade", "over_blade", "metal_blade", "assist_blade", "ratchet", "bit"]: st.session_state[f"c_{slot}_{k}"] = data.get(k, "--")
    if 'smart_match' in st.session_state: del st.session_state.smart_match
    st.session_state.smart_val = ""
    st.session_state.keyup_key += 1

def cancel_smart_combo():
    if 'smart_match' in st.session_state: del st.session_state.smart_match
    st.session_state.smart_val = ""
    st.session_state.keyup_key += 1

def append_suggestion(sug_text):
    words = st.session_state.smart_val.split()
    if words:
        words[-1] = sug_text
        st.session_state.smart_val = " ".join(words) + " "
        st.session_state.keyup_key += 1

@st.cache_data(ttl=120)
def gerar_pdf_decks(records, event_name):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    for d in records:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, f"Blader: {str(d['Player']).encode('latin-1', 'replace').decode('latin-1')}", ln=True, align='C')
        pdf.ln(5)
        pdf.set_font("Arial", size=12)
        for i in range(1, 5):
            combo = d.get(f'Combo_{i}')
            if combo: pdf.cell(0, 8, f"Combo {i}: {str(combo).encode('latin-1', 'replace').decode('latin-1')}", ln=True)
        pdf.ln(10)
        if d.get('Image_URL'):
            try:
                res = requests.get(d['Image_URL'], timeout=10)
                if res.status_code == 200:
                    img = Image.open(io.BytesIO(res.content))
                    img.thumbnail((600, 600))
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                        img.save(tmp_file, format="JPEG")
                        tmp_path = tmp_file.name
                    pdf.image(tmp_path, x=45, w=120)
                    os.remove(tmp_path)
            except:
                pdf.set_font("Arial", 'I', 10)
                pdf.cell(0, 10, "[Erro ao descarregar fotografia]", ln=True, align='C')
    saida = pdf.output(dest='S')
    return saida.encode('latin1') if type(saida) is str else bytes(saida)

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
active_tournaments = get_active_tournaments()
past_events = get_past_events_list()

# --- MÓDULO 1: FORMULÁRIO PÚBLICO ---
if menu == "📝 Formulário Público":
    st.title("📝 BBPT League - Deck Check")
    
    if not active_tournaments:
        st.warning("🔒 Não há nenhum torneio ativo neste momento.")
        st.stop()
        
    open_tournaments = [t for t in active_tournaments if t["checkin_open"]]
    
    if not open_tournaments:
        st.warning("🔒 Check-in Fechado. Todos os torneios em curso já iniciaram a fase de Batalhas!")
        st.stop()
    
    target_event = None
    if len(open_tournaments) > 1:
        st.info("⚠️ Estão a decorrer vários eventos em simultâneo. Por favor, seleciona o teu:")
        with st.container(border=True):
            target_event_name = st.radio("Em que torneio vais participar?", [t["event_name"] for t in open_tournaments], index=0)
            target_event = next(t for t in open_tournaments if t["event_name"] == target_event_name)
    else:
        target_event = open_tournaments[0]
        st.info(f"🏆 **A submeter para o evento:** {target_event['event_name']}")
    
    recs_list = get_all_records_cached(target_event["event_name"])
    st.metric("Decks Submetidos (Neste Evento)", len(recs_list))
    
    parts, alias_map = load_parts()
    opcoes_blader = load_players()
    all_available_parts = list(set([p for cat in parts.values() for p in cat]))

    with st.container(border=True):
        c_id1, c_id2 = st.columns([1, 2])
        selected_player = c_id1.selectbox("Blader:", opcoes_blader)
        custom_player = c_id2.text_input("Novo Blader:") if selected_player == "Outro (Novo Jogador)" else ""
        
        # 👇 IMPORTAÇÃO SEGURA DE DECKS DO SUPABASE 👇
        if selected_player not in ["-- Selecionar --", "Outro (Novo Jogador)"]:
            try:
                res_user = supabase.table("bladers").select("*").eq("alias", selected_player).execute()
                if res_user.data:
                    user_data = res_user.data[0]
                    slots_disponiveis = {}
                    
                    for s in ["slot_1", "slot_2", "slot_3", "slot_4", "slot_5"]:
                        slot_val = user_data.get(s)
                        if slot_val:
                            if isinstance(slot_val, str):
                                try: slot_val = json.loads(slot_val)
                                except: continue
                            if "name" in slot_val and slot_val["name"].strip():
                                display_name = f"{s.replace('_', ' ').title()} - {slot_val['name']}"
                            else:
                                display_name = s.replace('_', ' ').title()
                            slots_disponiveis[display_name] = slot_val

                    if slots_disponiveis:
                        st.markdown("---")
                        st.info("💡 Este jogador tem decks gravados. Podes importá-los com a password da tua conta!")
                        with st.expander("📥 Importar Deck Gravado", expanded=False):
                            c_load1, c_load2, c_load3 = st.columns([2, 1.5, 1])
                            deck_escolhido_nome = c_load1.selectbox("Carregar Deck:", ["-- Escolher --"] + list(slots_disponiveis.keys()))
                            pass_import = c_load2.text_input("Password da Conta:", type="password")
                            
                            st.write("") # Spacer vertical
                            if c_load3.button("Validar e Importar", use_container_width=True, type="secondary"):
                                if deck_escolhido_nome != "-- Escolher --":
                                    pass_hash = hashlib.md5(pass_import.encode()).hexdigest()
                                    if pass_hash == user_data.get("password_hash"):
                                        dados_deck = slots_disponiveis[deck_escolhido_nome]
                                        st.session_state.num_combos = dados_deck.get("size", 3)
                                        
                                        for i, c in enumerate(dados_deck["combos"]):
                                            # 👇 O TRADUTOR DE CATEGORIAS 👇
                                            builder_type = c.get("type", "Standard (BX / UX)")
                                            if builder_type in ["Basic (BX)", "Unique (UX)"]:
                                                translated_type = "Standard (BX / UX)"
                                            elif builder_type == "Custom (CX)":
                                                translated_type = "CX"
                                            elif builder_type == "Expand (CXE)":
                                                translated_type = "CX Expanded"
                                            else:
                                                translated_type = builder_type # Apanha o "UX Expanded" que já é igual
                                            
                                            # Aplica as peças traduzidas à memória
                                            st.session_state[f"c_{i}_type"] = translated_type
                                            st.session_state[f"c_{i}_main_blade"] = c.get("main_blade", "--")
                                            st.session_state[f"c_{i}_ratchet"] = c.get("ratchet", "--")
                                            st.session_state[f"c_{i}_bit"] = c.get("bit", "--")
                                            st.session_state[f"c_{i}_lock_chip"] = c.get("lock_chip", "--")
                                            st.session_state[f"c_{i}_assist_blade"] = c.get("assist_blade", "--")
                                            st.session_state[f"c_{i}_metal_blade"] = c.get("metal_blade", "--")
                                            st.session_state[f"c_{i}_over_blade"] = c.get("over_blade", "--")
                                            
                                        st.success("✅ Deck importado com sucesso!")
                                        st.rerun()
                                    else:
                                        st.error("❌ Password incorreta. Acesso negado.")
            except Exception as e:
                pass
                
    with st.container(border=True):
        st.subheader("⚡ Quick Add (Autocomplete Ativo)")
        c1, c2 = st.columns([3, 1])
        with c1:
            current_text = st.text_input(    "Escreve ou cola o teu combo:",value=st.session_state.smart_val,key=f"sk_{st.session_state.keyup_key}",placeholder="Ex: Flat 1-60 Dran Buster")
            if current_text is not None: st.session_state.smart_val = current_text
            
            if st.session_state.smart_val and not st.session_state.smart_val.endswith(" "):
                last_word = st.session_state.smart_val.split()[-1]
                if len(last_word) >= 2:
                    sugestoes = [p for p in all_available_parts if last_word.lower() in p.lower() and p.lower() != last_word.lower()][:5]
                    if sugestoes:
                        st.caption("✨ Sugestões:")
                        cols = st.columns(len(sugestoes))
                        for idx, s in enumerate(sugestoes): cols[idx].button(s, key=f"btn_{s}_{idx}", on_click=append_suggestion, args=(s,))

        if c2.button("Analisar 🔍", use_container_width=True):
            if st.session_state.smart_val.strip(): st.session_state.smart_match = parse_smart_combo(st.session_state.smart_val, parts, alias_map)
                
        if "smart_match" in st.session_state:
            m = st.session_state.smart_match
            if m["type"] in ["Standard (BX / UX)", "UX Expanded"]: display_text = f"{m.get('main_blade')} | {m.get('ratchet')} | {m.get('bit')}"
            elif m["type"] == "CX": display_text = f"{m.get('lock_chip')} | {m.get('main_blade')} | {m.get('assist_blade')} | {m.get('ratchet')} | {m.get('bit')}"
            else: display_text = f"{m.get('lock_chip')} | {m.get('metal_blade')} | {m.get('over_blade')} | {m.get('assist_blade')} | {m.get('ratchet')} | {m.get('bit')}"
                
            st.info(f"🧩 Detetado ({m['type']}): {display_text}")
            idx = st.selectbox("Slot:", [f"Combo {i+1}" for i in range(st.session_state.num_combos)])
            idx_n = int(idx.split(" ")[1]) - 1
            cb1, cb2 = st.columns(2)
            cb1.button("Aplicar", on_click=apply_smart_combo, args=(idx_n, m))
            cb2.button("Cancelar", on_click=cancel_smart_combo)
            
    st.radio("Nº Beyblades:", options=[3, 4], horizontal=True, key="num_combos")
    for i in range(st.session_state.num_combos):
        with st.container(border=True):
            t1, t2 = st.columns([1, 3]); t1.markdown(f"#### Combo {i+1}")
            ct = t2.selectbox("Tipo", ["Standard (BX / UX)", "CX", "CX Expanded", "UX Expanded"], key=f"c_{i}_type", label_visibility="collapsed")
            is_int = st.session_state.get(f"c_{i}_bit", "--") in ["Turbo", "Operate"]
            r_opts = ["Integrada"] if is_int else ["--"] + parts["ratchets"]
            
            if ct == "Standard (BX / UX)":
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.selectbox("Blade", ["--"]+parts["bx_ux_blades"], key=f"c_{i}_main_blade")
                c3.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_bit")
                c2.selectbox("Ratchet", r_opts, key=f"c_{i}_ratchet", disabled=is_int)
            elif ct == "CX":
                c1, c2, c3, c4, c5 = st.columns([1.5, 2, 2, 1.2, 1.2])
                if parts["lock_chips"]: c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"c_{i}_lock_chip")
                else: c1.text_input("Chip", key=f"c_{i}_lock_chip")
                c2.selectbox("Main", ["--"]+parts["cx_blades"], key=f"c_{i}_main_blade")
                c3.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"c_{i}_assist_blade")
                c5.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_bit")
                c4.selectbox("Ratchet", r_opts, key=f"c_{i}_ratchet", disabled=is_int)
            elif ct == "CX Expanded":
                c1, c2, c3, c4, c5, c6 = st.columns([1.5, 2, 2, 2, 1.2, 1.2])
                if parts["lock_chips"]: c1.selectbox("Chip", ["--"]+parts["lock_chips"], key=f"c_{i}_lock_chip")
                else: c1.text_input("Chip", key=f"c_{i}_lock_chip")
                c2.selectbox("Metal", ["--"]+parts["metal_blades"], key=f"c_{i}_metal_blade")
                c3.selectbox("Over", ["--"]+parts["over_blades"], key=f"c_{i}_over_blade")
                c4.selectbox("Assist", ["--"]+parts["assist_blades"], key=f"c_{i}_assist_blade")
                c6.selectbox("Bit", ["--"]+parts["bits"], key=f"c_{i}_bit")
                c5.selectbox("Ratchet", r_opts, key=f"c_{i}_ratchet", disabled=is_int)
            elif ct == "UX Expanded":
                c1, c2 = st.columns([2, 1])
                blade_opts = ["--"] + parts.get("ux_expanded_blades", [])
                curr_blade = st.session_state.get(f"c_{i}_main_blade", "--")
                if curr_blade not in blade_opts and curr_blade != "--": blade_opts.append(curr_blade)
                c1.selectbox("Blade", blade_opts, key=f"c_{i}_main_blade")
                bits_val = ["--"] + [b for b in parts["bits"] if b not in ["Turbo", "Operate"]]
                curr_bit = st.session_state.get(f"c_{i}_bit", "--")
                if curr_bit not in bits_val and curr_bit != "--": bits_val.append(curr_bit)
                c2.selectbox("Bit", bits_val, key=f"c_{i}_bit")
                st.session_state[f"c_{i}_ratchet"] = "Integrada na Blade"
                
    with st.container(border=True):
        up = st.file_uploader("Foto:", type=['png', 'jpg', 'jpeg'])
        if up: st.image(up, width=300)
        
    if st.button("Submeter Deck 🚀", use_container_width=True, type="primary"):
        name = custom_player if selected_player == "Outro (Novo Jogador)" else selected_player
        combos, missing_parts = [], False
        has_duplicates, dup_error_msg = False, ""
        used_blades, used_ratchets, used_bits, used_chips, used_assist, used_metal = set(), set(), set(), set(), set(), set()
        
        for i in range(st.session_state.num_combos):
            ct = st.session_state[f"c_{i}_type"]; cd = {"type": ct, "combo_number": i+1}
            ks = ["main_blade", "ratchet", "bit"] if ct in ["Standard (BX / UX)", "UX Expanded"] else ["lock_chip", "main_blade", "assist_blade", "ratchet", "bit"] if ct == "CX" else ["lock_chip", "metal_blade" , "over_blade" , "assist_blade", "ratchet", "bit"]
            
            for k in ks:
                v = st.session_state.get(f"c_{i}_{k}", "--")
                if ct == "UX Expanded" and k == "ratchet": v = "Integrada na Blade"
                elif k == "ratchet" and st.session_state.get(f"c_{i}_bit", "--") in ["Turbo", "Operate"]: v = "Integrada"
                cd[k] = v
                if v == "--" or not str(v).strip(): missing_parts = True
            combos.append(cd)

            if not missing_parts and not has_duplicates:
                b = cd.get('over_blade', cd.get('main_blade', '--'))
                if b != '--':
                    base = re.sub(r'\s*\(.*?\)\s*', '', str(b)).strip().lower()
                    if base in used_blades: has_duplicates = True; dup_error_msg = f"A Blade '{b}' está repetida!"
                    used_blades.add(base)
                r = cd.get('ratchet', '--')
                if ct == "UX Expanded": r = "Integrada na Blade"
                elif cd.get('bit', '--') in ["Turbo", "Operate"]: r = "Integrada"
                if r != '--' and "Integrada" not in r:
                    if r in used_ratchets: has_duplicates = True; dup_error_msg = f"A Ratchet '{r}' está repetida!"
                    used_ratchets.add(r)
                bt = cd.get('bit', '--')
                if bt != '--':
                    if bt in used_bits: has_duplicates = True; dup_error_msg = f"A Bit '{bt}' está repetida!"
                    used_bits.add(bt)
                if 'assist_blade' in cd and cd['assist_blade'] != '--':
                    if cd['assist_blade'] in used_assist: has_duplicates = True; dup_error_msg = f"Assist Blade '{cd['assist_blade']}' repetida!"
                    used_assist.add(cd['assist_blade'])
                if 'metal_blade' in cd and cd['metal_blade'] != '--':
                    if cd['metal_blade'] in used_metal: has_duplicates = True; dup_error_msg = f"Metal Blade '{cd['metal_blade']}' repetida!"
                    used_metal.add(cd['metal_blade'])
                if 'lock_chip' in cd and cd['lock_chip'] != '--' and cd['lock_chip'].strip() != '':
                    chip = cd['lock_chip'].strip().lower()
                    if chip in used_chips: has_duplicates = True; dup_error_msg = f"Lock Chip '{cd['lock_chip']}' repetido!"
                    used_chips.add(chip)

            if name == "-- Selecionar Jogador --" or not name.strip(): 
                st.error("⚠️ Por favor, escolhe um jogador da lista ou seleciona 'Outro (Novo Jogador)' para criar um novo.")
            elif missing_parts: 
                st.error("⚠️ Preenche todas as opções do teu deck.")
            elif has_duplicates: 
                st.error(f"⚠️ **Regra de Deck Check:** {dup_error_msg}")
            elif not up: 
                st.error("⚠️ Faltou anexar a prova fotográfica do deck!")
            else:
                with st.spinner("A gravar submissão..."):
                    try:
                        save_submission_cloud(name, combos, up, target_event["event_name"])
                        st.success("✅ O teu Deck foi submetido na base de dados oficial!")
                        st.balloons()
                    except Exception as err:
                        st.error(str(err))

# --- MÓDULO 2: CONSULTA PÚBLICA ---
elif menu == "🔍 Consulta Pública":
    st.title("🔍 Consulta Pública de Decks")
    st.markdown("Consulta as configurações de equipas submetidas.")
    nomes_ativos = [t["event_name"] for t in active_tournaments]
    todos_eventos = sorted(list(set(nomes_ativos + past_events)))
    
    if todos_eventos:
        evento_selecionado = st.selectbox("Escolher Evento para Consultar:", todos_eventos)
        recs_public = get_all_records_cached(evento_selecionado)
        st.metric("Total Decks Selados", len(recs_public))
        st.divider()
        for d in recs_public:
            with st.expander(f"👤 Blader: {d['Player']}"):
                col_c, col_i = st.columns([2, 1])
                with col_c:
                    for i in range(1, 5):
                        if d.get(f'Combo_{i}'): st.write(f"🔹 **Combo {i}:** {d[f'Combo_{i}']}")
                if d['Image_URL']: col_i.image(d['Image_URL'], use_container_width=True)
    else:
        st.info("Ainda não existem registos de eventos.")

# --- MÓDULO 3: PAINEL DE ORGANIZAÇÃO (SÓ ADMIN) ---
elif menu == "⚙️ Painel de Organização" and st.session_state.user_role == "admin":
    st.title("🛡️ Admin")
            
    st.subheader("📢 Gestão de Eventos")
    if past_events:
        with st.expander("📂 Histórico de Eventos (Reabrir)", expanded=False):
            sel_past = st.selectbox("Selecionar evento antigo:", ["-- Escolher --"] + past_events)
            if sel_past != "-- Escolher --":
                if st.button(f"Ativar '{sel_past}'"): 
                    set_active_tournament(sel_past)
                    st.rerun()
    st.divider()
    
    col1, col2 = st.columns(2)
    ev_n = col1.text_input("Nome do Novo Torneio:")
    if col1.button("CRIAR EVENTO", type="primary"):
        if ev_n.strip():
            set_active_tournament(ev_n.strip())
            st.rerun()
        else:
            st.warning("Digita o nome do torneio primeiro!")
            
    if col2.button("Limpar Cache 🔄"): st.cache_data.clear(); st.rerun()
    st.divider()
    
    if active_tournaments:
        st.markdown("### 🕹️ Controlo dos Torneios Ativos")
        st.caption("Podes ter até 3 torneios a decorrer e gerir a fase de cada um individualmente.")
        for t in active_tournaments:
            with st.container(border=True):
                st.markdown(f"**Torneio:** `{t['event_name']}`")
                colA, colB = st.columns(2)
                if t["checkin_open"]:
                    colA.success("🟢 Check-in Aberto")
                    if colA.button("🔒 Fechar Check-in (Iniciar Batalhas)", key=f"close_{t['id']}", use_container_width=True):
                        toggle_checkin(t["id"], False)
                        st.rerun()
                else:
                    colA.error("🔴 Batalhas em Curso")
                    if colA.button("🔓 Reabrir Check-in (Bloquear Batalhas)", key=f"open_{t['id']}", use_container_width=True):
                        toggle_checkin(t["id"], True)
                        st.rerun()
                        
                if colB.button("🗄️ Arquivar Torneio (Terminar)", key=f"arch_{t['id']}", type="secondary", use_container_width=True):
                    archive_tournament(t["id"])
                    st.rerun()
    else:
        st.info("Não tens nenhum torneio a decorrer de momento.")
        
    st.divider()
    
    st.subheader("👀 Verificar Decks Submetidos")
    nomes_ativos = [t["event_name"] for t in active_tournaments]
    todos_eventos = sorted(list(set(nomes_ativos + past_events)))
    
    if todos_eventos:
        evento_verificar = st.selectbox("Escolher Evento para Visualizar:", todos_eventos)
        recs_admin = get_all_records_cached(evento_verificar)
        st.metric(f"Total de Decks em '{evento_verificar}'", len(recs_admin))
        st.divider()
        for d in recs_admin:
            with st.expander(f"👤 {d['Player']}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    for i in range(1, 5):
                        if d.get(f'Combo_{i}'): st.write(f"**Combo {i}:** {d[f'Combo_{i}']}")
                    st.markdown("---")
                    confirm_key = f"del_mode_{d['id']}"
                    if confirm_key not in st.session_state: st.session_state[confirm_key] = False
                        
                    if not st.session_state[confirm_key]:
                        if st.button("Eliminar Deck 🗑️", key=f"del_trigger_{d['id']}", type="secondary"):
                            st.session_state[confirm_key] = True
                            st.rerun()
                    else:
                        st.warning("Apagar permanentemente este deck?")
                        btn_col1, btn_col2 = st.columns(2)
                        if btn_col1.button("✅ Confirmar", key=f"del_yes_{d['id']}", type="primary", use_container_width=True):
                            supabase.table("tournament_registrations").delete().eq("id", d["id"]).execute()
                            st.session_state[confirm_key] = False
                            st.cache_data.clear()
                            st.rerun()
                        if btn_col2.button("❌ Cancelar", key=f"del_no_{d['id']}", type="secondary", use_container_width=True):
                            st.session_state[confirm_key] = False
                            st.rerun()
                if d['Image_URL']: c2.image(d['Image_URL'])