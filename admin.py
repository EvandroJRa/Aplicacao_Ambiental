import streamlit as st
import requests
import pandas as pd

API_URL = "https://aplicacao-ambiental.onrender.com"

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
    
    with st.form("form_login"):
        email = st.text_input("E-mail corporativo")
        senha = st.text_input("Senha", type="password")
        submit_login = st.form_submit_button("Entrar", type="primary")
        
        if submit_login:
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
    # 👇 AQUI ADICIONAMOS O DASHBOARD NO MENU
    menu = st.sidebar.radio("Escolha uma ação:", ["Dashboard", "Novo Cliente", "Enviar Laudo/Documento"])
    
    st.sidebar.write("---")
    if st.sidebar.button("Sair (Logout)"):
        st.session_state["admin_token"] = None
        st.rerun()

    # -----------------------------------------
    # TELA 0: DASHBOARD (Visão Geral)
    # -----------------------------------------
    if menu == "Dashboard":
        st.header("📊 Visão Geral do Sistema")
        
        # Busca os dados na API passando o crachá de segurança
        res_clientes = requests.get(f"{API_URL}/clientes/", headers=headers)
        res_usuarios = requests.get(f"{API_URL}/usuarios/", headers=headers)
        
        if res_clientes.status_code == 200 and res_usuarios.status_code == 200:
            clientes = res_clientes.json()
            usuarios = res_usuarios.json()
            
            # 1. Cartões de Métricas (KPIs)
            col1, col2, col3 = st.columns(3)
            col1.metric("Empresas Cadastradas", len(clientes))
            col2.metric("Acessos Liberados", len(usuarios))
            col3.metric("Status do Servidor", "Online 🟢")
            
            st.divider()
            
            # 2. Tabela Visual de Acessos
            st.subheader("📋 Controle de Acessos")
            
            if len(usuarios) > 0:
                df_usuarios = pd.DataFrame(usuarios)
                # Reorganizando e renomeando as colunas para ficar elegante
                df_usuarios = df_usuarios[['id', 'cliente_id', 'email']]
                df_usuarios.columns = ['ID do Acesso', 'ID da Empresa', 'E-mail de Login']
                
                st.dataframe(df_usuarios, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum usuário cadastrado ainda.")
        else:
            st.error("Erro ao carregar os dados. Verifique a conexão com a API.")

    # -----------------------------------------
    # TELA 1: CADASTRAR NOVO CLIENTE
    # -----------------------------------------
    elif menu == "Novo Cliente":
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
            
            # Formata a lista para o SelectBox
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

# -----------------------------------------
    # TELA 3: AUDITORIA (LOGS DE ACESSO)
    # -----------------------------------------
    elif menu == "Auditoria":
        st.header("🕵️ Registro de Auditoria (Logs)")
        
        resp_logs = requests.get(f"{API_URL}/auditoria/", headers=headers)
        
        if resp_logs.status_code == 200:
            logs = resp_logs.json()
            if logs:
                df_logs = pd.DataFrame(logs)
                
                # Organiza as colunas para leitura humana
                colunas_vistas = [
                    'data_hora', 'email_usuario', 'nome_empresa', 
                    'evento', 'detalhes', 'ip', 'latitude', 'longitude'
                ]
                st.dataframe(df_logs[colunas_vistas], use_container_width=True)
                
                # Mapa Visual (Se houver coordenadas)
                st.subheader("📍 Mapa de Acessos")
                df_mapa = df_logs.dropna(subset=['latitude', 'longitude'])
                if not df_mapa.empty:
                    st.map(df_mapa)
            else:
                st.info("Nenhum log de auditoria registrado.")                    