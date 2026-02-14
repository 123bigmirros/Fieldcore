<template>
  <canvas
    ref="fogCanvas"
    class="fog-canvas"
  />
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { CONFIG } from '../constants/config'

const props = defineProps({
  myMachines: Array,
  transformer: Object
})

const fogCanvas = ref(null)
let resizeObserver = null

function draw() {
  const canvas = fogCanvas.value
  if (!canvas || !props.transformer) return

  canvas.width = window.innerWidth
  canvas.height = window.innerHeight

  const ctx = canvas.getContext('2d')

  // Full-screen black overlay
  ctx.fillStyle = 'rgba(0, 0, 0, 0.85)'
  ctx.fillRect(0, 0, canvas.width, canvas.height)

  // Use destination-out to erase the visible area
  ctx.globalCompositeOperation = 'destination-out'

  for (const machine of (props.myMachines || [])) {
    const pixel = props.transformer.gridToPixel(machine.position[0], machine.position[1])
    const radius = (machine.visibility_radius || 3) * CONFIG.GRID_SIZE

    const gradient = ctx.createRadialGradient(
      pixel.x, pixel.y, radius * 0.6,
      pixel.x, pixel.y, radius
    )
    gradient.addColorStop(0, 'rgba(0, 0, 0, 1)')
    gradient.addColorStop(1, 'rgba(0, 0, 0, 0)')

    ctx.beginPath()
    ctx.arc(pixel.x, pixel.y, radius, 0, Math.PI * 2)
    ctx.fillStyle = gradient
    ctx.fill()
  }

  ctx.globalCompositeOperation = 'source-over'
}

watch(() => props.myMachines, draw, { deep: true })
watch(() => props.transformer, draw)

onMounted(() => {
  draw()
  window.addEventListener('resize', draw)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', draw)
})
</script>

<style scoped>
.fog-canvas {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  z-index: 100;
}
</style>
