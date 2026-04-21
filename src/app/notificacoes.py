import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

# ==========================================
# CONFIGURAÇÕES SMTP (via .env)
# ==========================================
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USUARIO = os.getenv("SMTP_USUARIO")       # ex: laudos@suaempresa.com.br
SMTP_SENHA = os.getenv("SMTP_SENHA")           # senha do e-mail ou app password
EMAIL_REMETENTE = os.getenv("EMAIL_REMETENTE") # ex: laudos@suaempresa.com.br
EMAIL_ASSUNTO_PADRAO = os.getenv("EMAIL_ASSUNTO_PADRAO", "Portal Ambiental — Novo documento disponível")


# ==========================================
# NOTIFICAÇÃO WHATSAPP (existente)
# ==========================================
def enviar_aviso_laudo_whatsapp(
    numero_destino: str,
    nome_cliente: str,
    nome_documento: str
):
    """
    Dispara notificação WhatsApp ao cliente quando um novo documento é disponibilizado.
    Atualmente em modo de log — será substituído pela Meta API.
    """
    try:
        # TODO: substituir pelo envio real via Meta API (Cloud API / WhatsApp Business)
        mensagem = (
            f"Olá, {nome_cliente}! "
            f"Um novo documento foi disponibilizado no seu portal: *{nome_documento}*. "
            f"Acesse o Portal Ambiental para visualizar e baixar."
        )
        logger.info(f"[WhatsApp] Para: {numero_destino} | Mensagem: {mensagem}")

    except Exception as e:
        logger.warning(f"[WhatsApp] Falha ao enviar notificação: {e}")


# ==========================================
# NOTIFICAÇÃO E-MAIL (novo)
# ==========================================
def enviar_email_documento_disponivel(
    email_destino: str,
    nome_cliente: str,
    nome_documento: str,
    hash_arquivo: Optional[str] = None
):
    """
    Envia e-mail ao cliente informando que um novo documento foi disponibilizado.
    Inclui o hash SHA-256 do arquivo como prova de integridade.
    """
    if not all([SMTP_USUARIO, SMTP_SENHA, EMAIL_REMETENTE]):
        logger.warning("[E-mail] Credenciais SMTP não configuradas. Notificação ignorada.")
        return

    try:
        data_hora = datetime.now().strftime("%d/%m/%Y às %H:%M")

        # Corpo do e-mail em HTML
        corpo_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: auto;">
            <div style="background-color: #2e7d32; padding: 20px; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">🌿 Portal Ambiental</h2>
            </div>
            <div style="background-color: #f9f9f9; padding: 24px; border: 1px solid #ddd; border-top: none; border-radius: 0 0 8px 8px;">
                <p>Olá, <strong>{nome_cliente}</strong>!</p>
                <p>Um novo documento foi disponibilizado em sua conta no <strong>Portal Ambiental</strong>:</p>

                <div style="background-color: #e8f5e9; border-left: 4px solid #2e7d32; padding: 12px 16px; margin: 16px 0; border-radius: 4px;">
                    <strong>📄 Documento:</strong> {nome_documento}<br>
                    <strong>📅 Disponibilizado em:</strong> {data_hora}
                    {f'<br><strong>🔒 Hash SHA-256:</strong> <code style="font-size: 11px;">{hash_arquivo}</code>' if hash_arquivo else ''}
                </div>

                <p>Acesse o portal para visualizar e baixar o documento.</p>

                <p style="color: #666; font-size: 12px; margin-top: 32px; border-top: 1px solid #ddd; padding-top: 12px;">
                    Este é um e-mail automático. O acesso e download do documento serão registrados 
                    para fins de conformidade e auditoria técnica.
                </p>
            </div>
        </body>
        </html>
        """

        # Monta a mensagem
        msg = MIMEMultipart("alternative")
        msg["Subject"] = EMAIL_ASSUNTO_PADRAO
        msg["From"] = EMAIL_REMETENTE
        msg["To"] = email_destino
        msg.attach(MIMEText(corpo_html, "html"))

        # Envia via SMTP com TLS
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(SMTP_USUARIO, SMTP_SENHA)
            servidor.sendmail(EMAIL_REMETENTE, email_destino, msg.as_string())

        logger.info(f"[E-mail] Enviado para {email_destino} | Documento: {nome_documento}")

    except smtplib.SMTPAuthenticationError:
        logger.error("[E-mail] Falha de autenticação SMTP. Verifique SMTP_USUARIO e SMTP_SENHA no .env.")
    except smtplib.SMTPException as e:
        logger.error(f"[E-mail] Erro SMTP ao enviar para {email_destino}: {e}")
    except Exception as e:
        logger.error(f"[E-mail] Erro inesperado ao enviar para {email_destino}: {e}")


# ==========================================
# NOTIFICAÇÃO COMBINADA (WhatsApp + E-mail)
# ==========================================
def notificar_documento_disponivel(
    email_destino: str,
    numero_whatsapp: str,
    nome_cliente: str,
    nome_documento: str,
    hash_arquivo: str = None
):
    """
    Dispara as duas notificações em sequência.
    Chamada como background task no upload de documento.
    """
    enviar_aviso_laudo_whatsapp(
        numero_destino=numero_whatsapp,
        nome_cliente=nome_cliente,
        nome_documento=nome_documento
    )
    enviar_email_documento_disponivel(
        email_destino=email_destino,
        nome_cliente=nome_cliente,
        nome_documento=nome_documento,
        hash_arquivo=hash_arquivo
    )
