<template>
  <div class="status-panel">
    <div class="status-item">
      <span class="status-label">Human ID:</span>
      <span class="status-value">{{ humanId }}</span>
    </div>
    <div class="status-item">
      <span class="status-label">机器人:</span>
      <span class="status-value">{{ machineCount }}</span>
    </div>
    <div class="status-item">
      <span class="status-label">障碍物:</span>
      <span class="status-value">{{ obstacleCount }}</span>
    </div>
    <button @click="$emit('exit')" class="exit-button">退出系统</button>
  </div>
</template>

<script setup>
defineProps({
  humanId: String,
  machineCount: Number,
  obstacleCount: Number
})

defineEmits(['exit'])
</script>

<style scoped>
.status-panel {
  position: fixed;
  top: 20px;
  right: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  z-index: 10;
}

.status-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.status-item:last-of-type {
  margin-bottom: 0;
}

.status-label {
  font-weight: 600;
  color: #636e72;
  margin-right: 10px;
}

.status-value {
  font-weight: 700;
  color: #2d3436;
  background: #f8f9fa;
  padding: 2px 8px;
  border-radius: 4px;
  min-width: 30px;
  text-align: center;
}

.exit-button {
  margin-top: 10px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #fd79a8 0%, #e84393 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  width: 100%;
}

.exit-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(232, 67, 147, 0.4);
}
</style>

