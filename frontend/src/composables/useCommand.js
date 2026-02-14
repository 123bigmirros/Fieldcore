import { ref, computed } from 'vue'
import axios from 'axios'
import { CONFIG } from '../constants/config'

/**
 * Command sending management
 */
export function useCommand(humanId, apiKey) {
    const command = ref('')
    const isSending = ref(false)
    const message = ref('')
    const messageType = ref('info') // 'info' | 'success' | 'error'

    const canSend = computed(() => {
        return command.value.trim() && !isSending.value && humanId
    })

    /**
     * Send command
     */
    async function sendCommand() {
        if (!canSend.value || !humanId) return false

        isSending.value = true
        message.value = ''
        messageType.value = 'info'

        try {
            // Use API Key auth (in Authorization header with Bearer prefix)
            const response = await axios.post(
                `${CONFIG.API_BASE_URL}/api/v1/agents/${humanId}/commands`,
                { command: command.value.trim() },
                {
                    headers: {
                        'Authorization': `Bearer ${apiKey}`
                    }
                }
            )

            if (response.data.success) {
                message.value = '命令发送成功'
                messageType.value = 'success'
                command.value = ''

                // Clear message after 3 seconds
                setTimeout(() => {
                    message.value = ''
                }, 3000)

                return true
            } else {
                const errData = response.data.error
                message.value = (errData && errData.message) || errData || '发送失败'
                messageType.value = 'error'
                return false
            }
        } catch (error) {
            console.error('Failed to send command:', error)
            const errData = error.response?.data?.error
            message.value = (errData && errData.message) || errData || '发送失败，请重试'
            messageType.value = 'error'
            return false
        } finally {
            isSending.value = false
        }
    }

    /**
     * Reset state
     */
    function reset() {
        command.value = ''
        message.value = ''
        messageType.value = 'info'
    }

    return {
        command,
        isSending,
        message,
        messageType,
        canSend,
        sendCommand,
        reset
    }
}
