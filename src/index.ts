import { Hono } from "hono";

export type Env = {
    INSTAGRAM_VERIFY_TOKEN: string;
    INSTAGRAM_ACCESS_TOKEN: string;
    OPENAI_API_KEY: string;
    PUBLIC_BASE_URL: string;
    BLOCKS_KV: KVNamespace;
    AUDIO_BUCKET: R2Bucket;
    MESSAGE_BUFFER_DO: DurableObjectNamespace;
};

const app = new Hono<{ Bindings: Env }>();

app.get("/health", (c) => c.json({ status: "ok" }));

// Meta Webhook Verification
app.get("/webhook", (c) => {
    const mode = c.req.query("hub.mode");
    const challenge = c.req.query("hub.challenge");
    const token = c.req.query("hub.verify_token");

    if (mode === "subscribe" && token === c.env.INSTAGRAM_VERIFY_TOKEN) {
        return c.text(challenge || "");
    }

    return c.text("Verification token mismatch", 403);
});

import { KVBlocker } from "./services/kv_blocker";

// Ingestão: POST /webhook 
// Recebe mensagens, ignora "echos", trava no KV e joga o texto pro DO Alarmado de 5s.
app.post("/webhook", async (c) => {
    const body = await c.req.json() as any;
    const entries = body.entry || [];

    const kvBlocker = new KVBlocker(c.env.BLOCKS_KV);

    for (const entry of entries) {
        const messages = entry.messaging || [];

        for (const msg of messages) {
            const senderId = msg.sender?.id;
            const text = msg.message?.text;
            const isEcho = msg.message?.is_echo;
            const attachments = msg.message?.attachments || [];

            // Captura URL se for áudio (para transcrever)
            const audioUrl = attachments.find((a: any) => a.type === "audio")?.payload?.url;

            if (!senderId) continue;

            if (isEcho) {
                // Se a loja humana interagiu, dar Lock de 5 min via KV para mutar o agente.
                if (text) await kvBlocker.markUserInteraction(senderId);
                continue;
            }

            // Se o usuário dono do chat interagiu: checar se está em Lock
            if (await kvBlocker.isBlocked(senderId)) {
                console.log(`Ignorando mensagem de ${senderId.slice(-6)}, lock humano ativo.`);
                continue;
            }

            // Pegamos o identificador único do Durable Object por SenderId e mandamos pra ele guardar/esperar
            const doId = c.env.MESSAGE_BUFFER_DO.idFromName(senderId);
            const doStub = c.env.MESSAGE_BUFFER_DO.get(doId);

            // Tratamento Mínimo: Se enviar áudio mandamos o URL. Senão, vai texto.
            // O DO é blindado por HTTP subrequests locais da infra da CF.
            if (text) {
                c.executionCtx.waitUntil(
                    doStub.fetch("http://do/add", {
                        method: "POST",
                        body: JSON.stringify({ senderId, text })
                    })
                );
            } else if (audioUrl) {
                // Se for áudio, dizemos pro DO processar como transcrição num pipeline futuro.
                // Aqui, por simplificação, poderíamos transcrever direto e passar o text para o DO,
                // mas vamos mandar o URL e indicar ao DO.
                c.executionCtx.waitUntil(
                    doStub.fetch("http://do/add", {
                        method: "POST",
                        body: JSON.stringify({ senderId, isAudioUrl: true, text: audioUrl })
                    })
                );
            }
        }
    }

    return c.text("RECEIVED", 200);
});

export { MessageBufferDO } from "./durable_objects/message_buffer";
export default app;
