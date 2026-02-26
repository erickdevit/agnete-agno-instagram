# Agente Instagram (Agno + FastAPI + Redis)

Documentação oficial do projeto de atendimento automatizado via Instagram Direct para a operação da **Shineray Rosário**.

Este serviço recebe eventos de webhook do Instagram (Meta Graph API), agrega mensagens de usuário em janelas curtas, processa o contexto com um agente Agno, e envia respostas textuais (e opcionalmente áudio) de volta ao Instagram.

---

## 1) Visão Geral

### Objetivo

Fornecer um backend enxuto para atendimento semi-automatizado no Instagram, com foco em:

- qualificação de leads;
- coleta estruturada de dados;
- roteamento para atendimento humano no WhatsApp;
- persistência opcional de lead em NocoDB;
- proteção operacional contra conflitos entre atendimento manual e automático.

### Principais componentes

- **FastAPI**: expõe endpoints de saúde, webhook e mídia de áudio.
- **Agno Agent**: orquestra LLM, memória de sessão e ferramentas.
- **Redis**: usado para memória de conversa, buffer de mensagens e bloqueio por interação manual.
- **OpenAI API**: usada para chat, classificação de escopo, transcrição e síntese de áudio.
- **Meta Graph API**: canal de envio/recebimento de mensagens do Instagram.
- **NocoDB (opcional)**: persistência de leads via ferramenta do agente.

---

## 2) Arquitetura de Alto Nível

```text
Instagram User
   |
   | (DM / áudio)
   v
Meta Webhook -> FastAPI (/webhook)
   |                |
   |                +--> validação de evento + roteamento
   |
   +--> Buffer Redis (janela de silêncio ~5s)
             |
             v
        Agno Agent (OpenAIChat)
             |
             +--> Tool: add_lead_to_nocodb (opcional)
             |
             v
      Instagram Graph API (/me/messages)

Fluxos auxiliares:
- áudio recebido -> download -> ffmpeg -> transcrição
- resposta em áudio (opcional) -> TTS -> arquivo .wav temporário -> /media/audio/{file}
- interação manual detectada -> lock temporário em Redis (bloqueio do agente)
```

---

## 3) Estrutura do Repositório

```text
.
├── src/
│   ├── app.py                   # App FastAPI e endpoint /health
│   ├── config.py                # Carregamento e validação de variáveis de ambiente
│   ├── agent.py                 # Fábrica do agente Agno + tool registry
│   ├── prompts.py               # Prompt de sistema do agente
│   ├── tools.py                 # Ferramentas do agente (integração NocoDB)
│   ├── models.py                # Modelos Pydantic para validações
│   ├── interaction_blocker.py   # Bloqueio quando há interação manual
│   └── api/
│       ├── webhook.py           # Endpoints /webhook e processamento assíncrono
│       ├── instagram.py         # Envio de texto/áudio para Meta Graph API
│       ├── message_buffer.py    # Buffer por usuário para agrupar mensagens
│       ├── scope_classifier.py  # Classificação IN/OUT-of-scope
│       ├── transcription.py     # Download e transcrição de áudio recebido
│       ├── audio_reply.py       # Geração de resposta em áudio e URL pública
│       └── openai_client.py     # Cliente OpenAI compartilhado
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 4) Fluxo Funcional do Atendimento

1. **Meta chama `POST /webhook`** com eventos de mensagem.
2. O serviço filtra eventos relevantes e ignora ecos/outgoing.
3. Mensagens do usuário entram em **buffer no Redis**.
4. Após ~5s de silêncio, mensagens são combinadas em lote.
5. O texto final é validado e enviado ao agente Agno.
6. O agente responde e pode acionar ferramentas (ex.: NocoDB).
7. A resposta é enviada via Graph API em blocos (até 1000 chars por envio).

### Fluxo de áudio recebido

1. attachment de áudio é extraído do payload;
2. arquivo é baixado (com fallback sem header auth em certos links assinados);
3. quando possível, é convertido para WAV mono 16kHz via `ffmpeg`;
4. transcrição é executada com modelo configurado;
5. se transcrição falhar, o usuário recebe fallback pedindo texto.

### Fluxo de resposta em áudio (opcional)

1. classificador detecta caso fora de escopo (ou cenário aplicável);
2. texto de resposta é sintetizado (TTS), convertido para WAV e salvo temporariamente;
3. endpoint `/media/audio/{file_name}` expõe arquivo;
4. API envia attachment de áudio por URL pública HTTPS.

---

## 5) Pré-requisitos

- Docker e Docker Compose instalados.
- Conta Meta for Developers com app configurado para Instagram Messaging.
- Chave de API OpenAI válida.
- (Opcional) instância NocoDB com tabela de leads.
- (Recomendado) domínio HTTPS público para webhook e mídia.

---

## 6) Configuração de Ambiente

Crie seu arquivo local de ambiente:

```bash
cp .env.example .env
```

### Variáveis disponíveis

| Variável | Obrigatória | Descrição |
|---|---:|---|
| `OPENAI_API_KEY` | Sim | Chave da OpenAI utilizada por chat/transcrição/TTS/classificador. |
| `INSTAGRAM_VERIFY_TOKEN` | Sim (produção) | Token de verificação do webhook no Meta. |
| `INSTAGRAM_ACCESS_TOKEN` | Sim (produção) | Token de envio de mensagens pela Graph API. |
| `INSTAGRAM_API_VERSION` | Não | Versão da Graph API (padrão `v25.0`). |
| `PUBLIC_BASE_URL` | Recomendado | Base pública usada para expor áudio (`/media/audio/...`). |
| `REDIS_URL` | Sim | URL do Redis para memória, buffers e locks. |
| `AGENT_MODEL` | Não | Modelo de chat do agente (padrão `gpt-4o-mini`). |
| `AGENT_NAME` | Não | Nome/descrição do agente no runtime. |
| `NOCODB_API_TOKEN` | Opcional | Token para gravar leads no NocoDB. |
| `NOCODB_TABLE_URL` | Opcional | Endpoint da tabela de leads no NocoDB. |
| `AUDIO_TRANSCRIPTION_MODEL` | Não | Modelo de transcrição (padrão `gpt-4o-mini-transcribe`). |
| `AUDIO_REPLY_MODEL` | Não | Modelo TTS para respostas em áudio (padrão `gpt-4o-mini-tts`). |
| `AUDIO_REPLY_VOICE` | Não | Voz do TTS (padrão `alloy`). |
| `ENABLE_INSTAGRAM_AUDIO_REPLY` | Não | Habilita envio de resposta em áudio (`true/false`). |
| `MAX_TRANSCRIPTION_AUDIO_MB` | Não | Limite de tamanho de áudio para transcrição. |
| `MAX_TRANSCRIPTION_AUDIO_SECONDS` | Não | Limite de duração do áudio para transcrição. |
| `MAX_AGENT_INPUT_CHARS` | Não | Limite de caracteres enviados ao agente por lote. |
| `MAX_AUDIO_REPLY_CHARS` | Não | Limite de caracteres para sintetizar áudio curto. |

> Observação: em execução local sem Meta/NocoDB completos, parte dos fluxos será simulada/parcial.

---

## 7) Execução Local com Docker

Suba os serviços:

```bash
docker compose up --build -d
```

Verifique saúde:

```bash
curl http://localhost:8000/health
```

Acompanhe logs:

```bash
docker compose logs -f agent
```

Derrube ambiente:

```bash
docker compose down
```

---

## 8) Configuração do Webhook no Meta

No [Meta for Developers](https://developers.facebook.com):

1. Acesse **Webhooks** e selecione **Instagram**.
2. Configure callback URL: `https://<seu-dominio>/webhook`.
3. Configure verify token com `INSTAGRAM_VERIFY_TOKEN`.
4. Assine o campo **messages**.
5. Garanta HTTPS válido (certificado confiável).

Para testes locais, exponha `localhost:8000` com túnel HTTPS (ex.: ngrok).

---

## 9) Operação e Observabilidade

### Logs importantes

- `[RECV]` mensagens recebidas.
- `[SEND]` mensagens enviadas.
- `[OUTGOING]` eventos de eco/saída detectados.
- `[BLOCK]` estados de bloqueio por interação manual.
- `[TOOL]` execução de ferramentas.

### Saúde do serviço

- endpoint `GET /health` retorna `{"status":"ok"}` quando app ativo.

### Comportamentos de proteção

- rejeita webhook sem header `X-Hub-Signature-256`;
- limita tamanho/duração de áudio para transcrição;
- limita tamanho de entrada para o agente;
- retry com backoff no envio ao Graph API.

---

## 10) Guia Profissional: Criar e Expandir Ferramentas do Agente

Esta seção foi escrita para ser **operacional**, com exemplos reais e prontos para adaptação no código atual.

### 10.1 O que é uma ferramenta neste projeto

Uma ferramenta é uma função Python registrada no `Agent(...)` em `src/agent.py`. O LLM pode chamar essa função durante a conversa para executar ações de negócio fora do “texto puro” (consultar sistemas, gravar dados, abrir atendimento etc.).

No estado atual, a ferramenta ativa é `add_lead_to_nocodb` em `src/tools.py`.

### 10.2 Regras obrigatórias para qualquer nova ferramenta

Antes de codar, aplique estas regras:

1. **Assinatura explícita**: parâmetros simples e autoexplicativos.
2. **Validação forte**: criar `BaseModel` em `src/models.py` com `field_validator`.
3. **Timeout em toda chamada externa**: nunca deixar request sem timeout.
4. **Retorno canônico para o agente**: sempre iniciar com `SUCESSO:` ou `ERRO:`.
5. **Logs estruturados**: prefixe logs com `[TOOL] NomeDaFerramenta`.
6. **Falha segura**: erro da integração nunca deve derrubar o webhook.

### 10.3 Onde editar no projeto (mapa prático)

Para adicionar uma ferramenta nova, você sempre tocará estes arquivos:

- `src/models.py`: schema de entrada/normalização de dados.
- `src/tools.py`: implementação da ferramenta (regra de negócio + integração).
- `src/agent.py`: registro no array `tools=[...]`.
- `src/prompts.py`: regras para o agente saber **quando** chamar a ferramenta.
- `README.md`: documentação do contrato e exemplos de uso.

### 10.4 Fluxo padrão de implementação (passo a passo)

#### Passo 1 — Defina o contrato funcional

Documente:

- nome da função;
- parâmetros obrigatórios;
- pré-condições (o que o usuário deve informar antes da chamada);
- formato exato de retorno para sucesso e erro.

#### Passo 2 — Crie modelo de validação em `src/models.py`

- normalize entrada (`strip`, uppercase/lowercase, regex);
- rejeite dados incompletos com erro claro;
- evite lógica de integração no model (somente validação).

#### Passo 3 — Implemente a ferramenta em `src/tools.py`

- inicie com log da chamada;
- valide com Pydantic;
- faça request com timeout;
- trate exceções e converta em retorno `ERRO:` amigável.

#### Passo 4 — Registre em `src/agent.py`

Inclua a função nova no array `tools=[...]` do `Agent(...)`.

#### Passo 5 — Atualize o comportamento em `src/prompts.py`

Diga de forma explícita:

- quando a ferramenta deve ser acionada;
- quais dados devem ser coletados antes;
- quando **não** chamar a ferramenta.

#### Passo 6 — Valide ponta a ponta

- suba app local;
- envie mensagens que devem e não devem acionar a tool;
- confirme logs e retorno canônico.

---

### 10.5 Exemplo real #1 — Ferramenta de consulta de estoque

Objetivo: permitir ao agente consultar disponibilidade de modelo por cidade em um serviço externo.

#### 10.5.1 Adicionar variáveis no `.env.example`

```env
STOCK_API_URL=https://api.seudominio.com/estoque
STOCK_API_TOKEN=seu_token_de_estoque
```

#### 10.5.2 Adicionar variáveis em `src/config.py`

```python
STOCK_API_URL = os.getenv("STOCK_API_URL", "")
STOCK_API_TOKEN = (os.getenv("STOCK_API_TOKEN") or "").strip()
```

#### 10.5.3 Criar model em `src/models.py`

```python
from pydantic import BaseModel, Field, field_validator

class StockQueryModel(BaseModel):
    modelo: str = Field(..., min_length=2, max_length=60)
    cidade: str = Field(..., min_length=2, max_length=60)

    @field_validator("modelo", "cidade")
    @classmethod
    def normalize_text(cls, v: str) -> str:
        value = " ".join(v.strip().split())
        if not value:
            raise ValueError("campo obrigatório")
        return value
```

#### 10.5.4 Criar tool em `src/tools.py`

```python
import requests
from pydantic import ValidationError
from src.models import StockQueryModel
from src.config import STOCK_API_URL, STOCK_API_TOKEN


def consultar_estoque(modelo: str, cidade: str) -> str:
    logger.info("[TOOL] consultar_estoque called: modelo=%s cidade=%s", modelo, cidade)

    try:
        data = StockQueryModel(modelo=modelo, cidade=cidade)
    except ValidationError as e:
        return f"ERRO: parâmetros inválidos ({e.errors()})"

    if not STOCK_API_URL or not STOCK_API_TOKEN:
        return "ERRO: integração de estoque não configurada"

    headers = {"Authorization": f"Bearer {STOCK_API_TOKEN}"}
    params = {"modelo": data.modelo, "cidade": data.cidade}

    try:
        response = requests.get(STOCK_API_URL, headers=headers, params=params, timeout=8)
        response.raise_for_status()
        payload = response.json()
        quantidade = int(payload.get("quantidade", 0))

        if quantidade > 0:
            return f"SUCESSO: há {quantidade} unidade(s) de {data.modelo} em {data.cidade}."
        return f"SUCESSO: no momento não há estoque de {data.modelo} em {data.cidade}."
    except requests.Timeout:
        return "ERRO: consulta de estoque expirou, tente novamente em instantes"
    except Exception as exc:
        logger.error("[TOOL] consultar_estoque failed: %s", exc, exc_info=True)
        return "ERRO: falha ao consultar estoque"
```

#### 10.5.5 Registrar no agente em `src/agent.py`

```python
from src.tools import add_lead_to_nocodb, consultar_estoque

# ...
tools=[add_lead_to_nocodb, consultar_estoque]
```

#### 10.5.6 Atualizar prompt em `src/prompts.py`

Inclua regra como:

- “Quando o usuário perguntar disponibilidade imediata de um modelo por cidade, colete `modelo` e `cidade` e chame `consultar_estoque`.”

---

### 10.6 Exemplo real #2 — Ferramenta para agendar test ride

Objetivo: criar um agendamento em API de CRM quando o usuário já estiver qualificado.

#### 10.6.1 Adicionar variáveis no `.env.example`

```env
TEST_RIDE_API_URL=https://api.seudominio.com/test-ride
TEST_RIDE_API_TOKEN=seu_token_de_agendamento
```

#### 10.6.2 Adicionar variáveis em `src/config.py`

```python
TEST_RIDE_API_URL = os.getenv("TEST_RIDE_API_URL", "")
TEST_RIDE_API_TOKEN = (os.getenv("TEST_RIDE_API_TOKEN") or "").strip()
```

#### 10.6.3 Criar model em `src/models.py`

```python
from pydantic import BaseModel, Field, field_validator
from datetime import datetime

class TestRideBookingModel(BaseModel):
    nome: str = Field(..., min_length=3, max_length=100)
    telefone: str = Field(..., min_length=10, max_length=20)
    modelo: str = Field(..., min_length=2, max_length=60)
    data_preferida: str = Field(..., description="DD/MM/YYYY")

    @field_validator("data_preferida")
    @classmethod
    def validate_date(cls, v: str) -> str:
        datetime.strptime(v, "%d/%m/%Y")
        return v
```

#### 10.6.4 Criar tool em `src/tools.py`

```python
import requests
from pydantic import ValidationError
from src.models import TestRideBookingModel
from src.config import TEST_RIDE_API_URL, TEST_RIDE_API_TOKEN


def agendar_test_ride(nome: str, telefone: str, modelo: str, data_preferida: str) -> str:
    logger.info("[TOOL] agendar_test_ride called: nome=%s telefone=%s", nome, telefone)

    try:
        data = TestRideBookingModel(
            nome=nome,
            telefone=telefone,
            modelo=modelo,
            data_preferida=data_preferida,
        )
    except ValidationError as e:
        return f"ERRO: dados inválidos para agendamento ({e.errors()})"

    if not TEST_RIDE_API_URL or not TEST_RIDE_API_TOKEN:
        return "ERRO: integração de agendamento não configurada"

    payload = {
        "nome": data.nome,
        "telefone": data.telefone,
        "modelo": data.modelo,
        "data_preferida": data.data_preferida,
    }
    headers = {
        "Authorization": f"Bearer {TEST_RIDE_API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(TEST_RIDE_API_URL, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        protocolo = response.json().get("protocolo", "sem-protocolo")
        return f"SUCESSO: test ride solicitado. Protocolo {protocolo}."
    except requests.Timeout:
        return "ERRO: serviço de agendamento indisponível no momento"
    except Exception as exc:
        logger.error("[TOOL] agendar_test_ride failed: %s", exc, exc_info=True)
        return "ERRO: não foi possível concluir o agendamento"
```

#### 10.6.5 Registrar no agente em `src/agent.py`

```python
from src.tools import add_lead_to_nocodb, consultar_estoque, agendar_test_ride

# ...
tools=[add_lead_to_nocodb, consultar_estoque, agendar_test_ride]
```

#### 10.6.6 Atualizar prompt em `src/prompts.py`

Regras recomendadas:

- só chamar `agendar_test_ride` quando `nome`, `telefone`, `modelo` e `data_preferida` estiverem completos;
- em caso de `ERRO:`, orientar usuário a confirmar dados e tentar novamente;
- em `SUCESSO:`, informar protocolo ao usuário.

---

### 10.7 Padrão de qualidade para ferramentas (obrigatório em PR)

Todo PR que adiciona ferramenta deve incluir:

- [ ] modelo de validação em `src/models.py`;
- [ ] função documentada e logada em `src/tools.py`;
- [ ] registro no `tools=[...]` em `src/agent.py`;
- [ ] instrução de uso no `src/prompts.py`;
- [ ] variáveis de ambiente no `.env.example` e `src/config.py`;
- [ ] atualização deste README com contrato e exemplo.

### 10.8 Anti-padrões que devem ser evitados

- tool que faz request externo sem timeout;
- tool retornando texto ambíguo (sem `SUCESSO:`/`ERRO:`);
- validação só no prompt (sem validação no Python);
- registrar tool no código, mas esquecer regra no prompt;
- capturar exceção e não logar contexto mínimo.

---

## 11) Estratégia de Expansão do Agente (Roadmap Técnico)

### Curto prazo

- separar configurações por ambiente (dev/staging/prod);
- adicionar testes automatizados para validações de modelos e ferramentas;
- criar comandos administrativos para inspeção de locks/buffers no Redis.

### Médio prazo

- implementar camada de abstração para provedores externos (NocoDB/CRM/ERP);
- métricas centralizadas (latência, erro por endpoint/ferramenta);
- fila assíncrona para tarefas longas (ex.: Celery/RQ).

### Longo prazo

- múltiplas ferramentas de negócio (estoque, preço, agenda, proposta);
- avaliação de qualidade de resposta (human-in-the-loop);
- mecanismos anti-abuso e auditoria de segurança mais robustos.

---

## 12) Troubleshooting

### Serviço sobe, mas não responde webhook

- verifique URL pública HTTPS;
- valide `INSTAGRAM_VERIFY_TOKEN`;
- confira assinatura do campo `messages` no Meta.

### Mensagens não são enviadas

- confira `INSTAGRAM_ACCESS_TOKEN` e permissões;
- inspecione logs de `HTTPStatusError` em `send_message`.

### Áudio não transcreve

- confirme `ffmpeg` disponível no container;
- verifique tamanho/duração do áudio versus limites configurados;
- teste modelos de transcrição alternativos.

### NocoDB não grava

- valide `NOCODB_API_TOKEN` e `NOCODB_TABLE_URL`;
- confira mapeamento de campos e resposta HTTP da API.

### Redis indisponível

- confirme container `redis` ativo;
- valide `REDIS_URL`;
- em falhas de Redis, partes de buffer/bloqueio podem degradar.

---

## 13) Segurança e Boas Práticas

- não versionar `.env` com segredos reais;
- usar tokens de menor privilégio possível;
- rotacionar segredos periodicamente;
- restringir acesso de rede ao serviço;
- monitorar logs de erro e comportamento anômalo.

---

## 14) Comandos Úteis

```bash
# Subir ambiente

docker compose up --build -d

# Logs em tempo real

docker compose logs -f agent

# Healthcheck

curl http://localhost:8000/health

# Derrubar ambiente

docker compose down
```

---

## 15) Licenciamento e Dependências

Principais dependências:

- agno
- fastapi
- uvicorn
- redis
- openai
- pydantic
- httpx
- requests
- python-dotenv

Consulte `requirements.txt` para a lista completa atualmente utilizada.
