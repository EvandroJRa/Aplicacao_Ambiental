import os
import requests
from dotenv import load_dotenv

# Carrega as senhas do arquivo .env
load_dotenv()

TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
NUMERO_DESTINO = os.getenv("MEU_NUMERO_TESTE")

def disparar_teste_whatsapp():
    print(f"🔄 Preparando disparo para o número: {NUMERO_DESTINO}...")
    
    # A URL oficial da Meta para envio de mensagens
    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    
    # O cabeçalho de segurança com o nosso Token
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }
    
    # O "pacote" de dados que o WhatsApp exige
    payload = {
        "messaging_product": "whatsapp",
        "to": NUMERO_DESTINO,
        "type": "template",
        "template": {
            "name": "hello_world", # Template padrão aprovado da Meta
            "language": {
                "code": "en_US"
            }
        }
    }
    
    # O disparo real (Fazendo a requisição POST para a Meta)
    try:
        resposta = requests.post(url, headers=headers, json=payload)
        
        if resposta.status_code == 200:
            print("✅ SUCESSO! A mensagem foi entregue aos servidores da Meta.")
            print("📱 Olhe para o seu celular agora!")
        else:
            print(f"❌ ERRO {resposta.status_code}: A Meta recusou a mensagem.")
            print("Detalhes do erro:", resposta.json())
            
    except Exception as e:
        print(f"🚨 Erro crítico no Python: {e}")

# Executa a função
if __name__ == "__main__":
    disparar_teste_whatsapp()