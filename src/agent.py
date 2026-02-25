from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.db.redis import RedisDb
import os
from src.tools import add_lead_to_nocodb
from src.prompts import SYSTEM_PROMPT
from src.config import AGENT_MODEL, AGENT_NAME, REDIS_URL


def get_agent(session_id: str = "default_session") -> Agent:
    db = RedisDb(db_url=REDIS_URL, expire=300)
    return Agent(
        model=OpenAIChat(id=AGENT_MODEL),
        description=AGENT_NAME,
        instructions=SYSTEM_PROMPT,
        tools=[add_lead_to_nocodb],
        db=db,
        add_history_to_context=True,
        num_history_runs=10,
        learning=False,
        markdown=False,
        session_id=session_id
    )
