<template>
  <div v-if="show" class="command-input-overlay">
    <div class="command-input-box">
      <h3>🎯 发送指令</h3>
      <textarea
        v-model="localCommand"
        placeholder="请输入指令..."
        @keyup.enter.ctrl="$emit('send')"
        class="command-textarea"
        ref="textarea"
      ></textarea>
      <div class="command-buttons">
        <button
          @click="$emit('send')"
          :disabled="!localCommand.trim() || isSending"
          class="send-button"
        >
          {{ isSending ? '发送中...' : '发送 (Ctrl+Enter)' }}
        </button>
        <button @click="$emit('close')" class="cancel-button">取消</button>
      </div>
      <div v-if="error" class="error-message">{{ error }}</div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  show: Boolean,
  command: String,
  isSending: Boolean,
  error: String
})

const emit = defineEmits(['update:command', 'send', 'close'])

const textarea = ref(null)
const localCommand = ref(props.command)

watch(() => props.command, (val) => {
  localCommand.value = val
})

watch(localCommand, (val) => {
  emit('update:command', val)
})

watch(() => props.show, (val) => {
  if (val) {
    nextTick(() => {
      textarea.value?.focus()
    })
  }
})
</script>

<style scoped>
.command-input-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.command-input-box {
  background: white;
  border-radius: 12px;
  padding: 30px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  min-width: 500px;
  max-width: 80vw;
}

.command-input-box h3 {
  margin: 0 0 20px 0;
  color: #2d3436;
  font-size: 1.4rem;
  text-align: center;
}

.command-textarea {
  width: 100%;
  min-height: 120px;
  padding: 12px;
  border: 2px solid #e1e5e9;
  border-radius: 8px;
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
  margin-bottom: 15px;
}

.command-textarea:focus {
  outline: none;
  border-color: #74b9ff;
  box-shadow: 0 0 0 3px rgba(116, 185, 255, 0.1);
}

.command-buttons {
  display: flex;
  gap: 10px;
  justify-content: flex-end;
}

.send-button {
  padding: 10px 20px;
  background: linear-gradient(135deg, #00b894 0%, #00a085 100%);
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.send-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(0, 184, 148, 0.4);
}

.send-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.cancel-button {
  padding: 10px 20px;
  background: #636e72;
  color: white;
  border: none;
  border-radius: 6px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.cancel-button:hover {
  background: #2d3436;
  transform: translateY(-1px);
}

.error-message {
  color: #d63031;
  background: rgba(214, 48, 49, 0.1);
  padding: 10px;
  border-radius: 6px;
  border: 1px solid rgba(214, 48, 49, 0.2);
  font-size: 0.9rem;
  margin-top: 10px;
}
</style>

