<template>
  <div id="app">
    <!-- 登录界面 -->
    <LoginView
      v-if="!auth.humanId.value"
      v-model:input-human-id="auth.inputHumanId.value"
      v-model:machine-count="auth.machineCount.value"
      :is-creating="auth.isCreating.value"
      :login-error="auth.loginError.value"
      @submit="handleLogin"
    />

    <!-- 主界面 -->
    <div v-else class="main-interface">
      <!-- 世界视图 -->
      <WorldView
        :machines="worldData.machines.value"
        :obstacles="worldData.obstacles.value"
        :active-lasers="laser.activeLasers.value"
        :transformer="viewport.transformer.value"
        :is-position-visible="viewport.isPositionVisible"
        :show-grid="keyboard.showGrid.value"
        :my-machines="worldData.myMachines.value"
        :human-id="auth.humanId.value"
      />

    </div>
  </div>
</template>

<script setup>
import { watch, onBeforeUnmount } from 'vue'
import LoginView from './components/LoginView.vue'
import WorldView from './components/WorldView.vue'

import { useAuth } from './composables/useAuth'
import { useWorldData } from './composables/useWorldData'
import { useViewport } from './composables/useViewport'
import { useLaser } from './composables/useLaser'
import { useKeyboard } from './composables/useKeyboard'

// 状态管理
const auth = useAuth()
const worldData = useWorldData(auth.humanId)
const viewport = useViewport()
const laser = useLaser(
  worldData.machines,
  viewport.addLaserVision,
  viewport.removeLaserVision
)

// 键盘控制
const keyboard = useKeyboard({
  onDebug: showDebugInfo,
  onResize: forceUpdate
})

// ============= 生命周期 =============
onBeforeUnmount(() => {
  worldData.stopAutoRefresh()
})

// ============= 事件处理 =============
async function handleLogin() {
  const success = await auth.createHuman()
  if (success) {
    worldData.startAutoRefresh()
  }
}

function forceUpdate() {
  // 强制重新渲染
}

// ============= 调试工具 =============
function showDebugInfo() {
  console.log('=== 🔍 调试信息 ===')
  console.log(`机器人数量: ${worldData.machines.value.length}`)
  console.log(`障碍物数量: ${worldData.obstacles.value.length}`)
  console.log(`当前激光视野区域: ${viewport.laserVisionAreas.value.length}`)

  const myMachines = worldData.myMachines.value
  const otherMachines = worldData.machines.value.filter(m => !m.isMyMachine)

  console.log(`\n=== 👁️ 视野系统状态 ===`)
  console.log(`我的机器人(提供视野): ${myMachines.length}个`)
  myMachines.forEach(m => {
    console.log(`  🤖 ${m.machine_id}: (${m.position[0]}, ${m.position[1]}) 视野${m.visibility_radius}格`)
  })

  console.log(`他人的机器人: ${otherMachines.length}个`)
  otherMachines.forEach(m => {
    const visible = viewport.isPositionVisible(m.position, myMachines) ? '可见' : '不可见'
    console.log(`  👻 ${m.machine_id}: (${m.position[0]}, ${m.position[1]}) ${visible}`)
  })

  console.log('\n=== 🧪 激光系统状态 ===')
  console.log(`活跃激光数量: ${laser.activeLasers.value.length}`)
  console.log(`激光视野区域: ${viewport.laserVisionAreas.value.length}`)
  console.log('===============')
}

// 监听登录状态
watch(() => auth.humanId.value, (newVal, oldVal) => {
  if (newVal && !oldVal) {
    console.log(`✅ 登录成功: ${newVal}`)
  } else if (!newVal && oldVal) {
    console.log(`👋 退出登录: ${oldVal}`)
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

#app {
  width: 100vw;
  height: 100vh;
  background: #f5f5f5;
  display: flex;
  align-items: center;
  justify-content: center;
  font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
}

.main-interface {
  width: 100vw;
  height: 100vh;
  position: relative;
  background: white;
}
</style>
