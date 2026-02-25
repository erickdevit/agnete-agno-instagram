import os
import requests
import logging
from pydantic import ValidationError
from src.models import LeadModel
from src.config import NOCODB_API_TOKEN, NOCODB_TABLE_URL

logger = logging.getLogger(__name__)


def add_lead_to_nocodb(nome: str, cpf: str, telefone: str, modelo_interesse: str, nascimento: str, cnh: str) -> str:
    """
    Adiciona os dados do cliente (lead) no banco de dados NocoDB.
    Chame esta função sempre que o cliente fornecer todos os dados necessários (Nome, CPF, Telefone, Modelo de Interesse, Data de Nascimento e se possui CNH).

    Args:
        nome (str): Nome do cliente.
        cpf (str): CPF do cliente no formato 000.000.000-00.
        telefone (str): Telefone do cliente no formato (00) 00000-0000.
        modelo_interesse (str): O modelo exato da moto que o cliente tem interesse.
        nascimento (str): Data de nascimento do cliente no formato 00/00/0000.
        cnh (str): SIM ou NÃO, indicando se o cliente possui CNH.

    Returns:
        str: Mensagem de retorno sobre o status do salvamento.
    """
    logger.info("[TOOL] add_lead_to_nocodb called: nome=%s, cpf=%s..., telefone=%s", nome, cpf[:8], telefone)
    
    # Validate input data
    try:
        lead = LeadModel(
            nome=nome,
            cpf=cpf,
            telefone=telefone,
            modelo_interesse=modelo_interesse,
            nascimento=nascimento,
            cnh=cnh
        )
    except ValidationError as e:
        error_msg = f"Dados inválidos: "
        errors = []
        for error in e.errors():
            field = error['loc'][0]
            msg = error['msg']
            errors.append(f"{field} ({msg})")
        error_msg += ", ".join(errors)
        logger.warning("[TOOL] Validation error: %s", error_msg)
        return f"ERRO: {error_msg}"

    if not NOCODB_API_TOKEN or not NOCODB_TABLE_URL:
        logger.info("[TOOL] NocoDB not configured, returning local simulation")
        return "SUCESSO (Simulação Local): Lead adicionado no NocoDB."

    headers = {
        "xc-token": NOCODB_API_TOKEN,
        "Content-Type": "application/json"
    }

    payload = {
        "Nome": lead.nome,
        "CPF": lead.cpf,
        "Telefone": lead.telefone,
        "Modelo de Interesse": lead.modelo_interesse,
        "Nascimento": lead.nascimento,
        "CNH": lead.cnh
    }

    try:
        response = requests.post(NOCODB_TABLE_URL, headers=headers, json=payload, timeout=10)
        if response.status_code in (200, 201):
            logger.info("[TOOL] Lead successfully saved to NocoDB: %s", nome)
            return "SUCESSO: Lead adicionado no NocoDB."
        else:
            error_msg = f"ERRO ao adicionar no NocoDB: {response.status_code} - {response.text}"
            logger.error("[TOOL] %s", error_msg)
            return error_msg
    except requests.Timeout:
        error_msg = "ERRO: Timeout ao conectar com NocoDB"
        logger.error("[TOOL] %s", error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"ERRO na requisição para NocoDB: {str(e)}"
        logger.error("[TOOL] %s", error_msg, exc_info=True)
        return error_msg
