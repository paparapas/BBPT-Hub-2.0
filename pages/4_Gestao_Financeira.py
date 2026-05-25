import streamlit as st
import pandas as pd
import os
import base64
from streamlit_cookies_controller import CookieController
from db_connection import supabase


st.set_page_config(page_title="Gestão Financeira", page_icon="💰", layout="wide")

# --- PASSWORDS DE ACESSO ---
ADMIN_PASSWORD = "bbpt-paparapas" 
JUDGE_PASSWORD = "bbpt-judge"
FINANCE_PASSWORD = "bbpt-finance"

# ==========================================
# GESTÃO GLOBAL DE LOGIN (SIDEBAR AJUSTADA)
# ==========================================
from streamlit_cookies_controller import CookieController
import hashlib

# 1. INICIALIZAR AS VARIÁVEIS NA MEMÓRIA ANTES DE QUALQUER LEITURA
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "finance_auth" not in st.session_state:
    st.session_state.finance_auth = False

# 2. LER COOKIES
controller = CookieController()
cookie_role = controller.get('user_role')
cookie_finance = controller.get('finance_auth')

# 3. SINCRONIZAR COOKIES COM A MEMÓRIA
if cookie_role in ["owner", "admin", "judge"]:
    st.session_state.user_role = cookie_role

if cookie_finance == 'true':
    st.session_state.finance_auth = True

logo_path = "logo.png" if os.path.exists("logo.png") else "../logo.png"
has_logo = os.path.exists(logo_path)

with st.sidebar:
    if has_logo:
        with open(logo_path, "rb") as image_file: encoded_logo = base64.b64encode(image_file.read()).decode()
        st.markdown(f"<div><img src='data:image/png;base64,{encoded_logo}' width='150' style='margin-right:10px;'><h1 style='display:inline;font-size:1.8rem;'></h1></div>", unsafe_allow_html=True)
    else: st.title("🛡️ BBPT App")
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

# --- BLOQUEIO PARA QUEM NÃO É ADMIN ---
if st.session_state.user_role != "admin":
    st.error("🛑 Acesso Restrito: Apenas Administradores podem aceder à Gestão Financeira.")
    st.stop()

# --- BLOQUEIO DE SEGUNDA CAMADA (CADEADO FINANCEIRO) ---
if not st.session_state.finance_auth:
    st.warning("🔐 Secção Financeira Trancada.")
    st.info("Mesmo sendo Administrador, precisas da palavra-passe financeira para abrir o cofre.")
    with st.container(border=True):
        fin_pwd = st.text_input("Password Financeira:", type="password")
        if st.button("Desbloquear Cofre 🔓", type="primary"):
            if fin_pwd.strip() == FINANCE_PASSWORD:
                st.session_state.finance_auth = True
                controller.set('finance_auth', 'true', max_age=43200)
                st.rerun()
            else:
                st.error("Password Financeira Incorreta!")
    st.stop()

# ==========================================
# CÓDIGO DA GESTÃO FINANCEIRA
# ==========================================
st.title("💰 Checker Financeiro e Check-in")
st.markdown("Controla as presenças, taxas do torneio, método de pagamento e donativos dos participantes.")

@st.cache_data(ttl=2)
def get_active_tournaments():
    res = supabase.table("tournaments").select("*").eq("is_active", True).execute()
    return res.data

def update_tournament_fees(t_id, entry_fee, league_quota):
    supabase.table("tournaments").update({"entry_fee": entry_fee, "league_quota": league_quota}).eq("id", t_id).execute()
    st.cache_data.clear()

def fetch_registrations(tournament_id):
    res = supabase.table("tournament_registrations").select("id, blader_id, paid_entry, paid_quota, is_present, donation, payment_method, bladers(alias)").eq("tournament_id", tournament_id).execute()
    return res.data

active_tournaments = get_active_tournaments()

if not active_tournaments:
    st.warning("⚠️ Não há nenhum torneio ativo para gerir. Abre um no Painel de Organização.")
    st.stop()

if len(active_tournaments) > 1:
    st.info("⚠️ Estão a decorrer vários eventos. Seleciona a caixa qual queres gerir:")
    tourney_names = [t["name"] for t in active_tournaments]
    selected_name = st.selectbox("Torneio Ativo:", tourney_names)
    active_tourney = next(t for t in active_tournaments if t["name"] == selected_name)
    st.divider()
else:
    active_tourney = active_tournaments[0]

with st.expander("⚙️ Definir Valores a Pedir nesta Etapa", expanded=False):
    col_f1, col_f2, col_f3 = st.columns([1, 1, 1])
    current_entry = float(active_tourney.get("entry_fee", 2.0) or 2.0)
    current_quota = float(active_tourney.get("league_quota", 1.0) or 1.0)
    
    new_entry = col_f1.number_input("Valor da Inscrição (€):", min_value=0.0, value=current_entry, step=0.5)
    new_quota = col_f2.number_input("Valor da Quota da Liga (€):", min_value=0.0, value=current_quota, step=0.5)
    
    if col_f3.button("🔄 Atualizar Valores", use_container_width=True):
        update_tournament_fees(active_tourney["id"], new_entry, new_quota)
        st.success("Valores atualizados para este torneio!")
        st.rerun()

st.info(f"🏆 A gerir o Torneio: **{active_tourney['name']}** |  Inscrição: **{new_entry}€** |  Quota: **{new_quota}€**")

registrations = fetch_registrations(active_tourney["id"])

if not registrations:
    st.info("Ainda não há jogadores submetidos neste torneio específico.")
    st.stop()

data_for_grid = []
for r in registrations:
    data_for_grid.append({
        "ID_Registo": r["id"],
        "Blader": r["bladers"]["alias"] if r.get("bladers") else "Desconhecido",
        "Presente?": r.get("is_present", False),
        "Inscrição Paga?": r.get("paid_entry", False),
        "Quota Paga?": r.get("paid_quota", False),
        "Método Pag.": r.get("payment_method", "Numerário") or "Numerário",
        "Donativo (€)": float(r.get("donation", 0.0) or 0.0)
    })

df = pd.DataFrame(data_for_grid)

# Lógica matemática para separar os valores pagos por método
df["Valor Total Pago"] = (df["Inscrição Paga?"].astype(int) * new_entry) + (df["Quota Paga?"].astype(int) * new_quota) + df["Donativo (€)"]

total_numerario = df[df["Método Pag."] == "Numerário"]["Valor Total Pago"].sum()
total_mbway = df[df["Método Pag."] == "MBWay"]["Valor Total Pago"].sum()

total_inscritos = len(df)
total_presentes = df["Presente?"].sum()
receita_inscricoes = df["Inscrição Paga?"].sum() * new_entry
receita_quotas = df["Quota Paga?"].sum() * new_quota
total_donativos = df["Donativo (€)"].sum()
caixa_total = receita_inscricoes + receita_quotas + total_donativos

# Top Metrics
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Inscritos", f"{total_inscritos}")
col2.metric("Presenças", f"{total_presentes}")
col3.metric("Caixa Inscrições", f"{receita_inscricoes}€")
col4.metric("Caixa Quotas", f"{receita_quotas}€")
col5.metric("❤️ Total Donativos", f"{total_donativos}€")

st.markdown("---")
# Métricas Totais e de Divisão
m1, m2, m3 = st.columns([2, 1, 1])
m1.metric("💰 CAIXA TOTAL DESTE EVENTO", f"{caixa_total}€")
m2.metric("💵 Físico (Numerário)", f"{total_numerario}€")
m3.metric("📱 Digital (MBWay)", f"{total_mbway}€")

st.markdown("---")
st.subheader("📋 Grelha de Controlo Financeiro")

edited_df = st.data_editor(
    df.drop(columns=["Valor Total Pago"]), # Removemos a coluna de cálculo auxiliar da vista
    hide_index=True,
    use_container_width=True,
    disabled=["Blader", "ID_Registo"],
    column_config={
        "ID_Registo": None, 
        "Blader": st.column_config.TextColumn("Nickname", width="medium"),
        "Presente?": st.column_config.CheckboxColumn("Presente (Check-in)", default=False),
        "Inscrição Paga?": st.column_config.CheckboxColumn(f"Inscrição ({new_entry}€)", default=False),
        "Quota Paga?": st.column_config.CheckboxColumn(f"Quota ({new_quota}€)", default=False),
        "Método Pag.": st.column_config.SelectboxColumn("Método", options=["Numerário", "MBWay"], default="Numerário"),
        "Donativo (€)": st.column_config.NumberColumn("Donativo (€)", min_value=0.0, format="%.2f€", default=0.0)
    }
)

st.markdown("---")
col_save, col_export = st.columns([3, 1])

with col_save:
    if st.button("💾 Guardar Alterações Financeiras", type="primary", use_container_width=True):
        with st.spinner("A sincronizar dados..."):
            updates = []
            for index, row in edited_df.iterrows():
                orig_row = df.iloc[index]
                if (row["Presente?"] != orig_row["Presente?"] or 
                    row["Inscrição Paga?"] != orig_row["Inscrição Paga?"] or
                    row["Quota Paga?"] != orig_row["Quota Paga?"] or 
                    row["Método Pag."] != orig_row["Método Pag."] or
                    row["Donativo (€)"] != orig_row["Donativo (€)"]):
                    
                    updates.append({
                        "id": row["ID_Registo"], 
                        "is_present": row["Presente?"],
                        "paid_entry": row["Inscrição Paga?"], 
                        "paid_quota": row["Quota Paga?"], 
                        "payment_method": row["Método Pag."],
                        "donation": row["Donativo (€)"]
                    })
            if updates:
                try:
                    supabase.table("tournament_registrations").upsert(updates).execute()
                    st.success(f"✅ {len(updates)} registo(s) financeiro(s) atualizado(s)!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao guardar: {e}")
            else:
                st.info("Nenhuma alteração detetada.")

with col_export:
    export_df = edited_df.drop(columns=["ID_Registo"]).copy()
    export_df["Presente?"] = export_df["Presente?"].map({True: "Presente", False: "Ausente"})
    export_df["Inscrição Paga?"] = export_df["Inscrição Paga?"].map({True: f"{new_entry}€ Pago", False: "Não Pago"})
    export_df["Quota Paga?"] = export_df["Quota Paga?"].map({True: f"{new_quota}€ Pago", False: "Não Pago"})
    export_df["Donativo (€)"] = export_df["Donativo (€)"].apply(lambda x: f"{x}€")
    
    csv_data = export_df.to_csv(index=False).encode('utf-8-sig')
    file_name = f"Financeiro_{active_tourney['name'].replace(' ', '_')}.csv"
    st.download_button(label="📥 Exportar para CSV", data=csv_data, file_name=file_name, mime="text/csv", use_container_width=True)