import requests
import logging
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = (
    os.getenv("API_URL_NOTIFICACAO", "http://localhost:3030/api/v1/notificacao")
    + "/mensagem"
)


def enviar_notificacao(mensagem, phone):
    """Envia notificação via API para o número de telefone informado."""
    payload = {
        "message": mensagem,
        "phone": phone,
    }
    try:
        response = requests.post(API_URL, json=payload, timeout=5)
        if response.status_code == 200:
            logging.info(f"Notificação enviada para {phone}")
        else:
            logging.warning(
                f"Falha ao enviar notificação: {response.status_code} - {response.text}"
            )
    except Exception as e:
        logging.error(f"Erro ao enviar notificação: {e}")
