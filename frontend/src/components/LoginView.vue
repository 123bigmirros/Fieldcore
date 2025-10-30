<template>
  <div class="login-container">
    <div class="login-box">
      <h2>🤖 OpenManus 智能管理系统</h2>
      <div class="login-form">
        <input
          v-model="inputHumanId"
          type="text"
          placeholder="请输入Human ID"
          @keyup.enter="onSubmit"
          class="human-id-input"
        />
        <input
          v-model="machineCount"
          type="number"
          placeholder="机器人数量"
          min="1"
          max="10"
          class="machine-count-input"
        />
        <button
          @click="onSubmit"
          :disabled="!inputHumanId || isCreating"
          class="create-button"
        >
          {{ isCreating ? '创建中...' : '创建Human' }}
        </button>
        <div v-if="loginError" class="error-message">{{ loginError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  inputHumanId: String,
  machineCount: Number,
  isCreating: Boolean,
  loginError: String
})

const emit = defineEmits(['update:inputHumanId', 'update:machineCount', 'submit'])

function onSubmit() {
  emit('submit')
}
</script>

<style scoped>
.login-container {
  width: 100vw;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-box {
  background: rgba(255, 255, 255, 0.95);
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  backdrop-filter: blur(20px);
  text-align: center;
  min-width: 400px;
}

.login-box h2 {
  margin-bottom: 30px;
  color: #2d3436;
  font-size: 1.8rem;
  font-weight: 700;
}

.login-form {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.human-id-input, .machine-count-input {
  padding: 12px 16px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 1rem;
  transition: border-color 0.3s ease;
}

.human-id-input:focus, .machine-count-input:focus {
  outline: none;
  border-color: #74b9ff;
  box-shadow: 0 0 0 3px rgba(116, 185, 255, 0.1);
}

.create-button {
  padding: 12px 24px;
  background: linear-gradient(135deg, #74b9ff 0%, #0984e3 100%);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.create-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(116, 185, 255, 0.4);
}

.create-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-message {
  color: #d63031;
  background: rgba(214, 48, 49, 0.1);
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(214, 48, 49, 0.2);
  font-size: 0.9rem;
}
</style>

