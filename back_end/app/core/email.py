import logging
import os
from email.message import EmailMessage

import aiosmtplib
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("email")

SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USER
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "SaaS Gestão Académica")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() != "false"


async def enviar_email(
    destinatario: str, assunto: str, corpo_html: str,
    anexo_nome: str | None = None, anexo_content_type: str | None = None, anexo_conteudo: bytes | None = None,
) -> bool:
    """
    Envia um e-mail transacional (best-effort).

    Não propaga exceções: o envio de e-mail nunca deve cancelar a
    operação principal (ex.: registar uma escola, vincular um
    responsável) só porque o SMTP falhou ou nem está configurado. Quem
    chamar isto deve tratá-lo como "e se não enviar, paciência" — não
    como uma dependência crítica do fluxo (o retry em caso de falha
    passageira vive na fila, ver app/core/fila_notificacoes.py).

    anexo_*: opcional, um único anexo (ex.: circular de um Comunicado —
    ver app/api/v1/comunicacoes.py). Os três têm de vir juntos ou nenhum.

    Devolve True se o envio foi bem-sucedido, False caso contrário (e
    regista o motivo nos logs).
    """
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASSWORD or not SMTP_FROM_EMAIL:
        logger.warning(
            "SMTP não configurado (SMTP_HOST/SMTP_USER/SMTP_PASSWORD/SMTP_FROM_EMAIL "
            "em falta no .env) — e-mail para %s NÃO foi enviado. Assunto: %s",
            destinatario, assunto
        )
        return False

    mensagem = EmailMessage()
    mensagem["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    mensagem["To"] = destinatario
    mensagem["Subject"] = assunto
    mensagem.set_content("Este e-mail requer um cliente de correio compatível com HTML.")
    mensagem.add_alternative(corpo_html, subtype="html")

    if anexo_conteudo and anexo_nome:
        tipo_principal, _, subtipo = (anexo_content_type or "application/octet-stream").partition("/")
        mensagem.add_attachment(
            anexo_conteudo, maintype=tipo_principal or "application", subtype=subtipo or "octet-stream", filename=anexo_nome
        )

    try:
        await aiosmtplib.send(
            mensagem,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            start_tls=SMTP_USE_TLS,
        )
        logger.info("E-mail enviado para %s (assunto: %s)", destinatario, assunto)
        return True
    except Exception:
        logger.exception("Falha ao enviar e-mail para %s (assunto: %s)", destinatario, assunto)
        return False


def template_base(titulo: str, corpo_html: str) -> str:
    """Envelope HTML simples e consistente para os e-mails transacionais."""
    return f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; color: #1e293b;">
      <h2 style="color: #2563eb; margin-bottom: 8px;">{titulo}</h2>
      <div style="font-size: 14px; line-height: 1.6;">{corpo_html}</div>
      <p style="font-size: 12px; color: #94a3b8; margin-top: 32px;">
        SaaS Gestão Académica — este é um e-mail automático, não responda.
      </p>
    </div>
    """
