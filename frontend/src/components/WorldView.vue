<template>
  <div class="world-container">
    <div class="world-grid">
      <!-- 障碍物 -->
      <GameObject
        v-for="obstacle in visibleObstacles"
        :key="obstacle.obstacle_id"
        :object="obstacle"
        :transformer="transformer"
        type="obstacle"
      />

      <!-- 机器人 -->
      <GameObject
        v-for="machine in visibleMachines"
        :key="machine.machine_id"
        :object="machine"
        :transformer="transformer"
        type="machine"
      />

      <!-- 激光特效 -->
      <LaserBeam
        v-for="laser in activeLasers"
        :key="'laser-' + laser.id"
        :laser="laser"
        :transformer="transformer"
      />

      <!-- 网格辅助线 -->
      <div v-if="showGrid" class="grid-overlay"></div>
    </div>

    <!-- 命令面板 -->
    <CommandPanel :human-id="humanId" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import GameObject from './GameObject.vue'
import LaserBeam from './LaserBeam.vue'
import CommandPanel from './CommandPanel.vue'

const props = defineProps({
  machines: Array,
  obstacles: Array,
  activeLasers: Array,
  transformer: Object,
  isPositionVisible: Function,
  showGrid: Boolean,
  myMachines: Array,
  humanId: String
})

const visibleMachines = computed(() =>
  props.machines.filter(m => props.isPositionVisible(m.position, props.myMachines))
)

const visibleObstacles = computed(() =>
  props.obstacles.filter(o => props.isPositionVisible(o.position, props.myMachines))
)
</script>

<style scoped>
.world-container {
  width: 100vw;
  height: 100vh;
  position: relative;
}

.world-grid {
  width: 100vw;
  height: 100vh;
  position: relative;
  background:
    linear-gradient(to right, rgba(200, 200, 200, 0.3) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(200, 200, 200, 0.3) 1px, transparent 1px),
    linear-gradient(to right, rgba(100, 100, 100, 0.8) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(100, 100, 100, 0.8) 1px, transparent 1px);
  background-size: 30px 30px, 30px 30px, 100vw 30px, 30px 100vh;
  background-position: 50% 50%, 50% 50%, 50% 50%, 50% 50%;
}

.grid-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.1) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.1) 1px, transparent 1px);
  background-size: 30px 30px;
  background-position: calc(50% - 15px) calc(50% - 15px);
  z-index: 0;
}
</style>

