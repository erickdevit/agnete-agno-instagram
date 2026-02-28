import { BaseMessage } from "@langchain/core/messages";
import { Annotation } from "@langchain/langgraph";

/**
 * Define a memória e o estado persistente do LangGraph durante uma execução.
 */
export const AgentState = Annotation.Root({
    // Histórico de mensagens da conversa inteira
    messages: Annotation<BaseMessage[]>({
        reducer: (x, y) => x.concat(y),
        default: () => [],
    }),

    // Dados do lead identificados ao longo da conversa (State Extractor)
    leadInfo: Annotation<{
        name?: string;
        cpf?: string;
        phone?: string;
        modelOfInterest?: string;
        birthDate?: string;
        hasCNH?: boolean;
        notified?: boolean; // Para evitar notificações duplicadas pro NocoDB
    }>({
        reducer: (current, update) => ({ ...current, ...update }),
        default: () => ({ notified: false }),
    }),

    // ID de quem está mandando mensagem (o remetente do instagram)
    senderId: Annotation<string>({
        reducer: (x, y) => y ?? x,
        default: () => "",
    })
});

export type GraphState = typeof AgentState.State;
