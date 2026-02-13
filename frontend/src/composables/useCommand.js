import { ref, computed } from 'vue'
import axios from 'axios'
import { CONFIG } from '../constants/config'

/**
 * 命令发送管理
 */
export function useCommand(humanId) {
    const command = ref('')
    const isSending = ref(false)
    const message = ref('')
    const messageType = ref('info') // 'info' | 'success' | 'error'

    const canSend = computed(() => {
        return command.value.trim() && !isSending.value && humanId
    })

    /**
     * 发送命令
     */
    async function sendCommand() {
        if (!canSend.value || !humanId) return false

        isSending.value = true
        message.value = ''
        messageType.value = 'info'

        try {
            // 使用 humanId 作为 API key（放在 Authorization header）
            const response = await axios.post(
                `${CONFIG.API_BASE_URL}/api/agent/${humanId}/command`,
                { command: command.value.trim() },
                {
                    headers: {
                        'Authorization': humanId
                    }
                }
            )

            if (response.data.success) {
                message.value = '命令发送成功'
                messageType.value = 'success'
                command.value = ''

                // 3秒后清除消息
                setTimeout(() => {
                    message.value = ''
                }, 3000)

                return true
            } else {
                message.value = response.data.error || '发送失败'
                messageType.value = 'error'
                return false
            }
        } catch (error) {
            console.error('发送命令失败:', error)
            message.value = error.response?.data?.error || '发送失败，请重试'
            messageType.value = 'error'
            return false
        } finally {
            isSending.value = false
        }
    }

    /**
     * 重置状态
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

