import os
import requests
import logging
from dotenv import load_dotenv

# Configura o log para vermos o que acontece no terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Carrega as variáveis de ambiente
load_dotenv()

TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")

def enviar_aviso_laudo_whatsapp(numero_destino: str, nome_cliente: str, nome_documento: str):
    """
    Dispara uma notificação via WhatsApp avisando que um documento está disponível.
    """
    if not TOKEN or not PHONE_ID:
        logger.warning("Credenciais do WhatsApp não configuradas. Notificação ignorada.")
        return False

    url = f"https://graph.facebook.com/v18.0/{PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

    # Montando a mensagem personalizada (Texto Livre, possível devido à janela de 24h)
    mensagem_texto = (
        f"🌿 *Portal Ambiental - Novo Documento*\n\n"
        f"Olá, equipe da *{nome_cliente}*.\n\n"
        f"Informamos que o documento *{nome_documento}* acaba de ser disponibilizado no seu portal.\n\n"
        f"Acesse o sistema para fazer o download."
    )

    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {
            "body": mensagem_texto
        }
    }

    # # Trocando temporariamente de 'text' para 'template' para forçar a entrega
    # payload = {
    #     "messaging_product": "whatsapp",
    #     "to": numero_destino,
    #     "type": "template",
    #     "template": {
    #         "name": "hello_world",
    #         "language": {
    #             "code": "en_US"
    #         }
    #     }
    # }

    try:
        logger.info(f"Enviando notificação para {numero_destino}...")
        resposta = requests.post(url, headers=headers, json=payload)
        
        if resposta.status_code == 200:
            logger.info("✅ WhatsApp enviado com sucesso!")
            return True
        else:
            logger.error(f"❌ Falha ao enviar WhatsApp: {resposta.text}")
            return False
            
    except Exception as e:
        logger.error(f"🚨 Erro interno ao tentar enviar WhatsApp: {e}")
        return False