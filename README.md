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
├── requirements.txt
├── .dockerignore
└── example.env
```

---

## Deploy no Easypanel

Este projeto está pronto para deploy no Easypanel (ou qualquer infra baseada em Docker).

### 1. Crie o Serviço
No Easypanel, crie um **App Service** e aponte para este repositório.

### 2. Configure as Variáveis de Ambiente
Copie o conteúdo de `example.env` e cole na aba **Environment** do serviço no Easypanel.
Preencha os valores obrigatórios (`OPENAI_API_KEY`, tokens do Instagram, etc.).

A variável `PORT` será injetada automaticamente pelo Easypanel (padrão 80), mas o container está configurado para aceitar qualquer porta via `$PORT`. Se necessário, defina `PORT=8000` manualmente ou mapeie a porta externa 80 para a interna 8000.

### 3. Deploy
Clique em **Deploy**. O build usará o `Dockerfile` otimizado (multi-stage).

### 4. Healthcheck
Configure o healthcheck no Easypanel (se não detectar automático):
- Path: `/health`
- Port: `8000` (ou a que você definiu em `$PORT`)

### 5. Logs
Os logs estruturados são enviados para o stdout e podem ser vistos na aba **Logs** do serviço.

---

## Rodando Localmente com Docker

### 1. Configure o `.env`

```bash
cp example.env .env
# Edite .env com suas chaves
```

### 2. Suba com Docker Compose

```bash
docker compose up --build -d
```

O serviço ficará disponível em `http://localhost:8000`.

### 3. Verifique saúde do serviço

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

---

## Configuração do Webhook (Meta)

1. Vá em **Webhooks** → **Instagram** no [Meta for Developers](https://developers.facebook.com).
2. Endpoint: `https://seu-dominio.com/webhook`
3. Verify Token: o mesmo valor de `INSTAGRAM_VERIFY_TOKEN`
4. Assine o campo **messages**

---

## Dependências

- Python 3.11+ (slim image)
- [agno](https://github.com/agno-agi/agno)
- FastAPI + Gunicorn + Uvicorn
- Redis (memória de sessão/conversação)
- ffmpeg (para processamento de áudio)
