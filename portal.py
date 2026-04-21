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
js_ip = 'await fetch("https://api64.ipify.org?format=json").then(r => r.json()).then(d => d.ip)'
ip_usuario = st_javascript(js_ip)

if ip_usuario == 0:
    with st.spinner("Carregando..."):
        time.sleep(1.5)
        st.rerun()

# ==========================================
# CAPTURA DE USER AGENT VIA JAVASCRIPT
# ==========================================
js_ua = 'navigator.userAgent'
user_agent = st_javascript(js_ua)

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
if "login_auditado" not in st.session_state:
    st.session_state["login_auditado"] = False

# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================
def fazer_login(email: str, senha: str) -> bool:
    try:
        resposta = requests.post(
            f"{API_URL}/token",
            data={"username": email, "password": senha},
            timeout=10
        )
        if resposta.status_code == 200:
            st.session_state["token"] = resposta.json().get("access_token")
            st.session_state["login_auditado"] = False
            return True
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Erro de conexão: {e}")
        return False


def extrair_dados_do_token(token: str) -> dict:
    try:
        payload = token.split(".")[1]
        payload += "=" * ((4 - len(payload) % 4) % 4)
        return json.loads(base64.b64decode(payload).decode("utf-8"))
    except Exception:
        return {}


def verificar_token_expirado(dados_token: dict) -> bool:
    exp = dados_token.get("exp")
    return bool(exp and time.time() > exp)


def registrar_auditoria(token: str, evento: str, detalhes: str):
    """Registra qualquer evento de auditoria na API."""
    dados = {
        "evento": evento,
        "detalhes": detalhes,
        "ip": str(ip_usuario) if ip_usuario and ip_usuario != 0 else None,
        "latitude": latitude,
        "longitude": longitude,
        "user_agent": str(user_agent) if user_agent and user_agent != 0 else None,
    }
    headers = {"Authorization": f"Bearer {token}"}
    try:
        resposta = requests.post(
            f"{API_URL}/auditoria/",
            json=dados,
            headers=headers,
            timeout=10
        )
        if resposta.status_code not in (200, 201):
            st.warning(f"Auditoria retornou status inesperado: {resposta.status_code}")
    except requests.exceptions.RequestException as e:
        st.warning(f"Falha ao registrar auditoria: {e}")


def buscar_arquivo(url: str, token: str) -> bytes | None:
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
    headers = {"Authorization": f"Bearer {token}"}
    try:
        requests.post(f"{API_URL}/usuarios/ping", headers=headers, timeout=5)
    except requests.exceptions.RequestException:
        pass


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

    if verificar_token_expirado(dados_usuario):
        st.warning("Sua sessão expirou. Faça login novamente.")
        st.session_state["token"] = None
        st.rerun()

    cliente_id = dados_usuario.get("cliente_id")
    email_logado = dados_usuario.get("sub")

    # Registra LOGIN_PORTAL uma única vez por sessão
    # Garante que GPS e user agent já foram capturados pelo JS antes de registrar
    if not st.session_state.get("login_auditado") and ip_usuario and ip_usuario != 0:
        registrar_auditoria(
            token=token,
            evento="LOGIN_PORTAL",
            detalhes="Sessão iniciada no Portal Ambiental."
        )
        st.session_state["login_auditado"] = True

    # Heartbeat a cada 60 segundos
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
            st.session_state["login_auditado"] = False
            st.rerun()

    st.write("---")

    # Busca metadados dos documentos
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
                data_simples = doc["data_upload"][:10]

                with st.expander(f"📄 {doc['tipo_documento']} — {data_simples}"):

                    # Exibe hash SHA-256 para o cliente verificar integridade
                    if doc.get("hash_arquivo"):
                        st.caption(f"🔒 SHA-256: `{doc['hash_arquivo']}`")

                    nome_arquivo = doc["url_arquivo"].split("/")[-1]
                    url_completa = f"{API_URL}/{doc['url_arquivo']}".replace(" ", "%20")

                    # Chaves de estado por documento
                    chave_preparar = f"preparar_{doc['id']}"
                    chave_timer    = f"timer_{doc['id']}"
                    chave_conteudo = f"conteudo_{doc['id']}"
                    chave_pronto   = f"pronto_{doc['id']}"
                    chave_baixado  = f"baixado_{doc['id']}"

                    # ── ETAPA 1: Botão inicial ──────────────────────────────
                    if not st.session_state.get(chave_preparar):
                        if st.button("📥 Preparar download", key=f"btn_prep_{doc['id']}"):
                            with st.spinner("Buscando arquivo..."):
                                conteudo = buscar_arquivo(url_completa, token)

                            if conteudo:
                                st.session_state[chave_conteudo] = conteudo
                                st.session_state[chave_preparar] = True
                                st.session_state[chave_timer] = time.time()
                                registrar_auditoria(
                                    token=token,
                                    evento="DOWNLOAD_INICIADO",
                                    detalhes=f"Iniciou download: {doc['tipo_documento']} (ID: {doc['id']})"
                                )
                                st.rerun()
                            else:
                                st.error("Arquivo não encontrado no servidor.")

                    # ── ETAPA 2: Modal de confirmação com temporizador ──────
                    elif not st.session_state.get(chave_pronto):
                        tempo_decorrido = time.time() - st.session_state.get(chave_timer, time.time())
                        tempo_restante = max(0, 15 - int(tempo_decorrido))

                        st.info(
                            "📋 **Confirmação de Ciência**\n\n"
                            f"Ao confirmar, você declara que:\n"
                            f"- Teve acesso ao documento **{doc['tipo_documento']}**\n"
                            f"- Está ciente do seu conteúdo e das obrigações técnicas\n\n"
                            f"Este registro será gravado com data, hora, IP e localização."
                        )

                        if tempo_restante > 0:
                            st.warning(f"⏳ Aguarde **{tempo_restante}s** para confirmar...")
                            time.sleep(1)
                            st.rerun()
                        else:
                            col_ok, col_cancel = st.columns(2)

                            with col_ok:
                                if st.button(
                                    "✅ Confirmar e baixar",
                                    key=f"btn_ok_{doc['id']}",
                                    type="primary",
                                    use_container_width=True
                                ):
                                    registrar_auditoria(
                                        token=token,
                                        evento="CONFIRMACAO_CIENCIA",
                                        detalhes=f"Confirmou ciência: {doc['tipo_documento']} (ID: {doc['id']})"
                                    )
                                    st.session_state[chave_pronto] = True
                                    st.rerun()

                            with col_cancel:
                                if st.button(
                                    "✗ Cancelar",
                                    key=f"btn_cancel_{doc['id']}",
                                    use_container_width=True
                                ):
                                    for chave in [chave_preparar, chave_timer, chave_conteudo, chave_pronto]:
                                        st.session_state.pop(chave, None)
                                    st.rerun()

                    # ── ETAPA 3: Download liberado ──────────────────────────
                    else:
                        st.success("✅ Ciência confirmada. Clique para baixar.")

                        st.download_button(
                            label="⬇️ Baixar Laudo Oficial",
                            data=st.session_state[chave_conteudo],
                            file_name=nome_arquivo,
                            mime="application/pdf",
                            key=f"btn_dl_{doc['id']}",
                        )

                        # Registra a entrega do arquivo uma única vez
                        if not st.session_state.get(chave_baixado):
                            registrar_auditoria(
                                token=token,
                                evento="DOWNLOAD_DOCUMENTO",
                                detalhes=f"Baixou: {doc['tipo_documento']} (ID: {doc['id']})"
                            )
                            st.session_state[chave_baixado] = True

    elif resp.status_code == 401:
        st.warning("Sessão expirada. Faça login novamente.")
        st.session_state["token"] = None
        st.rerun()
    else:
        st.error(f"Erro ao buscar documentos (status {resp.status_code}).")
