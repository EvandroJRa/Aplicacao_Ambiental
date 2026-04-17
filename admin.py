import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

API_URL = "https://aplicacao-ambiental.onrender.com"

st.set_page_config(page_title="Painel Admin - Ambiental", page_icon="⚙️", layout="wide")

# ==========================================
# FUNÇÕES DE APOIO
# ==========================================
def calcular_status_visual(ultima_atividade):
    if not ultima_atividade:
        return "🔴 Offline"
    
    try:
        if isinstance(ultima_atividade, str):
            ultima_atv = pd.to_datetime(ultima_atividade)
        else:
            ultima_atv = ultima_atividade

        if ultima_atv.tzinfo is None:
            ultima_atv = ultima_atv.replace(tzinfo=timezone.utc)
            
        agora = datetime.now(timezone.utc)
        minutos = (agora - ultima_atv).total_seconds() / 60
        
        if minutos < 2: return "🟢 Online"
        elif minutos < 7: return "🟠 Ausente"
        else: return "🔴 Offline"
    except:
        return "⚪ Desconhecido"

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
# INTERFACE
# ==========================================
if st.session_state["admin_token"] is None:
    st.title("⚙️ Painel de Administração")
    with st.form("form_login"):
        email = st.text_input("E-mail corporativo")
        senha = st.text_input("Senha", type="password")
        if st.form_submit_button("Entrar", type="primary"):
            if fazer_login(email, senha): st.rerun()
            else: st.error("Credenciais inválidas.")
else:
    headers = {"Authorization": f"Bearer {st.session_state['admin_token']}"}
    
    st.sidebar.title("Menu Administrativo")
    # Adicionamos "Auditoria" explicitamente no menu lateral
    menu = st.sidebar.radio("Escolha uma ação:", ["Dashboard", "Auditoria", "Novo Cliente", "Enviar Laudo/Documento"])
    
    if st.sidebar.button("Sair (Logout)"):
        st.session_state["admin_token"] = None
        st.rerun()

    # -----------------------------------------
    # TELA 0: DASHBOARD (Visão Geral + Status Online)
    # -----------------------------------------
    if menu == "Dashboard":
        st.header("📊 Visão Geral do Sistema")
        
        res_clientes = requests.get(f"{API_URL}/clientes/", headers=headers)
        res_usuarios = requests.get(f"{API_URL}/usuarios/", headers=headers)
        
        if res_clientes.status_code == 200 and res_usuarios.status_code == 200:
            clientes = res_clientes.json()
            usuarios = res_usuarios.json()
            
            col1, col2, col3 = st.columns(3)
            col1.metric("Empresas", len(clientes))
            col2.metric("Acessos", len(usuarios))
            col3.metric("Servidor", "Online 🟢")
            
            st.divider()
            st.subheader("📋 Status dos Usuários em Tempo Real")
            
            if usuarios:
                df_usuarios = pd.DataFrame(usuarios)
                
                # APLICAÇÃO DA BOLINHA DE STATUS
                df_usuarios['Status'] = df_usuarios['ultima_atividade'].apply(calcular_status_visual)
                
                # Organizando colunas para visualização
                # Note que incluímos 'ultima_atividade' para conferência
                exibir = df_usuarios[['Status', 'email', 'cliente_id', 'ultima_atividade']]
                exibir.columns = ['Status', 'E-mail', 'ID Empresa', 'Última Atividade']
                
                st.dataframe(exibir, use_container_width=True, hide_index=True)
            else:
                st.info("Nenhum usuário cadastrado.")

    # -----------------------------------------
    # TELA 1: AUDITORIA (LOGS)
    # -----------------------------------------
    elif menu == "Auditoria":
        st.header("🕵️ Registro de Auditoria (Logs)")
        resp_logs = requests.get(f"{API_URL}/auditoria/", headers=headers)
        
        if resp_logs.status_code == 200:
            logs = resp_logs.json()
            if logs:
                df_logs = pd.DataFrame(logs)
                st.dataframe(df_logs[['data_hora', 'email_usuario', 'nome_empresa', 'evento', 'detalhes', 'ip']], use_container_width=True)
                
                st.subheader("📍 Mapa de Acessos")
                df_mapa = df_logs.dropna(subset=['latitude', 'longitude']).rename(columns={'latitude':'lat', 'longitude':'lon'})
                if not df_mapa.empty:
                    st.map(df_mapa)
            else:
                st.info("Sem registros.")

    # -----------------------------------------
    # TELA 2: NOVO CLIENTE
    # -----------------------------------------
    elif menu == "Novo Cliente":
        st.header("🏢 Cadastrar Nova Empresa")
        with st.form("form_novo_cliente", clear_on_submit=True):
            nome = st.text_input("Nome da Empresa")
            cnpj = st.text_input("CNPJ")
            whatsapp = st.text_input("WhatsApp")
            email_c = st.text_input("E-mail")
            if st.form_submit_button("Salvar"):
                payload = {"nome": nome, "cnpj": cnpj, "whatsapp_contato": whatsapp, "email": email_c}
                resp = requests.post(f"{API_URL}/clientes/", json=payload, headers=headers)
                if resp.status_code == 200: st.success("Sucesso!")

    # -----------------------------------------
    # TELA 3: ENVIAR LAUDO
    # -----------------------------------------
    elif menu == "Enviar Laudo/Documento":
        st.header("📤 Upload de Documentos")
        resp_c = requests.get(f"{API_URL}/clientes/", headers=headers)
        if resp_c.status_code == 200:
            cliente_sel = st.selectbox("Selecione o Cliente:", resp_c.json(), format_func=lambda c: f"{c['id']} - {c['nome']}")
            with st.form("form_upload"):
                tipo = st.selectbox("Tipo", ["Laudo de Análise", "Relatório", "Outros"])
                arquivo = st.file_uploader("Arquivo", type=['pdf', 'jpg', 'png', 'xlsx'])
                if st.form_submit_button("Enviar") and arquivo:
                    files = {"arquivo": (arquivo.name, arquivo.getvalue(), arquivo.type)}
                    requests.post(f"{API_URL}/clientes/{cliente_sel['id']}/documentos/", headers=headers, data={"tipo_documento": tipo}, files=files)
                    st.success("Enviado!")