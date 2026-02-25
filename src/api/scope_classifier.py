"""
Classifier for deciding whether a user request is outside assistant business scope.
"""
import asyncio
import logging

from openai import OpenAI

from src.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

CLASSIFIER_MODEL = "gpt-4o-mini"

SCOPE_DESCRIPTION = (
    "Escopo permitido: atendimento da loja Shineray Rosario sobre motos/produtos, "
    "modelos, precos, pagamento, financiamento, simulacao, localizacao da loja, "
    "catalogo e direcionamento para WhatsApp."
)


def _classify_sync(text: str) -> bool:
    client = OpenAI(api_key=OPENAI_API_KEY)
    completion = client.chat.completions.create(
        model=CLASSIFIER_MODEL,
        temperature=0,
        max_tokens=5,
        messages=[
            {
                "role": "system",
                "content": (
                    "Classifique a mensagem do usuario como IN_SCOPE ou OUT_OF_SCOPE. "
                    f"{SCOPE_DESCRIPTION} "
                    "Responda somente uma palavra: IN_SCOPE ou OUT_OF_SCOPE."
                ),
            },
            {"role": "user", "content": text},
        ],
    )
    result = (completion.choices[0].message.content or "").strip().upper()
    return result == "OUT_OF_SCOPE"


async def is_out_of_scope(text: str) -> bool:
    """
    Returns True when the message is outside business scope.
    Defaults to False if classification fails.
    """
    try:
        return await asyncio.to_thread(_classify_sync, text)
    except Exception as exc:
        logger.warning("Scope classification failed, defaulting to IN_SCOPE: %s", exc)
        return False
