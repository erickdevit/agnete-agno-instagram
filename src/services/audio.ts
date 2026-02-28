import OpenAI from "openai";

/**
 * Transcreve um áudio direto do URL do Meta via OpenAI Whisper.
 * Sem dependência de ffmpeg usando streaming de buffers.
 */
export async function transcribeAudio(audioUrl: string, accessToken: string, openai: OpenAI): Promise<string | null> {
    try {
        const headers = accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined;

        // O Meta fornece URLs que as vezes exigem auth e as vezes são content publico assinado
        let response = await fetch(audioUrl, { headers });
        if (response.status === 401 || response.status === 403) {
            response = await fetch(audioUrl);
        }

        if (!response.ok) {
            console.warn(`[Audio] Failed to fetch audio meta from ${audioUrl}`);
            return null;
        }

        const arrayBuffer = await response.arrayBuffer();

        // Criamos um novo File em memória. O Whisper aceita formatos como m4a, mp3, mp4 nativamente.
        // Instagram comumente envia containers MP4/M4A.
        const file = new File([arrayBuffer], "attachment.m4a", { type: "audio/mp4" });

        const transcription = await openai.audio.transcriptions.create({
            file,
            model: "whisper-1",
        });

        return transcription.text.trim();
    } catch (err) {
        console.error("[Audio] Transcription failed:", err);
        return null;
    }
}

/**
 * Cria a síntese de voz a partir de um texto, salva no Cloudflare R2 e devolve URL pública.
 */
export async function createAudioReply(text: string, openai: OpenAI, bucket: R2Bucket, publicUrlBase: string): Promise<string | null> {
    try {
        const safeText = text.substring(0, 500); // hard limit p/ segurança

        // Gera direto em mp3 (Instagram nativamente lê MP3/AAC no iOS/Android)
        const mp3Response = await openai.audio.speech.create({
            model: "tts-1",
            voice: "alloy",
            input: safeText,
            response_format: "mp3",
        });

        const arrayBuffer = await mp3Response.arrayBuffer();
        const fileName = `${crypto.randomUUID()}.mp3`;

        // Salva o buffer binário direto no Cloudflare R2
        await bucket.put(fileName, arrayBuffer, {
            httpMetadata: { contentType: "audio/mpeg" },
        });

        const base = publicUrlBase.replace(/\/$/, "");
        return `${base}/media/audio/${fileName}`;
    } catch (err) {
        console.error("[Audio] TTS failed:", err);
        return null;
    }
}
