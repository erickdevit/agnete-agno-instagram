import type { Env } from "../index";
import { appGraph } from "../agent/graph";
import { sendInstagramMessage } from "../services/instagram";
import { HumanMessage } from "@langchain/core/messages";

export class MessageBufferDO {
    state: DurableObjectState;
    env: Env;

    constructor(state: DurableObjectState, env: Env) {
        this.state = state;
        this.env = env;
    }

    async fetch(request: Request): Promise<Response> {
        const url = new URL(request.url);

        if (request.method === "POST" && url.pathname === "/add") {
            const data = await request.json() as { text: string; senderId: string };

            // Puxa mensagens existentes do Storage
            const messages = (await this.state.storage.get<string[]>("messages")) || [];
            messages.push(data.text);

            // Salva o buffer combinado com a nova mensagem
            await this.state.storage.put("messages", messages);
            await this.state.storage.put("senderId", data.senderId); // guarda quem é

            // Atualiza o alarme para daqui a 5 segundos (sempre afasta se houver novas msg)
            const now = Date.now();
            await this.state.storage.setAlarm(now + 5000);

            console.log(`[DO] Buffered message for ${data.senderId.slice(-6)}. Alarm set for 5s.`);
            return new Response(JSON.stringify({ status: "buffered" }), { status: 200 });
        }

        return new Response("Not found", { status: 404 });
    }

    /**
     * O Alarme é disparado apenas quando não houve chamadas ao fetch()/setAlarm() nos últimos 5 segundos.
     */
    async alarm(): Promise<void> {
        const messages = (await this.state.storage.get<string[]>("messages")) || [];
        const senderId = (await this.state.storage.get<string>("senderId"));

        if (!messages.length || !senderId) return;

        // Limpa o buffer para próximas mensagens
        await this.state.storage.delete("messages");

        // Concatena tudo com quebras de linha
        const combinedText = messages.join("\n");
        console.log(`[DO Alarm] Triggers for ${senderId.slice(-6)} with batch size ${messages.length}.`);

        try {
            // Inicia a resposta (LangGraph processa toda a bagagem e as tools)
            const initialState = {
                messages: [new HumanMessage(combinedText)]
            };

            // Executa o grafo com estado zerado ou você pode persistir esse Thread via Saver
            const result = await appGraph.invoke(initialState);

            const lastMsg = result.messages[result.messages.length - 1];
            const replyText = typeof lastMsg.content === "string" ? lastMsg.content : "Tive um problema!";

            // Responde pro Instagram
            await sendInstagramMessage(senderId, replyText, this.env.INSTAGRAM_ACCESS_TOKEN);

        } catch (e) {
            console.error(`[DO Alarm] Erro ao invocar LangGraph/IG:`, e);
        }
    }
}
