import { ref, computed } from 'vue'
import axios from 'axios'
import { CONFIG, DEFAULTS } from '../constants/config'

/**
 * World data management — fetches server-filtered data via the unified view endpoint
 */
export function useWorldData(humanId, apiKey) {
    const machines = ref([])
    const obstacles = ref([])
    const carriedResources = ref([])
    const myMachineIds = ref([])
    const refreshInterval = ref(null)

    /**
     * Refresh data (single request to unified endpoint via Agent Server proxy)
     */
    async function refreshData() {
        if (!humanId.value) return
        try {
            const headers = {}
            if (apiKey && apiKey.value) {
                headers['Authorization'] = `Bearer ${apiKey.value}`
            }
            const response = await axios.get(
                `${CONFIG.API_BASE_URL}/api/v1/world/view?human_id=${encodeURIComponent(humanId.value)}&t=${Date.now()}`,
                { headers }
            )
            const respData = response.data.data || response.data

            myMachineIds.value = respData.my_machine_ids || []

            machines.value = (respData.machines || []).map(machine => ({
                ...machine,
                visibility_radius: machine.visibility_radius || DEFAULTS.VISIBILITY_RADIUS,
                facing_direction: machine.facing_direction || DEFAULTS.FACING_DIRECTION,
                isMyMachine: myMachineIds.value.includes(machine.machine_id)
            }))

            obstacles.value = respData.obstacles || []
            carriedResources.value = respData.carried_resources || []
        } catch (error) {
            machines.value = []
            obstacles.value = []
            carriedResources.value = []
            myMachineIds.value = []
        }
    }

    function startAutoRefresh() {
        refreshData()
        refreshInterval.value = setInterval(refreshData, CONFIG.REFRESH_INTERVAL)
    }

    function stopAutoRefresh() {
        if (refreshInterval.value) {
            clearInterval(refreshInterval.value)
            refreshInterval.value = null
        }
    }

    const myMachines = computed(() => machines.value.filter(m => m.isMyMachine))

    return {
        machines,
        obstacles,
        myMachines,
        carriedResources,
        refreshData,
        startAutoRefresh,
        stopAutoRefresh
    }
}
