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
        else:
            st.error("Falha ao obter dados dos clientes ou usuários.")

            st.subheader("👥 Status dos Usuários")

            # 1. GARANTIA: Inicializa a variável como lista vazia
            usuarios = [] 

            try:
                # 2. Busca os dados na API
                resp = requests.get(f"{API_URL}/usuarios/", headers=headers)
                if resp.status_code == 200:
                    usuarios = resp.json()
                else:
                    st.error(f"Erro ao buscar usuários: {resp.status_code}")
            except Exception as e:
                st.error(f"Falha na conexão com a API: {e}")

            # 3. O SEU BLOCO (Agora com a variável garantida)
            if usuarios:
                df_usuarios = pd.DataFrame(usuarios)
                
                # 🛑 PROTEÇÃO: Só tenta calcular o status se a coluna existir no DataFrame
                if not df_usuarios.empty and 'ultima_atividade' in df_usuarios.columns:
                    df_usuarios['Status'] = df_usuarios['ultima_atividade'].apply(calcular_status_visual)
                    
                    # Organizando colunas para visualização
                    # Usamos .get() ou checamos as colunas para evitar novos erros de nome
                    colunas_disponiveis = df_usuarios.columns.tolist()
                    colunas_para_exibir = [c for c in ['Status', 'email', 'cliente_id', 'ultima_atividade'] if c in colunas_disponiveis]
                    
                    exibir = df_usuarios[colunas_para_exibir]
                    st.dataframe(exibir, use_container_width=True, hide_index=True)
                else:
                    st.info("Aguardando dados de atividade dos usuários...")
            else:
                st.info("Nenhum usuário cadastrado no sistema.")

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
    # TELA 2: NOVO CLIENTE (COM CRIAÇÃO DE ACESSO)
    # -----------------------------------------
    elif menu == "Novo Cliente":
        st.header("🏢 Cadastrar Nova Empresa e Primeiro Acesso")
        st.info("Ao salvar, o sistema criará a empresa e o usuário vinculado automaticamente.")
        
        with st.form("form_novo_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Dados da Empresa")
                nome = st.text_input("Razão Social / Nome Fantasia")
                cnpj = st.text_input("CNPJ (Apenas números)")
                whatsapp = st.text_input("WhatsApp do Responsável", help="Ex: 5511999999999")
            
            with col2:
                st.subheader("Credenciais de Acesso")
                email_c = st.text_input("E-mail de Login", help="Este será o usuário do portal")
                senha_prov = st.text_input("Senha Provisória", value="Alterar@123", type="password")
                st.caption("⚠️ O cliente será obrigado a trocar esta senha no primeiro login.")
            
            st.write("---")
            submit = st.form_submit_button("Finalizar Cadastro e Gerar Acesso", type="primary")
            
            if submit:
                # O payload agora leva a senha provisória para a API orquestrar tudo
                payload = {
                    "nome": nome,
                    "cnpj": cnpj,
                    "whatsapp_contato": whatsapp,
                    "email": email_c,
                    "senha_provisoria": senha_prov  # Campo novo para a API
                }
                
                with st.spinner("Sincronizando com o banco de dados..."):
                    resp = requests.post(f"{API_URL}/clientes/", json=payload, headers=headers)
                
                if resp.status_code == 200:
                    st.success(f"✅ Cliente '{nome}' e usuário '{email_c}' cadastrados com sucesso!")
                    st.balloons()
                else:
                    # Tenta mostrar o erro detalhado da API se houver (ex: CNPJ duplicado)
                    try:
                        erro_detalhe = resp.json().get('detail', resp.text)
                    except:
                        erro_detalhe = resp.text
                    st.error(f"Erro ao processar cadastro: {erro_detalhe}")

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