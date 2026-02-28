import { ChatOpenAI } from "@langchain/openai";
import { SystemMessage, HumanMessage, AIMessage, ToolMessage } from "@langchain/core/messages";
import { StateGraph, END, START } from "@langchain/langgraph";
import { AgentState, GraphState } from "./state";
import { SYSTEM_PROMPT } from "./prompts";
import { RegisterLeadTool } from "./tools";

export function getAppGraph(apiKey: string) {
    // Configura o Agente que vai possuir a Tool incorporada
    const llm = new ChatOpenAI({
        openAIApiKey: apiKey,
        modelName: "gpt-4o-mini", // ou gpt-4o de preferir mais inteligência
        temperature: 0.1, // temperatura baixa pra script comercial seguro
    }).bindTools([RegisterLeadTool]);

    /**
     * Nó core: Chama a Inteligência Artificial e alimenta o estado com a resposta (Texto ou Pedido de Tool).
     */
    async function callModel(state: GraphState) {
        const systemMsg = new SystemMessage(SYSTEM_PROMPT);
        // O Estado carrega o histórico completo de dezenas de mensagens
        const response = await llm.invoke([systemMsg, ...state.messages]);
        return { messages: [response] };
    }

    /**
     * Edge de Condição: Decide se o nó de ferramenta precisa ser chamado, 
     * ou se finalizamos o grafo (END) respondendo pro usuário.
     */
    function shouldContinue(state: GraphState): "tools" | typeof END {
        const lastMessage = state.messages[state.messages.length - 1];

        if (lastMessage instanceof AIMessage && lastMessage.tool_calls?.length) {
            return "tools";
        }
        return END;
    }

    /**
     * Nó de Tool: Se a IA escolheu rodar `register_lead`, efetuaremos a extração.
     * Após rodar a função, colocamos o retorno no array de mensagens para o Agente entender.
     */
    async function runTools(state: GraphState) {
        const lastMessage = state.messages[state.messages.length - 1] as AIMessage;
        const toolResults = [];

        for (const toolCall of lastMessage.tool_calls || []) {
            if (toolCall.name === "register_lead") {
                const result = await RegisterLeadTool.invoke(toolCall.args as any);
                toolResults.push(
                    new ToolMessage({
                        content: result as string,
                        tool_call_id: toolCall.id ?? "",
                        name: toolCall.name,
                    })
                );

                // Alimentamos a variável global do Lead no Estado pra não repetir a chamada
                state.leadInfo = { ...toolCall.args, notified: true };
            }
        }

        return {
            messages: toolResults,
            leadInfo: state.leadInfo
        };
    }

    // ========================================== //
    // Compilação Real do LangGraph Workflow      //
    // ========================================== //
    const workflow = new StateGraph(AgentState)
        .addNode("agent", callModel)
        .addNode("tools", runTools)
        // Padrão ReAct Tool Flow: START > Agente > (Precisa de tool? Tool : END) > Volta pro Agente > END
        .addEdge(START, "agent")
        .addConditionalEdges("agent", shouldContinue)
        .addEdge("tools", "agent");

    return workflow.compile();
}
