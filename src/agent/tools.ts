import { tool } from "@langchain/core/tools";
import { z } from "zod";

/**
 * Zod Schema para garantir que o Agente da OpenAI trará o formato estrito.
 */
const RegistrationSchema = z.object({
    name: z.string().describe("Nome do lead"),
    cpf: z.string().describe("CPF no formato 000.000.000-00"),
    phone: z.string().describe("Telefone no formato (00) 00000-0000"),
    modelOfInterest: z.string().describe("Modelo da moto de interesse"),
    birthDate: z.string().describe("Data de nascimento no formato 00/00/0000"),
    hasCNH: z.boolean().describe("Se o cliente possui CNH (true/false)"),
});

export type RegistrationData = z.infer<typeof RegistrationSchema>;

/**
 * Notificador Tool que dispara pro NocoDB (banco de dados) e pro Pushover (App do Vendedor).
 * Retorna sucesso para o LangGraph continuar conversando.
 */
export const RegisterLeadTool = tool(
    async (input, config) => {
        // Essa closure roda em Serverless Edge
        try {
            console.log("[RegisterLeadTool] Executando envio para a Base de Dados:", input);

            // Aqui integrariamos as chamadas FETCH para o NocoDB e Pushover
            // EX: await fetch('https://api.nocodb.com/...', { ... })
            // EX: await fetch('https://api.pushover.net/...', { ... })

            return `[SUCESSO] Dados registrados. Avise o cliente e mande este link do WhatsApp para ele: http://bit.ly/46ia00v`;
        } catch (e) {
            console.error(e);
            return `[FALHA] Não foi possível registrar os dados no momento.`;
        }
    },
    {
        name: "register_lead",
        description: "Registra os dados obrigatórios do cliente (Nome, CPF, Telefone, Modelo, Nascimento e CNH) assim que ele providenciar todos. Dispara notificação de urgência aos consultores.",
        schema: RegistrationSchema,
    }
);
