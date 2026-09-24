import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def _create_client() -> Client:
    # Só uma ligação bem-sucedida fica em cache.
    # Se der erro, o Streamlit NÃO guarda o erro e tenta de novo no próximo carregamento.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


def init_connection():
    try:
        return _create_client()
    except Exception as e:
        st.error(f"Erro ao ligar: {e}")
        return None


supabase = init_connection()
