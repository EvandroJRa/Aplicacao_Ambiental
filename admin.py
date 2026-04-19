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
    if not ultima_atividade: return "🔴 Offline"
    try:
        ultima_atv = pd.to_datetime(ultima_atividade)
        if ultima_atv.tzinfo is None: ultima_atv = ultima_atv.replace(tzinfo=timezone.utc)
        agora = datetime.now(timezone.utc)
        minutos = (agora - ultima_atv).total_seconds() / 60
        if minutos < 2: return "🟢 Online"
        elif minutos < 7: return "🟠 Ausente"
        else: return "🔴 Offline"
    except: return "⚪ Desconhecido"

# ==========================================
# GERENCIAMENTO DE SESSÃO
# ==========================================
if "admin_token" not in st.session_state:
    st.session_state["admin_token"] = None

def fazer_login(email, senha):
    resposta = requests.post(f"{API_URL}/token", data={"username": email, "password": senha})
    
    if resposta.status_code == 200:
        dados = resposta.json()
        
        # 🟢 A CATRACA DE SEGURANÇA: Só entra se tiver o crachá de admin!
        if dados.get("is_admin") == True:
            st.session_state["admin_token"] = dados.get("access_token")
            return True
        else:
            # Cliente tentou logar no painel administrativo
            st.error("❌ Acesso Negado: Área restrita para a equipe da Consensu.")
            return False
            
    # Se a senha estiver errada ou e-mail não existir
    st.error("E-mail ou senha incorretos.")
    return False

def exibir_auditoria(token):
    headers = {"Authorization": f"Bearer {token}"}
    resposta = requests.get(f"{API_URL}/auditoria/", headers=headers)
    
    if resposta.status_code == 200:
        dados = resposta.json()
        df = pd.DataFrame(dados)

        if not df.empty:
            # 1. Ajuste das Datas (DD-MM-YYYY)
            # Convertemos para datetime e depois para string formatada
            df['data_hora'] = pd.to_datetime(df['data_hora']).dt.strftime('%d-%m-%Y %H:%M:%S')

            # 2. Interface de Filtros
            st.subheader("🔍 Filtros de Pesquisa")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                busca_email = st.text_input("E-mail do Usuário")
            with col2:
                # Pegamos os eventos únicos para preencher o selectbox
                eventos_disponiveis = ["Todos"] + sorted(df['evento'].unique().tolist())
                filtro_evento = st.selectbox("Tipo de Evento", eventos_disponiveis)
            with col3:
                busca_empresa = st.text_input("Nome da Empresa")

            # 3. Lógica de Filtragem (Aplicada ao DataFrame)
            if busca_email:
                df = df[df['email_usuario'].str.contains(busca_email, case=False, na=False)]
            
            if filtro_evento != "Todos":
                df = df[df['evento'] == filtro_evento]
                
            if busca_empresa:
                df = df[df['nome_empresa'].str.contains(busca_empresa, case=False, na=False)]

            # 4. Exibição da Tabela
            st.write(f"Exibindo {len(df)} registros encontrados:")
            st.dataframe(
                df, 
                use_container_width=True,
                column_order=[
                    "data_hora", "email_usuario", "nome_empresa", 
                    "evento", "detalhes", "ip"
                ] # Define uma ordem mais limpa para o Admin
            )
        else:
            st.info("Nenhum registro de auditoria encontrado.")
    else:
        st.error("Erro ao carregar dados de auditoria.")

# ==========================================
# INTERFACE PRINCIPAL
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
    menu = st.sidebar.radio(
        "Escolha uma ação:", 
        ["Dashboard", 
         "Listar Clientes", 
         "Auditoria", 
         "Novo Cliente", 
         "Enviar Laudo/Documento", 
         "Debug Banco", 
         "Inspeção de Dados"]
    )

    if st.sidebar.button("Sair (Logout)"):
        st.session_state["admin_token"] = None
        st.rerun()

    # -----------------------------------------
    # TELA 0: DASHBOARD
    # -----------------------------------------
    if menu == "Dashboard":
        st.header("📊 Visão Geral do Sistema")
        res_c = requests.get(f"{API_URL}/clientes/", headers=headers)
        res_u = requests.get(f"{API_URL}/usuarios/", headers=headers)
        
        if res_c.status_code == 200 and res_u.status_code == 200:
            col1, col2, col3 = st.columns(3)
            col1.metric("Empresas", len(res_c.json()))
            usuarios = res_u.json()
            col2.metric("Acessos", len(usuarios))
            col3.metric("Servidor", "Online 🟢")
            
            st.divider()
            st.subheader("👥 Status em Tempo Real")
            if usuarios:
                df_u = pd.DataFrame(usuarios)
                if 'ultima_atividade' in df_u.columns:
                    df_u['Status'] = df_u['ultima_atividade'].apply(calcular_status_visual)
                    st.dataframe(df_u[['Status', 'email', 'cliente_id']], use_container_width=True, hide_index=True)
        else:
            st.error("Erro ao carregar indicadores.")

    # -----------------------------------------
    # TELA 1: LISTAR CLIENTES (COM BUSCA POR ID)
    # -----------------------------------------
    elif menu == "Listar Clientes":
            st.header("📋 Empresas Cadastradas")
            resp = requests.get(f"{API_URL}/clientes/", headers=headers)
            
            if resp.status_code == 200:
                clientes = resp.json()
                #st.write(clientes[0]) # <--- DESCOMENTE ESTA LINHA PARA TESTAR
                filtro = st.text_input("🔍 Pesquisar por ID de Faturamento ou Nome")
                
                if filtro:
                    clientes = [
                        c for c in clientes 
                        if filtro.lower() in str(c.get('codigo_identificador', c.get('codigo_cliente', ''))).lower() 
                        or filtro.lower() in c.get('nome', '').lower()
                    ]
                
                if clientes:
                    # Normalização: Garantimos que o campo apareça como 'ID Faturamento'
                    for c in clientes:
                        c['id_faturamento_view'] = c.get('codigo_identificador') or c.get('codigo_cliente') or "N/D"

                    df_c = pd.DataFrame(clientes)
                    
                    # Mapeamento de exibição
                    mapeamento = {
                        'id': 'ID Banco',
                        'id_faturamento_view': 'ID Faturamento', 
                        'nome': 'Razão Social',
                        'cnpj': 'CNPJ',
                        'email': 'E-mail'
                    }
                    
                    # Seleciona apenas as colunas que definimos acima e que existem no DataFrame
                    cols_para_exibir = [c for c in mapeamento.keys() if c in df_c.columns]
                    
                    df_view = df_c[cols_para_exibir].rename(columns=mapeamento)
                    st.dataframe(df_view, use_container_width=True, hide_index=True)
                else: 
                    st.info("Nenhum cliente encontrado.")
    # -----------------------------------------
    # TELA 2: AUDITORIA
    # -----------------------------------------
    elif menu == "Auditoria":
        st.header("🕵️ Registro de Auditoria")
        # 🟢 A MÁGICA AQUI: Chama a função que tem os filtros e formatação!
        exibir_auditoria(st.session_state['admin_token'])

    # -----------------------------------------
    # TELA 3: NOVO CLIENTE
    # -----------------------------------------
    elif menu == "Novo Cliente":
        st.header("🏢 Novo Cadastro")
        with st.form("form_novo_cliente", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome = st.text_input("Razão Social")
                cnpj = st.text_input("CNPJ")
                id_fat = st.text_input("ID Faturamento (Código Interno)")
            with col2:
                email_c = st.text_input("E-mail de Login")
                whatsapp = st.text_input("WhatsApp")
                senha_prov = st.text_input("Senha Provisória", value="Alterar@123", type="password")
            
            if st.form_submit_button("Salvar Cliente", type="primary"):
                payload = {"nome": nome, "cnpj": cnpj, "whatsapp_contato": whatsapp, "email": email_c, "senha_provisoria": senha_prov, "codigo_cliente": id_fat}
                res = requests.post(f"{API_URL}/clientes/", json=payload, headers=headers)
                if res.status_code == 200:
                    st.success("✅ Cadastrado com sucesso!"); st.balloons()
                else: st.error(f"Erro: {res.text}")

    # -----------------------------------------
    # TELA 4: ENVIAR LAUDO
    # -----------------------------------------
    elif menu == "Enviar Laudo/Documento":
        st.header("📤 Envio de Documentos")
        resp_c = requests.get(f"{API_URL}/clientes/", headers=headers)
        if resp_c.status_code == 200:
            clientes = resp_c.json()
            if not clientes: st.warning("Cadastre uma empresa primeiro.")
            else:
                arquivo = st.file_uploader("1️⃣ Selecione o arquivo", type=['pdf', 'xlsx', 'docx'])
                opcoes = {f"{c.get('codigo_identificador') or c['id']} - {c['nome']}": c['id'] for c in clientes}
                
                with st.form("form_upload"):
                    label_selecionado = st.selectbox("2️⃣ Destinatário", options=list(opcoes.keys()))
                    c_id = opcoes[label_selecionado]
                    tipo = st.selectbox("Categoria", ["Laudo de Solo", "Laudo de Água", "Relatório de Monitoramento", "Oficios", "Licenças Ambientais", "Certificados", "Declarações", "Outros"])
                    comp = st.date_input("Referência")
                    obs = st.text_area("Observações")
                    
                    if st.form_submit_button("🚀 Enviar"):
                        if arquivo:
                            files = {"arquivo": (arquivo.name, arquivo.getvalue(), arquivo.type)}
                            data = {"tipo_documento": tipo, "competencia": comp.strftime("%Y-%m-%d"), "detalhes": obs}
                            res = requests.post(f"{API_URL}/clientes/{c_id}/documentos/", data=data, files=files, headers=headers)
                            if res.status_code == 200: st.success("Enviado!"); st.balloons()
                            else: st.error(f"Erro: {res.text}")
                        else: st.error("Selecione um arquivo!")

    # -----------------------------------------
    # TELA 5: DEBUG TABELAS
    # -----------------------------------------
    elif menu == "Debug Banco":
            st.header("🗄️ Inspeção Direta do Banco de Dados")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Tabela: Usuários")
                res_u = requests.get(f"{API_URL}/usuarios/", headers=headers)
                if res_u.status_code == 200:
                    st.write(res_u.json()) # Mostra o JSON bruto para conferir os nomes dos campos
                    st.dataframe(pd.DataFrame(res_u.json()))
            
            with col2:
                st.subheader("Tabela: Clientes")
                res_c = requests.get(f"{API_URL}/clientes/", headers=headers)
                if res_c.status_code == 200:
                    st.dataframe(pd.DataFrame(res_c.json()))

    elif menu == "Inspeção de Dados":
        st.header("🔍 Verificação Interna do Banco")
        
        # Busca os usuários para ver o campo de atividade
        resp = requests.get(f"{API_URL}/usuarios/", headers=headers)
        if resp.status_code == 200:
            usuarios = resp.json()
            st.subheader("Tabela de Usuários (Bruto)")
            
            if usuarios:
                df_u = pd.DataFrame(usuarios)
                # Mostramos a hora exata que está no banco para comparar com o seu relógio
                cols = ['email', 'cliente_id', 'ultima_atividade']
                st.dataframe(df_u[[c for c in cols if c in df_u.columns]], use_container_width=True)
                
                # Debug de fuso horário
                st.info(f"🕒 Hora atual do seu navegador (Local): {datetime.now()}")
                st.info(f"🌍 Hora atual para comparação (UTC): {datetime.now(timezone.utc)}")
            else:
                st.warning("Nenhum usuário encontrado.")                            
                            