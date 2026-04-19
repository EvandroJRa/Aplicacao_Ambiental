import requests
import os
import json
from dotenv import load_dotenv

# ==========================================
# CONFIGURAÇÕES INICIAIS
# ==========================================
# Troque para http://127.0.0.1:8000 se for testar localmente
API_URL = "https://aplicacao-ambiental.onrender.com" 

# Credenciais do seu Admin atual para o script ter permissão
load_dotenv()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL")
ADMIN_SENHA = os.getenv("ADMIN_SENHA")

# Trava de segurança: impede o script de rodar se esquecer de configurar o .env
if not ADMIN_EMAIL or not ADMIN_SENHA:
    print("❌ ERRO DE SEGURANÇA: Credenciais não encontradas.")
    print("Certifique-se de que o arquivo .env existe e contém ADMIN_EMAIL e ADMIN_SENHA.")
    exit()

def print_sucesso(msg):
    print(f"✅ [SUCESSO] {msg}")

def print_erro(msg, detalhes=""):
    print(f"❌ [ERRO] {msg}")
    if detalhes:
        print(f"   Detalhes: {detalhes}")

# ==========================================
# 1. LOGIN DO ADMIN
# ==========================================
print("🔄 Iniciando rotina de MOCK de dados...")
res_login = requests.post(f"{API_URL}/token", data={"username": ADMIN_EMAIL, "password": ADMIN_SENHA})

if res_login.status_code != 200:
    print_erro("Falha no login do Admin. Verifique as credenciais no script.")
    exit()

token = res_login.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}
print_sucesso("Login Admin realizado com sucesso.")
# ==========================================

# Quantidade de clientes que você quer gerar
quantidade_clientes = 5

print(f"⚙️ Iniciando a criação de {quantidade_clientes} clientes mock...\n")

for i in range(1, quantidade_clientes + 1):
    print(f"--- 🏢 GERANDO CLIENTE {i} ---")
    
    # ==========================================
    # 2. CADASTRAR CLIENTE MOCK (Dinâmico)
    # ==========================================
    dados_cliente = {
        "nome": f"Empresa Mock Ambiental {i} LTDA",
        "cnpj": f"00.000.000/000{i}-99",
        "whatsapp_contato": f"4999999990{i}",
        "email": f"contato{i}@mockambiental.com",
        "senha_provisoria": "Teste@123",
        "codigo_cliente": f"MOCK-00{i}"
    }

    res_cliente = requests.post(f"{API_URL}/clientes/", json=dados_cliente, headers=headers)
    if res_cliente.status_code in [200, 201]:
        cliente_id = res_cliente.json().get("id")
        print_sucesso(f"Cliente '{dados_cliente['nome']}' criado! (ID: {cliente_id})")
    else:
        print_erro(f"Falha ao criar cliente {i}.", res_cliente.text)
        continue # Pula para o próximo número se der erro

    # ==========================================
    # 3. CADASTRAR USUÁRIO DO CLIENTE (Dinâmico)
    # ==========================================
    email_usuario = f"teste{i}@mockambiental.com"
    dados_usuario = {
        "email": email_usuario,
        "cliente_id": cliente_id,
        "senha": "Teste@123"
    }

    res_usuario = requests.post(f"{API_URL}/usuarios/", json=dados_usuario, headers=headers)
    if res_usuario.status_code in [200, 201]:
        print_sucesso(f"Usuário criado: {email_usuario}")
    else:
        print_erro(f"Erro ao criar usuário {i}.", res_usuario.text)

    # ==========================================
    # 4. CRIAR PDF FALSO E FAZER UPLOAD (Dinâmico)
    # ==========================================
    nome_arquivo = f"laudo_mock_cliente_{i}.pdf"

    # Cria o PDF temporário
    with open(nome_arquivo, "wb") as f:
        f.write(f"%PDF-1.4\n%Fake PDF for Client {i}\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n".encode())

    # Faz o Upload
    with open(nome_arquivo, "rb") as f:
        files = {"arquivo": (nome_arquivo, f, "application/pdf")}
        data = {
            "cliente_id": cliente_id,
            "tipo_documento": "Laudo Laboratorial de Teste"
        }
        
        res_upload = requests.post(f"{API_URL}/documentos/upload", headers=headers, files=files, data=data)

    if res_upload.status_code in [200, 201]:
        print_sucesso(f"Documento vinculado ao Cliente {i} com sucesso!\n")
    else:
        print_erro(f"Falha no upload do documento {i}.", res_upload.text)

    # Limpa o arquivo PDF da sua máquina após o upload
    if os.path.exists(nome_arquivo):
        os.remove(nome_arquivo)

print("🚀 === ROTINA CONCLUÍDA === 🚀")
print("Você pode testar os acessos usando as contas:")
for i in range(1, quantidade_clientes + 1):
    print(f"👉 teste{i}@mockambiental.com (Senha: Teste@123)")