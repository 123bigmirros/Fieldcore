<template>
  <div id="app">
    <!-- Login view -->
    <LoginView
      v-if="!auth.humanId.value"
      v-model:input-human-id="auth.inputHumanId.value"
      v-model:machine-count="auth.machineCount.value"
      :is-creating="auth.isCreating.value"
      :login-error="auth.loginError.value"
      @submit="handleLogin"
    />

    <!-- Main interface -->
    <div v-else class="main-interface">
      <!-- World view -->
      <WorldView
        :machines="worldData.machines.value"
        :obstacles="worldData.obstacles.value"
        :carried-resources="worldData.carriedResources.value"
        :active-lasers="laser.activeLasers.value"
        :transformer="viewport.transformer.value"
        :show-grid="keyboard.showGrid.value"
        :my-machines="worldData.myMachines.value"
        :human-id="auth.humanId.value"
        :api-key="auth.apiKey.value"
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

// State management
const auth = useAuth()
const worldData = useWorldData(auth.humanId, auth.apiKey)
const viewport = useViewport()
const laser = useLaser(
  worldData.machines,
  viewport.addLaserVision,
  viewport.removeLaserVision
)

// Keyboard controls
const keyboard = useKeyboard({
  onDebug: showDebugInfo,
  onResize: forceUpdate
})

// ============= Lifecycle =============
onBeforeUnmount(() => {
  worldData.stopAutoRefresh()
})

// ============= Event handlers =============
async function handleLogin() {
  const success = await auth.createHuman()
  if (success) {
    worldData.startAutoRefresh()
  }
}

function forceUpdate() {
  // Force re-render
}

// ============= Debug tools =============
function showDebugInfo() {
  console.log('=== Debug Info ===')
  console.log(`Machines: ${worldData.machines.value.length}`)
  console.log(`Obstacles: ${worldData.obstacles.value.length}`)
  console.log(`Laser vision areas: ${viewport.laserVisionAreas.value.length}`)

  const myMachines = worldData.myMachines.value
  const otherMachines = worldData.machines.value.filter(m => !m.isMyMachine)

  console.log(`\n=== Vision System ===`)
  console.log(`My machines (provide vision): ${myMachines.length}`)
  myMachines.forEach(m => {
    console.log(`  ${m.machine_id}: (${m.position[0]}, ${m.position[1]}) vision ${m.visibility_radius} cells`)
  })

  console.log(`Other machines: ${otherMachines.length}`)
  otherMachines.forEach(m => {
    const visible = viewport.isPositionVisible(m.position, myMachines) ? 'visible' : 'hidden'
    console.log(`  ${m.machine_id}: (${m.position[0]}, ${m.position[1]}) ${visible}`)
  })

  console.log('\n=== Laser System ===')
  console.log(`Active lasers: ${laser.activeLasers.value.length}`)
  console.log(`Laser vision areas: ${viewport.laserVisionAreas.value.length}`)
  console.log('===============')
}

// Watch login state
watch(() => auth.humanId.value, (newVal, oldVal) => {
  if (newVal && !oldVal) {
    console.log(`Logged in: ${newVal}`)
  } else if (!newVal && oldVal) {
    console.log(`Logged out: ${oldVal}`)
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
