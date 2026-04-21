import streamlit as st
import requests
import base64
import json
from streamlit_js_eval import get_geolocation
from streamlit_autorefresh import st_autorefresh
from streamlit_javascript import st_javascript


# Configurações iniciais da página
# Endereço do nosso motor FastAPI
API_URL = "https://aplicacao-ambiental.onrender.com"

st.set_page_config(page_title="Portal Ambiental", page_icon="🌿", layout="centered")

#######################captura do IP real do usuário via JavaScript (usando ipify)
# 2. Captura do IP (JavaScript)
js_code = 'await fetch("https://api64.ipify.org?format=json").then(res => res.json()).then(data => data.ip)'
ip_usuario = st_javascript(js_code)

# --- ESPERA ESTRATÉGICA ---
# Se o IP ainda não foi capturado, mostramos um aviso rápido
if not ip_usuario:
    with st.spinner("Protegendo sua conexão..."):
        time.sleep(1.5) # 1.5 segundos é o suficiente para o JS responder
        st.rerun() # Recarrega a página agora com o IP preenchido

def registrar_auditoria_portal(doc):
    st.toast(f"Registrando acesso para {doc['tipo_documento']}...") # Isso aparecerá no seu celular
    # Se o JS ainda não carregou, o ip_usuario será 0 ou None. 
    # Vamos garantir que ele envie uma string para a API não ignorar.
    envio_ip = str(ip_usuario) if ip_usuario else "Aguardando JS..."
    
    dados_auditoria = {
        "evento": "DOWNLOAD_DOCUMENTO",
        "detalhes": f"Baixou: {doc['tipo_documento']}",
        "ip": envio_ip, 
        "latitude": latitude,
        "longitude": longitude
    }
    
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    requests.post(f"{API_URL}/auditoria/", json=dados_auditoria, headers=headers)

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
def registrar_auditoria_portal(doc):
    """Envia o log para a API apenas quando o usuário clica no botão"""
    dados_auditoria = {
        "evento": "DOWNLOAD_DOCUMENTO",
        "detalhes": f"Baixou: {doc['tipo_documento']} (ID: {doc['id']})",
        "latitude": latitude,
        "longitude": longitude
    }
    headers = {"Authorization": f"Bearer {st.session_state['token']}"}
    try:
        # Note que não passamos o IP aqui. 
        # O main.py vai detectar o IP real automaticamente pelos headers!
        requests.post(f"{API_URL}/auditoria/", json=dados_auditoria, headers=headers)
    except:
        pass
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
    st_autorefresh(interval=60000, key="frequencia_online")
    
    try:
        headers_ping = {"Authorization": f"Bearer {st.session_state['token']}"}
        requests.post(f"{API_URL}/usuarios/ping", headers=headers_ping)
    except:
        pass

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
            # Melhorando a visualização da data no portal
            data_simples = doc['data_upload'][:10] # Pega AAAA-MM-DD
            
            with st.expander(f"📄 {doc['tipo_documento']} - {data_simples}"):
                nome_arquivo_limpo = doc['url_arquivo'].split("/")[-1]
                url_completa = f"{API_URL}/{doc['url_arquivo']}".replace(" ", "%20")
                
                try:
                    # 1. Buscamos o conteúdo do arquivo
                    res_arq = requests.get(url_completa, headers=headers)
                    
                    if res_arq.status_code == 200:
                        # 2. O BOTÃO "DEDO-DURO"
                        # Ele só chama a função de auditoria quando é CLICADO
                        st.download_button(
                            label="⬇️ Baixar Laudo Oficial",
                            data=res_arq.content,
                            file_name=nome_arquivo_limpo,
                            mime="application/pdf",
                            key=f"btn_{doc['id']}",
                            on_click=registrar_auditoria_portal, # <--- Chama a função
                            args=(doc,) # <--- Passa os dados do documento para a função
                        )
                    else:
                        st.error("Arquivo não encontrado no servidor.")
                except Exception as e:
                    st.error(f"Erro ao preparar download: {e}")
    else:
        st.info("Nenhum laudo encontrado para sua conta.")