<template>
  <div
    :class="['game-object', type]"
    :style="objectStyle"
    :title="object[idKey]"
  >
    <template v-if="type === 'machine'">
      <div class="machine-front" :style="frontStyle"></div>
      <div class="machine-id">{{ getMachineDisplayName(object.machine_id) }}</div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { CONFIG, COLORS } from '../constants/config'
import { DIRECTION_STYLES } from '../utils/coordinateTransform'

const props = defineProps({
  object: Object,
  transformer: Object,
  type: String  // 'machine' or 'obstacle'
})

const idKey = computed(() => props.type === 'machine' ? 'machine_id' : 'obstacle_id')

const objectStyle = computed(() => {
  const [x, y] = props.object.position
  const pixel = props.transformer.gridToPixel(x, y)
  const size = (props.object.size || 1.0) * CONFIG.GRID_SIZE

  const baseStyle = {
    left: `${pixel.x}px`,
    top: `${pixel.y}px`,
    width: `${size}px`,
    height: `${size}px`,
    transform: 'translate(-50%, -50%)'
  }

  if (props.type === 'machine') {
    return {
      ...baseStyle,
      '--machine-color': props.object.isMyMachine ? COLORS.MY_MACHINE : COLORS.OTHER_MACHINE,
      opacity: props.object.isMyMachine ? 1.0 : 0.7
    }
  }

  return baseStyle
})

const frontStyle = computed(() => {
  if (props.type !== 'machine') return {}

  const [dx, dy] = props.object.facing_direction || [1, 0]
  const direction = props.transformer.getFacingDirection(dx, dy)
  return DIRECTION_STYLES[direction] || DIRECTION_STYLES.right
})

function getMachineDisplayName(machineId) {
  const match = machineId.match(/(\d+)/)
  return match ? match[1] : machineId
}
</script>

<style scoped>
.game-object {
  position: absolute;
  transition: all 0.4s cubic-bezier(0.25, 0.8, 0.25, 1);
  cursor: pointer;
  user-select: none;
  z-index: 2;
}

.machine {
  background:
    linear-gradient(135deg, var(--machine-color, #74b9ff) 0%, color-mix(in srgb, var(--machine-color, #74b9ff) 80%, #000 20%) 100%),
    linear-gradient(135deg, #fff6, #fff0 60%);
  border: 2px solid #fff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 1rem;
  font-weight: 700;
  box-shadow: 0 0 12px 3px color-mix(in srgb, var(--machine-color, #74b9ff) 70%, #fff 30%),
              0 2px 6px color-mix(in srgb, var(--machine-color, #74b9ff) 60%, #000 40%) inset;
  overflow: hidden;
  backdrop-filter: blur(1px);
}

.machine:hover {
  box-shadow: 0 0 20px 6px #74b9ffdd, 0 2px 8px #0984e366 inset;
  transform: scale(1.1) rotate(1deg) translate(-50%, -50%);
}

.machine-id {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  font-size: 1rem;
  font-family: 'JetBrains Mono', 'Fira Mono', 'Consolas', monospace;
  font-weight: 800;
  letter-spacing: 1px;
  text-shadow:
    0 1px 3px rgba(0, 0, 0, 0.8),
    0 0 8px rgba(255, 255, 255, 0.6),
    0 0 12px rgba(116, 185, 255, 0.4);
  color: #fff;
  white-space: nowrap;
  z-index: 2;
}

.machine-front {
  position: absolute;
  background: linear-gradient(135deg, #ffff00 0%, #ffd700 100%);
  box-shadow:
    0 0 8px rgba(255, 255, 0, 0.8),
    0 0 12px rgba(255, 215, 0, 0.4),
    inset 0 1px 2px rgba(255, 255, 255, 0.3);
  z-index: 4;
  pointer-events: none;
}

.obstacle {
  background: linear-gradient(135deg, #636e72 0%, #2d3436 100%);
  border: 1px solid #474747;
  border-radius: 2px;
  box-shadow: 0 0 4px 1px rgba(45, 52, 54, 0.3);
  z-index: 1;
}

.obstacle:hover {
  box-shadow: 0 0 8px 2px rgba(116, 185, 255, 0.5);
  border-color: #74b9ff;
}
</style>

