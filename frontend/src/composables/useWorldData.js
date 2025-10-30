import { ref, computed } from 'vue'
import axios from 'axios'
import { parseApiData } from '../utils/dataParser'
import { CONFIG, DEFAULTS } from '../constants/config'

/**
 * 世界数据管理（机器人和障碍物）
 */
export function useWorldData(humanId) {
    const machines = ref([])
    const obstacles = ref([])
    const refreshInterval = ref(null)

    /**
     * 获取机器人数据
     */
    async function fetchMachines() {
        try {
            const response = await axios.get(`${CONFIG.MCP_BASE_URL}/machines?t=${Date.now()}`)
            const parsed = parseApiData(response.data)

            if (parsed) {
                machines.value = parsed.map(machine => ({
                    ...machine,
                    visibility_radius: machine.visibility_radius || DEFAULTS.VISIBILITY_RADIUS,
                    facing_direction: machine.facing_direction || DEFAULTS.FACING_DIRECTION,
                    isMyMachine: machine.owner === humanId.value
                }))

                const myCount = machines.value.filter(m => m.isMyMachine).length
                const othersCount = machines.value.length - myCount
                console.log(`👤 [${humanId.value}] 我的${myCount}个 + 他人${othersCount}个 = 总计${machines.value.length}个`)
            }
        } catch (error) {
            machines.value = []
        }
    }

    /**
     * 获取障碍物数据
     */
    async function fetchObstacles() {
        try {
            const response = await axios.get(`${CONFIG.MCP_BASE_URL}/obstacles`)
            const parsed = parseApiData(response.data)
            if (parsed) obstacles.value = parsed
        } catch (error) {
            obstacles.value = []
        }
    }

    /**
     * 刷新数据
     */
    async function refreshData() {
        if (!humanId.value) return
        await Promise.all([fetchMachines(), fetchObstacles()])
    }

    /**
     * 开始自动刷新
     */
    function startAutoRefresh() {
        refreshData()
        refreshInterval.value = setInterval(refreshData, CONFIG.REFRESH_INTERVAL)
    }

    /**
     * 停止自动刷新
     */
    function stopAutoRefresh() {
        if (refreshInterval.value) {
            clearInterval(refreshInterval.value)
            refreshInterval.value = null
        }
    }

    // 计算属性：我的机器人
    const myMachines = computed(() => machines.value.filter(m => m.isMyMachine))

    return {
        machines,
        obstacles,
        myMachines,
        refreshData,
        startAutoRefresh,
        stopAutoRefresh
    }
}

