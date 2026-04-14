import streamlit as st
import requests
import base64
import json

# Endereço do nosso motor FastAPI
API_URL = "http://localhost:8000"

st.set_page_config(page_title="Portal Ambiental", page_icon="🌿", layout="centered")

# ==========================================
# GERENCIAMENTO DE SESSÃO
# ==========================================
if "token" not in st.session_state:
    st.session_state["token"] = None

# ==========================================
# FUNÇÕES DE COMUNICAÇÃO COM A API
# ==========================================
def fazer_login(email, senha):
    url = f"{API_URL}/token"
    dados = {"username": email, "password": senha}
    resposta = requests.post(url, data=dados)
    
    if resposta.status_code == 200:
        st.session_state["token"] = resposta.json().get("access_token")
        return True
    return False

def fazer_logout():
    st.session_state["token"] = None

def extrair_dados_do_token(token):
    """Abre o Token JWT para descobrir o ID do cliente sem precisar perguntar ao banco"""
    try:
        # O JWT tem 3 partes separadas por ponto. O "recheio" é a parte 1.
        payload = token.split(".")[1]
        # Adiciona o preenchimento necessário para o base64 do Python não reclamar
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.b64decode(payload).decode("utf-8"))
    except Exception:
        return {"cliente_id": 1} # Fallback de segurança

def buscar_documentos(token, cliente_id):
    """Vai até a API e pede os documentos usando o crachá de segurança"""
    url = f"{API_URL}/clientes/{cliente_id}/documentos/"
    # AQUI ESTÁ A CHAVE DE ACESSO:
    headers = {"Authorization": f"Bearer {token}"}
    
    resposta = requests.get(url, headers=headers)
    if resposta.status_code == 200:
        return resposta.json()
    return []

# ==========================================
# TELA DE LOGIN (Se não tem token)
# ==========================================
if st.session_state["token"] is None:
    st.image("https://cdn-icons-png.flaticon.com/512/2942/2942185.png", width=100)
    st.title("Portal Ambiental")
    st.markdown("Bem-vindo! Acesse seus laudos e documentos técnicos.")
    st.write("---")
    
    email = st.text_input("E-mail corporativo")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar", type="primary"):
        if email and senha:
            if fazer_login(email, senha):
                st.rerun()
            else:
                st.error("E-mail ou senha incorretos.")
        else:
            st.warning("Preencha o e-mail e a senha.")

# ==========================================
# ÁREA DO CLIENTE LOGADO (Se tem token)
# ==========================================
else:
    # 1. Descobrimos quem é o cliente
    dados_usuario = extrair_dados_do_token(st.session_state["token"])
    cliente_id = dados_usuario.get("cliente_id")
    email_logado = dados_usuario.get("sub")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🌿 Área do Cliente")
        st.caption(f"Logado como: {email_logado}")
    with col2:
        if st.button("Sair (Logout)"):
            fazer_logout()
            st.rerun()
            
    st.write("---")
    
    # 2. Buscamos os documentos lá no FastAPI
    st.subheader("Meus Laudos e Documentos")
    documentos = buscar_documentos(st.session_state["token"], cliente_id)
    
    if documentos:
        # Mostra cada documento em uma caixinha bonitinha
        for doc in documentos:
            data_formatada = doc['data_upload'][:10] # Pega só o YYYY-MM-DD
            
            with st.container():
                st.info(f"📄 **{doc['tipo_documento']}**")
                st.write(f"📅 **Data de Upload:** {data_formatada}")
                st.write(f"🔗 [Clique aqui para baixar o arquivo]({API_URL}/{doc['url_arquivo']})")
                st.write("---")
    else:
        st.warning("Nenhum documento encontrado para a sua empresa no momento.")