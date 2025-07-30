<template>
  <div id="app">
    <div class="header">
      <h1>OpenManus Machine Movement</h1>
      <div class="controls">
        <button @click="refreshData" :disabled="loading">刷新数据</button>
        <button @click="startAutoRefresh" v-if="!autoRefresh">自动刷新</button>
        <button @click="stopAutoRefresh" v-if="autoRefresh">停止自动刷新</button>
      </div>
    </div>

    <div class="main-content">
      <div class="visualization">
        <div class="world-container">
          <div class="world-grid">
            <div
              v-for="machine in machines"
              :key="machine.machine_id"
              class="machine"
              :style="getMachineStyle(machine)"
              :title="getMachineTooltip(machine)"
            >
              <div class="machine-id">{{ machine.machine_id }}</div>
              <div class="machine-life">❤️ {{ machine.life_value }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="info-panel">
        <h3>机器信息</h3>
        <div v-if="loading" class="loading">加载中...</div>
        <div v-else-if="machines.length === 0" class="no-machines">
          暂无机器
        </div>
        <div v-else class="machine-list">
          <div
            v-for="machine in machines"
            :key="machine.machine_id"
            class="machine-item"
          >
            <h4>{{ machine.machine_id }}</h4>
            <p>位置: {{ formatPosition(machine.position) }}</p>
            <p>类型: {{ machine.machine_type }}</p>
            <p>生命值: {{ machine.life_value }}</p>
            <p>状态: {{ machine.status }}</p>
            <p v-if="machine.last_action">最后动作: {{ machine.last_action }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'App',
  data() {
    return {
      machines: [],
      loading: false,
      autoRefresh: false,
      refreshInterval: null
    }
  },
  mounted() {
    this.refreshData()
  },
  beforeUnmount() {
    this.stopAutoRefresh()
  },
  methods: {
    async refreshData() {
      this.loading = true
      try {
        const response = await axios.get('/api/machines')
        // axios已经自动解析了JSON，不需要再次parse
        this.machines = Object.values(response.data)
      } catch (error) {
        console.error('获取机器数据失败:', error)
      } finally {
        this.loading = false
      }
    },
    startAutoRefresh() {
      this.autoRefresh = true
      this.refreshInterval = setInterval(() => {
        this.refreshData()
      }, 1000)
    },
    stopAutoRefresh() {
      this.autoRefresh = false
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
    },
    getMachineStyle(machine) {
      const [x, y, z] = machine.position
      // 将3D坐标映射到2D显示
      const scale = 2
      const centerX = 50
      const centerY = 50

      return {
        left: `${centerX + x * scale}%`,
        top: `${centerY - z * scale}%`,
        transform: `translate(-50%, -50%) scale(${1 + y * 0.1})`
      }
    },
    getMachineTooltip(machine) {
      return `${machine.machine_id}\n位置: ${this.formatPosition(machine.position)}\n生命值: ${machine.life_value}`
    },
    formatPosition(position) {
      return `(${position.join(', ')})`
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  font-family: Arial, sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  background: #2c3e50;
  color: white;
  padding: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header h1 {
  font-size: 1.5rem;
}

.controls button {
  margin-left: 0.5rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 4px;
  background: #3498db;
  color: white;
  cursor: pointer;
}

.controls button:hover {
  background: #2980b9;
}

.controls button:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.visualization {
  flex: 2;
  padding: 1rem;
  background: #ecf0f1;
}

.world-container {
  width: 100%;
  height: 100%;
  position: relative;
  background: #fff;
  border: 2px solid #bdc3c7;
  border-radius: 8px;
  overflow: hidden;
}

.world-grid {
  width: 100%;
  height: 100%;
  position: relative;
}

.machine {
  position: absolute;
  width: 60px;
  height: 60px;
  background: #e74c3c;
  border: 2px solid #c0392b;
  border-radius: 50%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 0.8rem;
  font-weight: bold;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0,0,0,0.2);
}

.machine:hover {
  transform: translate(-50%, -50%) scale(1.1);
  box-shadow: 0 4px 8px rgba(0,0,0,0.3);
}

.machine-id {
  font-size: 0.7rem;
  line-height: 1;
}

.machine-life {
  font-size: 0.6rem;
  margin-top: 2px;
}

.info-panel {
  flex: 1;
  padding: 1rem;
  background: #f8f9fa;
  overflow-y: auto;
}

.info-panel h3 {
  margin-bottom: 1rem;
  color: #2c3e50;
}

.loading, .no-machines {
  text-align: center;
  color: #7f8c8d;
  padding: 2rem;
}

.machine-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.machine-item {
  background: white;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #ddd;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

.machine-item h4 {
  color: #e74c3c;
  margin-bottom: 0.5rem;
}

.machine-item p {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: #2c3e50;
}
</style>
