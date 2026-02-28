const INTERACTION_LOCK_PREFIX = "user_interaction_lock:";
const INTERACTION_LOCK_TTL = 300; // 5 minutos de bloqueio

export class KVBlocker {
    constructor(private kv: KVNamespace) { }

    /**
     * Marca que o usuário interagiu. Se for a primeira interação recente, trava por 5 minutos.
     */
    async markUserInteraction(senderId: string): Promise<void> {
        const key = `${INTERACTION_LOCK_PREFIX}${senderId}`;
        const exists = await this.kv.get(key);

        if (!exists) {
            await this.kv.put(key, "locked", { expirationTtl: INTERACTION_LOCK_TTL });
            console.log(`[USER] First interaction from ${senderId.slice(-6)} - Agent blocked for 5 min`);
        } else {
            console.log(`[USER] Additional interaction from ${senderId.slice(-6)} - Block continues`);
        }
    }

    /**
     * Checa se o usuário atual está bloqueado.
     */
    async isBlocked(senderId: string): Promise<boolean> {
        const key = `${INTERACTION_LOCK_PREFIX}${senderId}`;
        const val = await this.kv.get(key);
        return val !== null;
    }

    /**
     * Força o desbloqueio prematuro de um usuário.
     */
    async unblock(senderId: string): Promise<void> {
        const key = `${INTERACTION_LOCK_PREFIX}${senderId}`;
        await this.kv.delete(key);
        console.log(`[UNBLOCK] Agent unblocked manually for ${senderId.slice(-6)}`);
    }
}
