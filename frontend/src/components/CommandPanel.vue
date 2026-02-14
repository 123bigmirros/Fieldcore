<template>
  <div class="command-panel">
    <div class="panel-header">
      <h3>发送命令</h3>
    </div>
    <div class="panel-content">
      <div class="form-group">
        <label for="command-input">命令：</label>
        <input
          id="command-input"
          v-model="commandState.command"
          type="text"
          placeholder="请输入命令"
          class="command-input"
          @keyup.enter="handleSend"
        />
      </div>

      <button
        @click="handleSend"
        :disabled="!commandState.canSend"
        class="send-button"
      >
        {{ commandState.isSending ? '发送中...' : '发送命令' }}
      </button>

      <div v-if="commandState.message" :class="['message', commandState.messageType]">
        {{ commandState.message }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive } from 'vue'
import { useCommand } from '../composables/useCommand'

const props = defineProps({
  humanId: {
    type: String,
    required: true
  },
  apiKey: {
    type: String,
    required: true
  }
})

const commandState = reactive(useCommand(props.humanId, props.apiKey))

async function handleSend() {
  await commandState.sendCommand()
}
</script>

<style scoped>
.command-panel {
  position: fixed;
  bottom: 20px;
  left: 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid #e1e5e9;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(10px);
  z-index: 10;
  min-width: 300px;
  max-width: 380px;
}

.panel-header {
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
  color: #2d3436;
}

.panel-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-weight: 500;
  color: #636e72;
  font-size: 0.9rem;
}

.command-input {
  padding: 8px 12px;
  border: 2px solid #e1e5e9;
  border-radius: 6px;
  font-size: 0.95rem;
  transition: border-color 0.3s ease;
}

.command-input:focus {
  outline: none;
  border-color: #74b9ff;
  box-shadow: 0 0 0 3px rgba(116, 185, 255, 0.1);
}

.send-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  margin-top: 4px;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(116, 185, 255, 0.4);
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.message {
  padding: 10px;
  border-radius: 6px;
  font-size: 0.9rem;
  border: 1px solid;
}

.message.success {
  color: #00b894;
  background: rgba(0, 184, 148, 0.1);
  border-color: rgba(0, 184, 148, 0.2);
}

.message.error {
  color: #d63031;
  background: rgba(214, 48, 49, 0.1);
  border-color: rgba(214, 48, 49, 0.2);
}

.message.info {
  color: #0984e3;
  background: rgba(9, 132, 227, 0.1);
  border-color: rgba(9, 132, 227, 0.2);
}
</style>

