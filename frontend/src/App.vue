<script setup lang="ts">
import { onMounted } from 'vue'
import { usePlano } from './stores/plano'
import MapView from './components/MapView.vue'
import ViaturasPanel from './components/ViaturasPanel.vue'
import CartoesPrograma from './components/CartoesPrograma.vue'
import ComoFunciona from './components/ComoFunciona.vue'

const plano = usePlano()
onMounted(plano.carregar)
</script>

<template>
  <header class="topo">
    <h1>Policiamento Preventivo <span>· 39ª CIA PM</span></h1>
    <ComoFunciona />
  </header>
  <p v-if="plano.erro" class="erro">{{ plano.erro }}</p>
  <main class="layout">
    <ViaturasPanel class="lateral" />
    <MapView class="centro" />
    <CartoesPrograma class="lateral direita" />
  </main>
</template>

<style scoped>
.topo {
  height: 48px; display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; background: #1c1c1c; color: #f4f1ea; border-bottom: 3px solid var(--dourado);
}
h1 { font-size: 17px; margin: 0; letter-spacing: .02em; }
h1 span { color: var(--dourado); font-weight: 400; }
.erro { background: #ffe0e0; color: #900; margin: 0; padding: 8px 16px; }
.layout { display: grid; grid-template-columns: 300px 1fr 400px; height: calc(100vh - 51px); }
.lateral { background: var(--superficie); border-right: 1px solid var(--borda); }
.direita { border-right: 0; border-left: 1px solid var(--borda); }
.centro { min-height: 0; }

@media (max-width: 1200px) {
  .layout { grid-template-columns: 1fr; grid-template-rows: auto 60vh auto; height: auto; }
  .lateral, .direita { border: 0; }
}

@media print {
  .topo, .layout > :not(.direita) { display: none; }
  .layout { display: block; height: auto; }
}
</style>
