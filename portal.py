import streamlit as st
import requests
import base64
import json
from streamlit_js_eval import get_geolocation
from streamlit_autorefresh import st_autorefresh

# Endereço do nosso motor FastAPI
API_URL = "https://aplicacao-ambiental.onrender.com"

st.set_page_config(page_title="Portal Ambiental", page_icon="🌿", layout="centered")

# ==========================================
# 1. CAPTURA DE LOCALIZAÇÃO (GPS)
# ==========================================
st.sidebar.subheader("📍 Segurança e Auditoria")
st.sidebar.caption("Sua localização é registrada para conformidade técnica.")

localizacao = get_geolocation()
latitude = None
longitude = None

if localizacao and 'coords' in localizacao:
    latitude = localizacao['coords'].get('latitude')
    longitude = localizacao['coords'].get('longitude')
    st.sidebar.success("Sinal GPS conectado.")
elif localizacao is None:
    st.sidebar.info("Aguardando sinal do GPS...")
else:
    st.sidebar.warning("Localização não disponível.")

# ==========================================
# 2. FUNÇÃO DE DOWNLOAD E AUDITORIA
# ==========================================
def registrar_e_preparar_download(doc):
    dados_auditoria = {
        "evento": "DOWNLOAD_DOCUMENTO",
        "detalhes": f"ID: {doc['id']} - Tipo: {doc['tipo_documento']}",
        "latitude": latitude,
        "longitude": longitude
    }
    
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    
    try:
        # Registra no banco
        requests.post(f"{API_URL}/auditoria/", json=dados_auditoria, headers=headers)
        
        # Busca o arquivo real
        url_arquivo = f"{API_URL}/{doc['url_arquivo']}".replace(" ", "%20")
        res_arquivo = requests.get(url_arquivo)
        
        if res_arquivo.status_code == 200:
            return res_arquivo.content
    except Exception:
        st.error("Erro na validação de segurança do download.")
    return None

# ==========================================
# GERENCIAMENTO DE SESSÃO E API
# ==========================================
if "token" not in st.session_state:
    st.session_state["token"] = None

def fazer_login(email, senha):
    resposta = requests.post(f"{API_URL}/token", data={"username": email, "password": senha})
    if resposta.status_code == 200:
        st.session_state["token"] = resposta.json().get("access_token")
        return True
    return False

def extrair_dados_do_token(token):
    try:
        payload = token.split(".")[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.b64decode(payload).decode("utf-8"))
    except:
        return {}

# ==========================================
# TELA DE LOGIN
# ==========================================
if st.session_state["token"] is None:
    st.title("🌿 Portal Ambiental")
    st.markdown("Acesse seus laudos de forma segura.")
    
    email = st.text_input("E-mail corporativo")
    senha = st.text_input("Senha", type="password")
    if st.button("Entrar", type="primary"):
        if fazer_login(email, senha):
            st.rerun()
        else:
            st.error("E-mail ou senha incorretos.")

# ==========================================
# ÁREA DO CLIENTE LOGADO
# ==========================================
else:
    # --- SISTEMA DE STATUS ONLINE (BATIMENTO CARDÍACO) ---
    # Atualiza silenciosamente a cada 60 segundos
    st_autorefresh(interval=60000, key="frequencia_online")
    
    try:
        headers_ping = {"Authorization": f"Bearer {st.session_state['token']}"}
        requests.post(f"{API_URL}/usuarios/ping", headers=headers_ping)
    except:
        pass # Silencia se a rede falhar momentaneamente

    # --- INTERFACE ---
    dados_usuario = extrair_dados_do_token(st.session_state["token"])
    cliente_id = dados_usuario.get("cliente_id")
    email_logado = dados_usuario.get("sub")
    
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🌿 Meus Documentos")
        st.caption(f"Logado como: {email_logado}")
    with col2:
        if st.button("Sair"):
            st.session_state["token"] = None
            st.rerun()
            
    st.write("---")
    
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    resp = requests.get(f"{API_URL}/clientes/{cliente_id}/documentos/", headers=headers)
    
    if resp.status_code == 200:
        documentos = resp.json()
        for doc in documentos:
            with st.expander(f"📄 {doc['tipo_documento']} - {doc['data_upload'][:10]}"):
                nome_arquivo_limpo = doc['url_arquivo'].split("/")[-1]
                
                conteudo_arquivo = registrar_e_preparar_download(doc)
                
                if conteudo_arquivo:
                    st.download_button(
                        label="⬇️ Baixar e Registrar Acesso",
                        data=conteudo_arquivo,
                        file_name=nome_arquivo_limpo,
                        mime="application/pdf",
                        key=f"btn_{doc['id']}"
                    )
                else:
                    st.error("Arquivo indisponível para download.")
    else:
        st.info("Nenhum laudo encontrado para sua conta.")