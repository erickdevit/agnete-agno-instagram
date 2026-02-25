# Agente Instagram — vsimple

Versão minimalista do agente de atendimento via Instagram usando [Agno](https://github.com/agno-agi/agno) + FastAPI + Redis.

Sem interface web. Apenas o core do agente recebendo mensagens do Instagram via webhook e respondendo automaticamente.

---

## Estrutura

```
vsimple/
├── src/
│   ├── agent.py        # Inicialização do agente Agno
│   ├── app.py          # FastAPI app (só webhook + /health)
│   ├── config.py       # Variáveis de ambiente
│   ├── prompts.py      # System prompt do agente
│   ├── tools.py        # Ferramentas: NocoDB + notificação vendedores
│   └── api/
│       ├── instagram.py  # Envio de mensagens via Graph API
│       └── webhook.py    # Recepção de mensagens do Instagram
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Como usar

### 1. Configure o `.env`

```bash
cp .env.example .env
```

Edite o `.env` e preencha:

| Variável | Descrição |
|---|---|
| `OPENAI_API_KEY` | Chave da OpenAI |
| `INSTAGRAM_VERIFY_TOKEN` | Token que você define ao registrar o webhook no Meta |
| `INSTAGRAM_ACCESS_TOKEN` | Token de acesso da página Instagram |
| `NOCODB_API_TOKEN` | Token da API do NocoDB (opcional) |
| `NOCODB_TABLE_URL` | URL da tabela de leads no NocoDB (opcional) |
| `AUDIO_TRANSCRIPTION_MODEL` | Modelo OpenAI para transcrição de áudio (padrão: `gpt-4o-mini-transcribe`) |

### 2. Suba com Docker Compose

```bash
docker compose up --build -d
```

O serviço ficará disponível em `http://localhost:8000`.

### 3. Configure o webhook no Meta Developer

Na plataforma [Meta for Developers](https://developers.facebook.com):

1. Vá em **Webhooks** → **Instagram**
2. Endpoint: `https://seu-dominio.com/webhook`
3. Verify Token: o mesmo valor que você colocou em `INSTAGRAM_VERIFY_TOKEN`
4. Assine o campo **messages**

> ⚠️ O endpoint precisa ser HTTPS público. Para testes locais, use [ngrok](https://ngrok.com):
> ```bash
> ngrok http 8000
> ```

### 4. Verifique saúde do serviço

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

### 5. Ver logs em tempo real

```bash
docker compose logs -f agent
```

---

## Personalizando o agente

- **System prompt:** edite `src/prompts.py`
- **Ferramentas:** edite `src/tools.py` para adicionar integrações
- **Modelo LLM:** altere `AGENT_MODEL` no `.env` (padrão: `gpt-4o-mini`)

---

## Dependências

- Python 3.11+
- [agno](https://github.com/agno-agi/agno)
- FastAPI + Uvicorn
- Redis (memória de sessão/conversação)
- httpx, python-dotenv, pydantic, requests
