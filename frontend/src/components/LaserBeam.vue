<template>
  <div class="laser-beam" :style="laserStyle"></div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  laser: Object,
  transformer: Object
})

const laserStyle = computed(() => {
  const [startGridX, startGridY] = props.laser.startPos
  const [endGridX, endGridY] = props.laser.endPos

  const startPixel = props.transformer.gridToPixel(startGridX, startGridY)
  const endPixel = props.transformer.gridToPixel(endGridX, endGridY)

  const dx = endPixel.x - startPixel.x
  const dy = endPixel.y - startPixel.y
  const length = Math.sqrt(dx * dx + dy * dy)
  const angle = Math.atan2(dy, dx) * 180 / Math.PI

  return {
    left: `${startPixel.x}px`,
    top: `${startPixel.y}px`,
    width: `${length}px`,
    height: '8px',
    transform: `rotate(${angle}deg)`,
    transformOrigin: '0 50%'
  }
})
</script>

<style scoped>
.laser-beam {
  position: absolute;
  background: linear-gradient(90deg,
    rgba(255, 50, 50, 0.9) 0%,
    rgba(255, 150, 150, 1) 20%,
    rgba(255, 200, 200, 1) 50%,
    rgba(255, 150, 150, 1) 80%,
    rgba(255, 50, 50, 0.2) 100%);
  box-shadow:
    0 0 15px rgba(255, 0, 0, 0.8),
    0 0 30px rgba(255, 0, 0, 0.6),
    inset 0 0 5px rgba(255, 255, 255, 0.3);
  border-radius: 4px;
  z-index: 5;
  animation: laser-flash 0.5s ease-out;
}

@keyframes laser-flash {
  0% {
    opacity: 0;
    transform: scaleX(0) scaleY(0.3);
    filter: brightness(2) blur(2px);
  }
  15% {
    opacity: 1;
    transform: scaleX(0.3) scaleY(1);
    filter: brightness(3) blur(1px);
  }
  30% {
    opacity: 1;
    transform: scaleX(1) scaleY(1.2);
    filter: brightness(2.5) blur(0px);
  }
  70% {
    opacity: 1;
    transform: scaleX(1) scaleY(1);
    filter: brightness(1.5) blur(0px);
  }
  100% {
    opacity: 0;
    transform: scaleX(1) scaleY(0.8);
    filter: brightness(1) blur(1px);
  }
}
</style>

