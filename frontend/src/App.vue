<template>
  <div id="app">
    <div class="header">
      <h1>OpenManus 世界管理器</h1>
      <div class="status-indicator">
        <span :class="['status-dot', connectionStatus]"></span>
        {{ connectionStatusText }}
      </div>
      <div class="controls">
        <button @click="refreshData" :disabled="loading">刷新数据</button>
        <button @click="startAutoRefresh" v-if="!autoRefresh">自动刷新</button>
        <button @click="stopAutoRefresh" v-if="autoRefresh">停止自动刷新</button>
        <button @click="resetWorld" :disabled="loading">重置世界</button>
      </div>
    </div>

    <div class="main-content">
      <div class="visualization">
        <div class="world-container">
          <div class="world-info">
            <h3>世界状态</h3>
            <p>机器数量: {{ machines.length }}</p>
            <p>连接状态: {{ connectionStatusText }}</p>
          </div>
          <div class="world-grid">
            <div
              v-for="machine in machines"
              :key="machine.machine_id"
              class="machine"
              :style="getMachineStyle(machine)"
              :title="getMachineTooltip(machine)"
              @click="selectMachine(machine)"
            >
              <div class="machine-id">{{ machine.machine_id }}</div>
              <div class="machine-life">❤️ {{ machine.life_value }}</div>
              <div class="machine-status" :class="machine.status">{{ machine.status }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="info-panel">
        <div class="panel-section">
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
              :class="{ selected: selectedMachine && selectedMachine.machine_id === machine.machine_id }"
              @click="selectMachine(machine)"
            >
              <h4>{{ machine.machine_id }}</h4>
              <p>位置: {{ formatPosition(machine.position) }}</p>
              <p>类型: {{ machine.machine_type }}</p>
              <p>生命值: {{ machine.life_value }}</p>
              <p>状态: <span :class="machine.status">{{ machine.status }}</span></p>
              <p v-if="machine.last_action">最后动作: {{ machine.last_action }}</p>
            </div>
          </div>
        </div>

        <div class="panel-section" v-if="selectedMachine">
          <h3>选中机器详情</h3>
          <div class="machine-detail">
            <h4>{{ selectedMachine.machine_id }}</h4>
            <p><strong>位置:</strong> {{ formatPosition(selectedMachine.position) }}</p>
            <p><strong>类型:</strong> {{ selectedMachine.machine_type }}</p>
            <p><strong>生命值:</strong> {{ selectedMachine.life_value }}</p>
            <p><strong>状态:</strong> <span :class="selectedMachine.status">{{ selectedMachine.status }}</span></p>
            <p v-if="selectedMachine.last_action"><strong>最后动作:</strong> {{ selectedMachine.last_action }}</p>
          </div>
        </div>

        <div class="panel-section">
          <h3>系统信息</h3>
          <div class="system-info">
            <p><strong>API地址:</strong> http://localhost:8003</p>
            <p><strong>最后更新:</strong> {{ lastUpdateTime }}</p>
            <p><strong>自动刷新:</strong> {{ autoRefresh ? '开启' : '关闭' }}</p>
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
      refreshInterval: null,
      connectionStatus: 'disconnected',
      selectedMachine: null,
      lastUpdateTime: '未更新'
    }
  },
  computed: {
    connectionStatusText() {
      const statusMap = {
        connected: '已连接',
        connecting: '连接中',
        disconnected: '未连接',
        error: '连接错误'
      }
      return statusMap[this.connectionStatus] || '未知状态'
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
      this.connectionStatus = 'connecting'

      try {
        // 连接到MCP服务器的HTTP API
        const response = await axios.get('/mcp/machines')

        let machines = response.data

        // 处理字符串化的JSON数据
        if (typeof machines === 'string') {
          try {
            machines = JSON.parse(machines)
          } catch (e) {
            console.error('JSON解析失败:', e)
            machines = {}
          }
        }

        // 兼容对象和数组
        if (machines && !Array.isArray(machines) && typeof machines === 'object') {
          machines = Object.values(machines)
        }

        if (machines && Array.isArray(machines)) {
          this.machines = machines
          this.connectionStatus = 'connected'
          this.lastUpdateTime = new Date().toLocaleTimeString()
        } else {
          console.error('无效的数据格式:', response.data)
          this.connectionStatus = 'error'
        }
      } catch (error) {
        console.error('获取机器数据失败:', error)
        this.connectionStatus = 'error'
        this.machines = []
      } finally {
        this.loading = false
      }
    },

    async resetWorld() {
      try {
        await axios.post('http://localhost:8003/mcp/reset')
        this.refreshData()
      } catch (error) {
        console.error('重置世界失败:', error)
      }
    },

    startAutoRefresh() {
      this.autoRefresh = true
      this.refreshInterval = setInterval(() => {
        this.refreshData()
      }, 2000) // 每2秒刷新一次
    },

    stopAutoRefresh() {
      this.autoRefresh = false
      if (this.refreshInterval) {
        clearInterval(this.refreshInterval)
        this.refreshInterval = null
      }
    },

    selectMachine(machine) {
      this.selectedMachine = machine
    },

    getMachineStyle(machine) {
      const [x, y, z] = machine.position
      const scale = 3
      const centerX = 50
      const centerY = 20

      return {
        left: `${centerX + x * scale}%`,
        top: `${centerY + y * scale}%`,
        transform: `translate(-50%, -50%)`
      }
    },

    getMachineTooltip(machine) {
      return `${machine.machine_id}\n位置: ${this.formatPosition(machine.position)}\n生命值: ${machine.life_value}\n状态: ${machine.status}`
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
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: #f5f5f5;
}

.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.header h1 {
  font-size: 1.8rem;
  font-weight: 600;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.9rem;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  display: inline-block;
}

.status-dot.connected {
  background: #27ae60;
  box-shadow: 0 0 5px #27ae60;
}

.status-dot.connecting {
  background: #f39c12;
  animation: pulse 1s infinite;
}

.status-dot.disconnected {
  background: #95a5a6;
}

.status-dot.error {
  background: #e74c3c;
}

@keyframes pulse {
  0% { opacity: 1; }
  50% { opacity: 0.5; }
  100% { opacity: 1; }
}

.controls {
  display: flex;
  gap: 0.5rem;
}

.controls button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  background: rgba(255,255,255,0.2);
  color: white;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s ease;
}

.controls button:hover {
  background: rgba(255,255,255,0.3);
  transform: translateY(-1px);
}

.controls button:disabled {
  background: rgba(255,255,255,0.1);
  cursor: not-allowed;
  transform: none;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
  gap: 1rem;
  padding: 1rem;
}

.visualization {
  flex: 2;
  background: white;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  overflow: hidden;
}

.world-container {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  flex-direction: column;
}

.world-info {
  padding: 1rem;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.world-info h3 {
  color: #495057;
  margin-bottom: 0.5rem;
}

.world-info p {
  margin: 0.25rem 0;
  color: #6c757d;
  font-size: 0.9rem;
}

.world-grid {
  flex: 1;
  position: relative;
  background: linear-gradient(45deg, #f8f9fa 25%, transparent 25%),
              linear-gradient(-45deg, #f8f9fa 25%, transparent 25%),
              linear-gradient(45deg, transparent 75%, #f8f9fa 75%),
              linear-gradient(-45deg, transparent 75%, #f8f9fa 75%);
  background-size: 20px 20px;
  background-position: 0 0, 0 10px, 10px -10px, -10px 0px;
}

.machine {
  position: absolute;
  width: 70px;
  height: 70px;
  background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
  border: 3px solid #fff;
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
  box-shadow: 0 4px 15px rgba(0,0,0,0.2);
}

.machine:hover {
  transform: translate(-50%, -50%) scale(1.15);
  box-shadow: 0 6px 20px rgba(0,0,0,0.3);
}

.machine.selected {
  border-color: #f39c12;
  box-shadow: 0 0 0 3px rgba(243, 156, 18, 0.3);
}

.machine-id {
  font-size: 0.7rem;
  line-height: 1;
  text-align: center;
}

.machine-life {
  font-size: 0.6rem;
  margin-top: 2px;
}

.machine-status {
  font-size: 0.5rem;
  margin-top: 2px;
  padding: 1px 4px;
  border-radius: 3px;
  background: rgba(255,255,255,0.2);
}

.machine-status.active {
  background: rgba(39, 174, 96, 0.8);
}

.machine-status.inactive {
  background: rgba(149, 165, 166, 0.8);
}

.info-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
}

.panel-section {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.panel-section h3 {
  color: #2c3e50;
  margin-bottom: 1rem;
  font-size: 1.2rem;
  font-weight: 600;
}

.loading, .no-machines {
  text-align: center;
  color: #7f8c8d;
  padding: 2rem;
  font-style: italic;
}

.machine-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.machine-item {
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  background: #f8f9fa;
  cursor: pointer;
  transition: all 0.3s ease;
}

.machine-item:hover {
  background: #e9ecef;
  transform: translateX(5px);
}

.machine-item.selected {
  background: #fff3cd;
  border-color: #f39c12;
}

.machine-item h4 {
  color: #e74c3c;
  margin-bottom: 0.5rem;
  font-size: 1rem;
}

.machine-item p {
  margin: 0.25rem 0;
  font-size: 0.85rem;
  color: #495057;
}

.machine-item .active {
  color: #27ae60;
  font-weight: 600;
}

.machine-item .inactive {
  color: #95a5a6;
}

.machine-detail {
  background: #f8f9fa;
  padding: 1rem;
  border-radius: 8px;
  border: 1px solid #e9ecef;
}

.machine-detail h4 {
  color: #e74c3c;
  margin-bottom: 0.75rem;
}

.machine-detail p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.system-info p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
  color: #495057;
}

.system-info strong {
  color: #2c3e50;
}
</style>
