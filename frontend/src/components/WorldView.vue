<template>
  <div class="world-container">
    <div class="world-grid">
      <!-- Obstacles -->
      <GameObject
        v-for="obstacle in obstacles"
        :key="obstacle.obstacle_id"
        :object="obstacle"
        :transformer="transformer"
        type="obstacle"
      />

      <!-- Carried resources -->
      <GameObject
        v-for="(res, idx) in carriedResources"
        :key="'carried-' + res.holder_id + '-' + res.slot"
        :object="res"
        :transformer="transformer"
        type="carried_resource"
      />

      <!-- Machines -->
      <GameObject
        v-for="machine in machines"
        :key="machine.machine_id"
        :object="machine"
        :transformer="transformer"
        type="machine"
      />

      <!-- Laser effects -->
      <LaserBeam
        v-for="laser in activeLasers"
        :key="'laser-' + laser.id"
        :laser="laser"
        :transformer="transformer"
      />

      <!-- Fog of war -->
      <FogOfWar
        :my-machines="myMachines"
        :transformer="transformer"
      />

      <!-- Grid overlay -->
      <div v-if="showGrid" class="grid-overlay"></div>
    </div>

    <!-- Command panel -->
    <CommandPanel :human-id="humanId" :api-key="apiKey" />
  </div>
</template>

<script setup>
import GameObject from './GameObject.vue'
import LaserBeam from './LaserBeam.vue'
import CommandPanel from './CommandPanel.vue'
import FogOfWar from './FogOfWar.vue'

defineProps({
  machines: Array,
  obstacles: Array,
  carriedResources: Array,
  activeLasers: Array,
  transformer: Object,
  showGrid: Boolean,
  myMachines: Array,
  humanId: String,
  apiKey: String
})
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
