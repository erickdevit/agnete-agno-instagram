const GRAPH_INSTAGRAM_BASE_URL = "https://graph.instagram.com";
const INSTAGRAM_API_VERSION = "v22.0"; // Ou a versão atualmente utilizada pelo app

function textMessagesUrl(): string {
    return `${GRAPH_INSTAGRAM_BASE_URL}/${INSTAGRAM_API_VERSION}/me/messages`;
}

/**
 * Envia uma mensagem de texto simples pelo Meta Graph API.
 */
export async function sendInstagramMessage(recipientId: string, text: string, token: string): Promise<boolean> {
    const url = textMessagesUrl();
    const safeText = text.substring(0, 1000); // hard limit Meta

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                recipient: { id: recipientId },
                message: { text: safeText }
            })
        });

        if (!res.ok) {
            const errorText = await res.text();
            console.error(`[IG API] Falha ao enviar texto: HTTP ${res.status}`, errorText);
            return false;
        }

        console.log(`[IG API] Enviada para ${recipientId.slice(-6)} com sucesso.`);
        return true;
    } catch (error) {
        console.error(`[IG API] Exceção de rede:`, error);
        return false;
    }
}

/**
 * Envia anexo de áudio hospedado no R2 publicamente.
 */
export async function sendInstagramAudio(recipientId: string, audioUrl: string, token: string): Promise<boolean> {
    const url = textMessagesUrl();

    try {
        const res = await fetch(url, {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${token}`,
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                recipient: { id: recipientId },
                message: {
                    attachment: {
                        type: "audio",
                        payload: { url: audioUrl, is_reusable: false }
                    }
                }
            })
        });

        if (!res.ok) {
            const errorText = await res.text();
            console.error(`[IG API] Falha ao anexar áudio: HTTP ${res.status}`, errorText);
            return false;
        }

        console.log(`[IG API] Áudio enviado com sucesso para ${recipientId.slice(-6)}`);
        return true;
    } catch (error) {
        console.error(`[IG API] Exceção de rede ao enviar áudio:`, error);
        return false;
    }
}
