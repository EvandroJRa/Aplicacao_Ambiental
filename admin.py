import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Painel Admin - Ambiental", page_icon="⚙️", layout="wide")

# ==========================================
# GERENCIAMENTO DE SESSÃO
# ==========================================
if "admin_token" not in st.session_state:
    st.session_state["admin_token"] = None

def fazer_login(email, senha):
    resposta = requests.post(f"{API_URL}/token", data={"username": email, "password": senha})
    if resposta.status_code == 200:
        st.session_state["admin_token"] = resposta.json().get("access_token")
        return True
    return False

# ==========================================
# TELA DE LOGIN
# ==========================================
if st.session_state["admin_token"] is None:
    st.title("⚙️ Painel de Administração")
    st.subheader("Acesso restrito à equipe interna")
    
    email = st.text_input("E-mail corporativo")
    senha = st.text_input("Senha", type="password")
    
    if st.button("Entrar", type="primary"):
        if fazer_login(email, senha):
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

# ==========================================
# TELA DO SISTEMA (LOGADO)
# ==========================================
else:
    headers = {"Authorization": f"Bearer {st.session_state['admin_token']}"}
    
    # Menu Lateral
    st.sidebar.title("Menu Administrativo")
    menu = st.sidebar.radio("Escolha uma ação:", ["Novo Cliente", "Enviar Laudo/Documento"])
    
    st.sidebar.write("---")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state["admin_token"] = None
        st.rerun()

    # -----------------------------------------
    # TELA 1: CADASTRAR NOVO CLIENTE
    # -----------------------------------------
    if menu == "Novo Cliente":
        st.header("🏢 Cadastrar Nova Empresa")
        
        with st.form("form_novo_cliente", clear_on_submit=True):
            nome = st.text_input("Nome da Empresa (Razão Social)")
            cnpj = st.text_input("CNPJ (Apenas números ou formatado)")
            whatsapp = st.text_input("WhatsApp do Responsável (Ex: 5511999999999)")
            email_cliente = st.text_input("E-mail de Contato")
            
            submit = st.form_submit_button("Salvar Cliente", type="primary")
            
            if submit:
                dados_cliente = {
                    "nome": nome,
                    "cnpj": cnpj,
                    "whatsapp_contato": whatsapp,
                    "email": email_cliente
                }
                resp = requests.post(f"{API_URL}/clientes/", json=dados_cliente, headers=headers)
                
                if resp.status_code == 200:
                    st.success(f"Cliente '{nome}' cadastrado com sucesso!")
                else:
                    st.error(f"Erro ao cadastrar: {resp.text}")

    # -----------------------------------------
    # TELA 2: ENVIAR LAUDO E NOTIFICAR
    # -----------------------------------------
    elif menu == "Enviar Laudo/Documento":
        st.header("📤 Upload de Documentos")
        
        # 1. Puxa a lista de clientes para o seu time escolher
        resp_clientes = requests.get(f"{API_URL}/clientes/", headers=headers)
        
        if resp_clientes.status_code == 200:
            lista_clientes = resp_clientes.json()
            
            # Formata a lista para o SelectBox (mostra o nome, mas guarda o dicionário inteiro)
            cliente_selecionado = st.selectbox(
                "Selecione o Cliente:", 
                options=lista_clientes, 
                format_func=lambda c: f"{c['id']} - {c['nome']}"
            )
            
            with st.form("form_upload", clear_on_submit=True):
                tipo_doc = st.selectbox("Tipo de Documento", ["Laudo de Análise", "Relatório Técnico", "Certificado de Destinação", "Outros"])
                arquivo = st.file_uploader("Selecione o arquivo (PDF, JPG, Excel)", type=['pdf', 'jpg', 'png', 'xlsx'])
                
                submit_upload = st.form_submit_button("Enviar e Notificar Cliente", type="primary")
                
                if submit_upload and arquivo and cliente_selecionado:
                    # Prepara o arquivo para viajar pela internet até o FastAPI
                    files = {"arquivo": (arquivo.name, arquivo.getvalue(), arquivo.type)}
                    data = {"tipo_documento": tipo_doc}
                    
                    url_upload = f"{API_URL}/clientes/{cliente_selecionado['id']}/documentos/"
                    
                    with st.spinner("Enviando arquivo e disparando WhatsApp..."):
                        resp_upload = requests.post(url_upload, headers=headers, data=data, files=files)
                        
                    if resp_upload.status_code == 200:
                        st.success("✅ Arquivo enviado e notificação programada!")
                    else:
                        st.error(f"Erro no envio: {resp_upload.text}")
                elif submit_upload and not arquivo:
                    st.warning("Por favor, anexe um arquivo antes de enviar.")