import { ref } from 'vue'
import axios from 'axios'
import { CONFIG } from '../constants/config'

/**
 * Human 认证管理
 */
export function useAuth() {
    const humanId = ref(null)
    const inputHumanId = ref('')
    const machineCount = ref(3)
    const isCreating = ref(false)
    const loginError = ref('')

    /**
     * 创建 Human
     */
    async function createHuman() {
        if (!inputHumanId.value.trim()) {
            loginError.value = 'Human ID不能为空'
            return false
        }

        isCreating.value = true
        loginError.value = ''

        try {
            const response = await axios.post(`${CONFIG.API_BASE_URL}/api/humans`, {
                human_id: inputHumanId.value.trim(),
                machine_count: machineCount.value
            })

            if (response.data.status === 'success') {
                humanId.value = inputHumanId.value.trim()
                inputHumanId.value = ''
                document.title = `OpenManus - ${humanId.value}`

                console.log(`✅ [${humanId.value}] Human创建成功，机器人数量: ${response.data.actual_count}/${response.data.requested_count}`)
                return true
            }
            return false
        } catch (error) {
            console.error('创建Human失败:', error)
            loginError.value = error.response?.data?.error || '创建失败，请重试'
            return false
        } finally {
            isCreating.value = false
        }
    }

    /**
     * 退出系统
     */
    async function exitSystem() {
        if (!humanId.value) return

        try {
            await axios.delete(`${CONFIG.API_BASE_URL}/api/humans/${humanId.value}`)
            console.log(`✅ Human ${humanId.value} 已删除`)
        } catch (error) {
            console.error('删除Human失败:', error)
        } finally {
            humanId.value = null
            document.title = 'OpenManus'
        }
    }

    return {
        humanId,
        inputHumanId,
        machineCount,
        isCreating,
        loginError,
        createHuman,
        exitSystem
    }
}

