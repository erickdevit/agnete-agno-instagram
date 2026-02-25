import os
import requests


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
    print(f"[TOOL] add_lead_to_nocodb called with: {nome}, {cpf}, {telefone}, {modelo_interesse}, {nascimento}, {cnh}")

    nocodb_token = os.getenv("NOCODB_API_TOKEN")
    nocodb_url = os.getenv("NOCODB_TABLE_URL", "")

    if not nocodb_token or not nocodb_url:
        return "SUCESSO (Simulação Local): Lead adicionado no NocoDB."

    headers = {
        "xc-token": nocodb_token,
        "Content-Type": "application/json"
    }

    payload = {
        "Nome": nome,
        "CPF": cpf,
        "Telefone": telefone,
        "Modelo de Interesse": modelo_interesse,
        "Nascimento": nascimento,
        "CNH": cnh
    }

    try:
        response = requests.post(nocodb_url, headers=headers, json=payload)
        if response.status_code in (200, 201):
            return "SUCESSO: Lead adicionado no NocoDB."
        else:
            return f"ERRO ao adicionar no NocoDB: {response.text}"
    except Exception as e:
        return f"ERRO na requisição para NocoDB: {str(e)}"
