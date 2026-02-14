import { ref } from 'vue'
import axios from 'axios'
import { CONFIG } from '../constants/config'

/**
 * Human authentication management
 * Flow: register -> get api_key -> create agent
 */
export function useAuth() {
    const humanId = ref(null)
    const apiKey = ref(null)
    const inputHumanId = ref('')
    const machineCount = ref(3)
    const isCreating = ref(false)
    const loginError = ref('')

    /**
     * Create Human (two-step flow)
     */
    async function createHuman() {
        if (!inputHumanId.value.trim()) {
            loginError.value = 'Human ID不能为空'
            return false
        }

        isCreating.value = true
        loginError.value = ''

        try {
            // Step 1: Register to get API Key
            const registerResp = await axios.post(`${CONFIG.API_BASE_URL}/api/v1/auth/register`, {
                agent_id: inputHumanId.value.trim()
            })
            const respData = registerResp.data.data || registerResp.data
            const key = respData.api_key
            if (!key) {
                loginError.value = '注册失败：未获取到 API Key'
                return false
            }
            apiKey.value = key

            // Step 2: Create Agent (with API Key)
            const agentResp = await axios.post(
                `${CONFIG.API_BASE_URL}/api/v1/agents`,
                {
                    agent_type: 'human',
                    agent_id: inputHumanId.value.trim(),
                    machine_count: machineCount.value
                },
                { headers: { 'Authorization': `Bearer ${key}` } }
            )

            humanId.value = inputHumanId.value.trim()
            inputHumanId.value = ''
            document.title = `OpenManus - ${humanId.value}`

            console.log(`[${humanId.value}] Human created successfully`)
            return true
        } catch (error) {
            console.error('Failed to create Human:', error)
            const errData = error.response?.data?.error
            loginError.value = (errData && errData.message) || errData || '创建失败，请重试'
            return false
        } finally {
            isCreating.value = false
        }
    }

    /**
     * Exit system
     */
    async function exitSystem() {
        if (!humanId.value) return

        try {
            await axios.delete(`${CONFIG.API_BASE_URL}/api/v1/agents/${humanId.value}`, {
                headers: { 'Authorization': `Bearer ${apiKey.value}` }
            })
            console.log(`Human ${humanId.value} deleted`)
        } catch (error) {
            console.error('Failed to delete Human:', error)
        } finally {
            humanId.value = null
            apiKey.value = null
            document.title = 'OpenManus'
        }
    }

    return {
        humanId,
        apiKey,
        inputHumanId,
        machineCount,
        isCreating,
        loginError,
        createHuman,
        exitSystem
    }
}
