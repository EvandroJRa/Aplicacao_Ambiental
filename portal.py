import streamlit as st
import requests
import base64
import json
import time
from streamlit_js_eval import get_geolocation
from streamlit_autorefresh import st_autorefresh
from streamlit_javascript import st_javascript

# ==========================================
# CONFIGURAÇÃO INICIAL
# ==========================================
API_URL = "https://aplicacao-ambiental.onrender.com"

st.set_page_config(
    page_title="Portal Ambiental",
    page_icon="🌿",
    layout="centered"
)

# ==========================================
# CAPTURA DE IP VIA JAVASCRIPT
# ==========================================
js_code = 'await fetch("https://api64.ipify.org?format=json").then(res => res.json()).then(data => data.ip)'
ip_usuario = st_javascript(js_code)

# Aguarda o JS retornar o IP antes de continuar
# ip_usuario == 0 significa que o componente ainda não executou
if ip_usuario == 0:
    with st.spinner("Carregando..."):
        time.sleep(1.5)
        st.rerun()

# ==========================================
# CAPTURA DE LOCALIZAÇÃO GPS
# ==========================================
st.sidebar.subheader("📍 Segurança e Auditoria")
st.sidebar.caption("Sua localização é registrada para conformidade técnica.")

localizacao = get_geolocation()
latitude = None
longitude = None

if localizacao and "coords" in localizacao:
    latitude = localizacao["coords"].get("latitude")
    longitude = localizacao["coords"].get("longitude")
    st.sidebar.success("✅ Sinal GPS conectado.")
elif localizacao is None:
    st.sidebar.info("⏳ Aguardando sinal do GPS...")
else:
    st.sidebar.warning("⚠️ Localização não disponível.")

# ==========================================
# GERENCIAMENTO DE SESSÃO
# ==========================================
if "token" not in st.session_state:
    st.session_state["token"] = None

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def fazer_login(email: str, senha: str) -> bool:
    """Autentica o usuário e armazena o token na sessão."""
    try:
        resposta = requests.post(
            f"{API_URL}/token",
            data={"username": email, "password": senha},
            timeout=10
        )
        if resposta.status_code == 200:
            st.session_state["token"] = resposta.json().get("access_token")
            return True
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão: {e}")
        return False


def extrair_dados_do_token(token: str) -> dict:
    """Decodifica o payload do JWT sem verificação de assinatura."""
    try:
        payload = token.split(".")[1]
        # Adiciona padding necessário para base64
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.b64decode(payload).decode("utf-8"))
    except Exception:
        return {}


def verificar_token_expirado(dados_token: dict) -> bool:
    """Verifica se o token JWT já expirou."""
    exp = dados_token.get("exp")
    if exp and time.time() > exp:
        return True
    return False


def registrar_auditoria(token: str, doc: dict):
    """
    Registra o evento de download na API.
    Chamada apenas quando o usuário efetivamente clica para baixar.
    """
    dados_auditoria = {
        "evento": "DOWNLOAD_DOCUMENTO",
        "detalhes": f"Baixou: {doc['tipo_documento']} (ID: {doc['id']})",
        "ip": str(ip_usuario) if ip_usuario and ip_usuario != 0 else None,
        "latitude": latitude,
        "longitude": longitude
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resposta = requests.post(
            f"{API_URL}/auditoria/",
            json=dados_auditoria,
            headers=headers,
            timeout=10
        )
        if resposta.status_code not in (200, 201):
            st.warning(f"Auditoria retornou status inesperado: {resposta.status_code}")
    except requests.exceptions.RequestException as e:
        st.warning(f"Falha ao registrar auditoria: {e}")


def buscar_arquivo(url: str, token: str) -> bytes | None:
    """Faz o download do arquivo PDF do servidor."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resposta = requests.get(url, headers=headers, timeout=15)
        if resposta.status_code == 200:
            return resposta.content
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar arquivo: {e}")
        return None


def enviar_ping(token: str):
    """Mantém a sessão ativa no servidor (heartbeat)."""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        requests.post(f"{API_URL}/usuarios/ping", headers=headers, timeout=5)
    except requests.exceptions.RequestException:
        pass  # Ping falhou — não é crítico, apenas ignora


# ==========================================
# TELA DE LOGIN
# ==========================================
if st.session_state["token"] is None:
    st.title("🌿 Portal Ambiental")
    st.markdown("Acesse seus laudos e documentos de forma segura.")
    st.write("---")

    email = st.text_input("E-mail corporativo", placeholder="seu@email.com.br")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar", type="primary", use_container_width=True):
        if not email or not senha:
            st.warning("Preencha o e-mail e a senha.")
        else:
            with st.spinner("Autenticando..."):
                if fazer_login(email, senha):
                    st.rerun()
                else:
                    st.error("E-mail ou senha incorretos.")

# ==========================================
# ÁREA AUTENTICADA
# ==========================================
else:
    token = st.session_state["token"]
    dados_usuario = extrair_dados_do_token(token)

    # Verifica se o token expirou
    if verificar_token_expirado(dados_usuario):
        st.warning("Sua sessão expirou. Faça login novamente.")
        st.session_state["token"] = None
        st.rerun()

    # Verifica se o usuário precisa trocar a senha
    if dados_usuario.get("exigir_troca_senha"):
        st.warning("⚠️ Você precisa alterar sua senha antes de continuar.")
        nova_senha = st.text_input("Nova senha", type="password", key="nova_senha")
        confirmar = st.text_input("Confirmar nova senha", type="password", key="confirmar_senha")
        if st.button("Salvar nova senha", type="primary"):
            if nova_senha != confirmar:
                st.error("As senhas não coincidem.")
            elif len(nova_senha) < 6:
                st.error("A senha deve ter ao menos 6 caracteres.")
            else:
                # Placeholder: implementar endpoint de troca de senha
                st.success("Senha alterada com sucesso! Faça login novamente.")
                st.session_state["token"] = None
                st.rerun()
        st.stop()

    cliente_id = dados_usuario.get("cliente_id")
    email_logado = dados_usuario.get("sub")

    # Heartbeat — mantém sessão ativa a cada 60 segundos
    st_autorefresh(interval=60000, key="heartbeat")
    enviar_ping(token)

    # Cabeçalho
    col1, col2 = st.columns([4, 1])
    with col1:
        st.title("🌿 Meus Documentos")
        st.caption(f"Logado como: **{email_logado}**")
    with col2:
        if st.button("Sair", use_container_width=True):
            st.session_state["token"] = None
            st.rerun()

    st.write("---")

    # Busca lista de documentos (apenas metadados, sem baixar arquivos)
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resp = requests.get(
            f"{API_URL}/clientes/{cliente_id}/documentos/",
            headers=headers,
            timeout=10
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Erro ao buscar documentos: {e}")
        st.stop()

    if resp.status_code == 200:
        documentos = resp.json()

        if not documentos:
            st.info("Nenhum laudo encontrado para sua conta.")
        else:
            st.markdown(f"**{len(documentos)} documento(s) disponível(is):**")

            for doc in documentos:
                data_simples = doc["data_upload"][:10]  # AAAA-MM-DD

                with st.expander(f"📄 {doc['tipo_documento']} — {data_simples}"):
                    nome_arquivo = doc["url_arquivo"].split("/")[-1]
                    url_completa = f"{API_URL}/{doc['url_arquivo']}".replace(" ", "%20")

                    # Chave de estado para controlar se o usuário solicitou o download
                    chave_download = f"solicitar_download_{doc['id']}"
                    chave_conteudo = f"conteudo_arquivo_{doc['id']}"

                    # Botão que registra a auditoria e prepara o arquivo
                    if st.button(
                        "📥 Preparar download",
                        key=f"preparar_{doc['id']}",
                        help="Clique para baixar o laudo oficial"
                    ):
                        with st.spinner("Buscando arquivo..."):
                            conteudo = buscar_arquivo(url_completa, token)

                        if conteudo:
                            # Armazena o conteúdo na sessão para o download_button
                            st.session_state[chave_conteudo] = conteudo
                            # Registra a auditoria apenas aqui, após clique explícito
                            registrar_auditoria(token, doc)
                            st.session_state[chave_download] = True
                        else:
                            st.error("Arquivo não encontrado no servidor.")

                    # Exibe o botão de download real apenas quando o arquivo está pronto
                    if st.session_state.get(chave_download) and st.session_state.get(chave_conteudo):
                        st.download_button(
                            label="⬇️ Baixar Laudo Oficial",
                            data=st.session_state[chave_conteudo],
                            file_name=nome_arquivo,
                            mime="application/pdf",
                            key=f"download_{doc['id']}",
                        )

    elif resp.status_code == 401:
        st.warning("Sessão expirada. Faça login novamente.")
        st.session_state["token"] = None
        st.rerun()
    else:
        st.error(f"Erro ao buscar documentos (status {resp.status_code}).")