import { ref } from 'vue'
import axios from 'axios'
import { CONFIG } from '../constants/config'

/**
 * 指令系统
 */
export function useCommand(humanId) {
    const showCommandInput = ref(false)
    const currentCommand = ref('')
    const isSendingCommand = ref(false)
    const commandError = ref('')
    const spaceKeyCount = ref(0)
    const spaceKeyTimer = ref(null)

    /**
     * 处理空格键（双击打开）
     */
    function handleSpaceKey() {
        spaceKeyCount.value++

        if (spaceKeyTimer.value) {
            clearTimeout(spaceKeyTimer.value)
        }

        spaceKeyTimer.value = setTimeout(() => {
            if (spaceKeyCount.value >= 2) {
                openCommandInput()
            }
            spaceKeyCount.value = 0
        }, CONFIG.SPACE_KEY_TIMEOUT)
    }

    /**
     * 打开指令输入框
     */
    function openCommandInput() {
        showCommandInput.value = true
        currentCommand.value = ''
        commandError.value = ''
    }

    /**
     * 关闭指令输入框
     */
    function closeCommandInput() {
        showCommandInput.value = false
        currentCommand.value = ''
        commandError.value = ''
    }

    /**
     * 发送指令
     */
    async function sendCommand() {
        if (!currentCommand.value.trim() || !humanId.value) {
            return
        }

        isSendingCommand.value = true
        commandError.value = ''

        const commandToSend = currentCommand.value.trim()
        closeCommandInput()

        try {
            const response = await axios.post(
                `${CONFIG.API_BASE_URL}/api/humans/${humanId.value}/command`,
                { command: commandToSend }
            )

            if (response.data.status === 'success') {
                console.log(`📡 指令已发送: ${commandToSend}`)
            }
        } catch (error) {
            console.error('发送指令失败:', error)
        } finally {
            isSendingCommand.value = false
        }
    }

    return {
        showCommandInput,
        currentCommand,
        isSendingCommand,
        commandError,
        handleSpaceKey,
        openCommandInput,
        closeCommandInput,
        sendCommand
    }
}

