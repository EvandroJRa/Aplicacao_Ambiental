import streamlit as st
import requests
import pandas as pd
import urllib.parse # <-- Nova importação para consertar os espaços nos links!

# Configuração da página
st.set_page_config(page_title="Portal Ambiental", page_icon="🌿", layout="wide")
API_URL = "http://localhost:8000"

st.title("🌿 Portal Ambiental")
st.markdown("Bem-vindo ao sistema de gestão de laudos e ofícios.")
st.divider()

try:
    # 1. Puxa a lista de clientes da API
    resposta_clientes = requests.get(f"{API_URL}/clientes/")
    
    if resposta_clientes.status_code == 200:
        clientes = resposta_clientes.json()
        
        if clientes:
            opcoes_clientes = {cliente['nome']: cliente['id'] for cliente in clientes}
            
            # --- MENU LATERAL ---
            st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3039/3039849.png", width=100)
            st.sidebar.header("Filtros de Busca")
            cliente_selecionado_nome = st.sidebar.selectbox("Selecione o Cliente:", list(opcoes_clientes.keys()))
            cliente_id = opcoes_clientes[cliente_selecionado_nome]
            
            # --- ÁREA PRINCIPAL ---
            st.subheader(f"📊 Painel de Controle: {cliente_selecionado_nome}")
            
            # BLOCO 1: PONTOS DE MONITORAMENTO
            st.markdown("### 📍 Pontos de Monitoramento Cadastrados")
            resposta_pontos = requests.get(f"{API_URL}/clientes/{cliente_id}/pontos/")
            
            if resposta_pontos.status_code == 200:
                pontos = resposta_pontos.json()
                if pontos:
                    df_pontos = pd.DataFrame(pontos)
                    df_pontos = df_pontos[['nome_ponto', 'tipo', 'latitude', 'longitude', 'ativo']]
                    st.dataframe(df_pontos, use_container_width=True, hide_index=True)
                else:
                    st.info("Nenhum ponto de monitoramento cadastrado para esta empresa.")
            else:
                st.error("Erro ao buscar os pontos de monitoramento.")
                
            # BLOCO 2: DOCUMENTOS E LAUDOS
            st.divider()
            st.markdown("### 📄 Documentos e Laudos Disponíveis")
            resposta_docs = requests.get(f"{API_URL}/clientes/{cliente_id}/documentos/")
            
            if resposta_docs.status_code == 200:
                documentos = resposta_docs.json()
                if documentos:
                    for doc in documentos:
                        col1, col2, col3 = st.columns([3, 2, 2])
                        with col1:
                            st.write(f"**{doc['tipo_documento']}**")
                        with col2:
                            data_comp = doc.get('competencia')
                            st.write(f"Competência: {data_comp if data_comp else 'N/A'}")
                        with col3:
                            # CORREÇÃO AQUI: Transforma espaços em %20 para a web entender
                            caminho_seguro = urllib.parse.quote(doc['url_arquivo'])
                            url_download = f"{API_URL}/{caminho_seguro}"
                            
                            st.markdown(f"[📥 Baixar Arquivo]({url_download})")
                        st.write("---")
                else:
                    st.info("Nenhum documento ou laudo disponível para download.")
            else:
                st.error("Erro ao buscar os documentos.")
                
        else:
            st.warning("Nenhum cliente cadastrado no sistema ainda.")
            
except requests.exceptions.ConnectionError:
    st.error("🚨 Não foi possível conectar à API. Verifique se o uvicorn está rodando no terminal.")