<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import { usePlano } from '../stores/plano'
import { COR_PRIORIDADE, ROTULO_MODO, ROTULO_PRIORIDADE, corViatura } from '../cores'
import type { HexFeature, Prioridade } from '../types'

const plano = usePlano()
const el = ref<HTMLDivElement>()
const colorirPor = ref<'prioridade' | 'viatura'>('prioridade')
const mostrarOcorrencias = ref(false)

let mapa: L.Map
const renderer = L.canvas({ padding: 0.5 })
const camadaTerritorio = L.layerGroup()
const camadaHex = L.layerGroup()
const camadaPatrulha = L.layerGroup()
const camadaOcorrencias = L.layerGroup()
const camadaViaturas = L.layerGroup()

const hexPorId = computed(() => new Map(plano.hexagonos?.features.map((h) => [h.properties.hex_id, h]) ?? []))

const donoDoHex = computed(() => {
  const dono = new Map<number, string>()
  for (const [vid, ids] of Object.entries(plano.estado?.atribuicoes ?? {})) {
    for (const id of ids) dono.set(id, vid)
  }
  return dono
})

// Cartões cujas faixas aparecem no mapa: o da viatura selecionada, ou todos.
const cartoesVisiveis = computed(() =>
  plano.viaturaSelecionada
    ? plano.cartoes.filter((c) => c.viatura === plano.viaturaSelecionada)
    : plano.cartoes,
)

function latLngs(h: HexFeature): [number, number][] {
  return h.geometry.coordinates[0].map(([lon, lat]) => [lat, lon])
}

function centro(h: HexFeature): L.LatLng {
  return L.latLngBounds(latLngs(h)).getCenter()
}

function desenharTerritorio() {
  camadaTerritorio.clearLayers()
  if (!plano.territorio) return
  const geo = L.geoJSON(plano.territorio, {
    style: { color: '#1c1c1c', weight: 2, fill: false },
  }).addTo(camadaTerritorio)
  mapa.fitBounds(geo.getBounds(), { padding: [20, 20] })
}

function desenharHexagonos() {
  camadaHex.clearLayers()
  if (!plano.hexagonos) return
  const dono = donoDoHex.value
  const mudaram = new Set(plano.estado?.mudanca?.hex_mudaram ?? [])
  const hora = plano.horaSelecionada

  L.geoJSON(plano.hexagonos, {
    style: (f) => {
      const p = (f as HexFeature).properties
      const vid = dono.get(p.hex_id)
      const daSelecionada = plano.viaturaSelecionada !== null && vid === plano.viaturaSelecionada
      const apagado = (plano.viaturaSelecionada !== null && !daSelecionada) || hora !== null
      const porViatura = colorirPor.value === 'viatura' && vid
      return {
        renderer,
        color: mudaram.has(p.hex_id) ? '#d00000' : '#ffffff',
        weight: mudaram.has(p.hex_id) ? 1.5 : 0.5,
        fillColor: porViatura ? corViatura(vid, plano.viaturas) : COR_PRIORIDADE[p.prioridade],
        fillOpacity: apagado ? 0.2 : p.score_total > 0 || porViatura ? 0.6 : 0.25,
      }
    },
    onEachFeature: (f, layer) => {
      const p = (f as HexFeature).properties
      const vid = dono.get(p.hex_id)
      const naturezas = Object.entries(p.por_natureza).filter(([, n]) => n > 0).map(([k, n]) => `${k}: ${n}`).join(' · ')
      const naHora = hora !== null ? `<br>Pontos às ${String(hora).padStart(2, '0')}h: ${p.por_hora[hora]}` : ''
      layer.bindTooltip(
        `<b>Hexágono ${p.hex_id}</b> · ${ROTULO_PRIORIDADE[p.prioridade]}<br>` +
        `Pontos ${p.score_total} · ${p.total} ocorrências${naturezas ? `<br>${naturezas}` : ''}${naHora}` +
        `<br>Viatura: ${vid ?? '—'}${mudaram.has(p.hex_id) ? ' · <span style="color:#d00000">mudou de viatura</span>' : ''}`,
        { sticky: true },
      )
      layer.on('click', () => { if (vid) plano.viaturaSelecionada = plano.viaturaSelecionada === vid ? null : vid })
    },
  }).addTo(camadaHex)
}

// Na faixa selecionada: a área de patrulha de cada viatura e as quadrículas de destaque.
function desenharPatrulha() {
  camadaPatrulha.clearLayers()
  if (plano.horaSelecionada === null) return
  for (const c of cartoesVisiveis.value) {
    const faixa = c.faixas.find((f) => f.hora === plano.horaSelecionada)
    if (!faixa) continue
    const cor = corViatura(c.viatura, plano.viaturas)
    for (const id of faixa.hexagonos_patrulha) {
      const h = hexPorId.value.get(id)
      if (h) L.polygon(latLngs(h), { renderer, color: cor, weight: 0.5, fillColor: cor, fillOpacity: 0.35, interactive: false }).addTo(camadaPatrulha)
    }
    for (const id of faixa.hexagonos_destaque) {
      const h = hexPorId.value.get(id)
      if (h) L.polygon(latLngs(h), { renderer, color: '#000', weight: 2.5, fillColor: cor, fillOpacity: 0.9, interactive: false }).addTo(camadaPatrulha)
    }
  }
}

function desenharOcorrencias() {
  camadaOcorrencias.clearLayers()
  if (!mostrarOcorrencias.value || !plano.ocorrencias) return
  for (const f of plano.ocorrencias.features) {
    if (plano.horaSelecionada !== null && f.properties.hora !== plano.horaSelecionada) continue
    const [lon, lat] = f.geometry.coordinates
    L.circleMarker([lat, lon], { renderer, radius: 2.5, color: '#222', weight: 0.5, fillOpacity: 0.8 })
      .bindTooltip(`${f.properties.natureza} · ${new Date(f.properties.data_hora).toLocaleString('pt-BR')}`)
      .addTo(camadaOcorrencias)
  }
}

function desenharViaturas() {
  camadaViaturas.clearLayers()
  for (const c of plano.cartoes) {
    // Posição: quadrícula de destaque da faixa selecionada, ou o hexágono-base.
    const faixa = plano.horaSelecionada !== null ? c.faixas.find((f) => f.hora === plano.horaSelecionada) : undefined
    const hex = hexPorId.value.get(faixa?.hexagonos_destaque[0] ?? c.hex_base)
    if (!hex) continue
    const cor = corViatura(c.viatura, plano.viaturas)
    L.marker(centro(hex), {
      icon: L.divIcon({
        className: 'marcador-viatura',
        html: `<span style="background:${cor}">${c.viatura.replace('VTR-', '')}</span>`,
        iconSize: [26, 26],
      }),
      zIndexOffset: 1000,
    })
      .bindTooltip(`${c.viatura}${faixa ? ` · ${ROTULO_MODO[faixa.modo]}` : ' · hexágono-base'}`)
      .on('click', () => { plano.viaturaSelecionada = plano.viaturaSelecionada === c.viatura ? null : c.viatura })
      .addTo(camadaViaturas)
  }
}

function desenharTudo() {
  desenharHexagonos()
  desenharPatrulha()
  desenharOcorrencias()
  desenharViaturas()
}

onMounted(() => {
  mapa = L.map(el.value!, { preferCanvas: true }).setView([-19.875, -44.04], 14)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap',
  }).addTo(mapa)
  for (const c of [camadaTerritorio, camadaHex, camadaPatrulha, camadaOcorrencias, camadaViaturas]) c.addTo(mapa)
  desenharTerritorio()
  desenharTudo()
  // O Leaflet não percebe sozinho quando o contêiner muda de tamanho.
  observador = new ResizeObserver(() => mapa.invalidateSize())
  observador.observe(el.value!)
})

let observador: ResizeObserver | undefined
onBeforeUnmount(() => {
  observador?.disconnect()
  mapa?.remove()
})

watch(() => plano.territorio, desenharTerritorio)
watch(
  () => [plano.hexagonos, plano.estado, plano.viaturaSelecionada, plano.horaSelecionada, colorirPor.value, mostrarOcorrencias.value],
  desenharTudo,
)
</script>

<template>
  <div class="mapa-wrap">
    <div ref="el" class="mapa" />
    <div class="controles">
      <label>
        Colorir por
        <select v-model="colorirPor">
          <option value="prioridade">Prioridade</option>
          <option value="viatura">Área da viatura</option>
        </select>
      </label>
      <label><input v-model="mostrarOcorrencias" type="checkbox" /> Ocorrências</label>
    </div>
    <div class="legenda">
      <div v-for="(cor, p) in COR_PRIORIDADE" :key="p">
        <i :style="{ background: cor }" /> {{ ROTULO_PRIORIDADE[p as Prioridade] }}
      </div>
      <div v-if="plano.estado?.mudanca"><i class="mudou" /> Mudou de viatura</div>
      <div v-if="plano.horaSelecionada !== null"><i class="destaque" /> Quadrícula de destaque</div>
    </div>
    <p v-if="plano.horaSelecionada !== null" class="aviso-hora">
      Faixa {{ String(plano.horaSelecionada).padStart(2, '0') }}h: áreas de patrulha
      {{ plano.viaturaSelecionada ? `da ${plano.viaturaSelecionada}` : 'de todas as viaturas' }}
    </p>
  </div>
</template>

<style scoped>
.mapa-wrap { position: relative; height: 100%; }
.mapa { height: 100%; }
.controles, .legenda, .aviso-hora {
  position: absolute; z-index: 500; background: var(--superficie); border-radius: 6px;
  padding: 8px 10px; box-shadow: 0 1px 4px rgb(0 0 0 / 0.25); font-size: 13px;
}
.controles { top: 10px; right: 10px; display: flex; gap: 12px; align-items: center; }
.legenda { bottom: 20px; right: 10px; display: grid; gap: 4px; }
.legenda i { display: inline-block; width: 14px; height: 14px; vertical-align: -2px; margin-right: 4px; border-radius: 2px; }
.legenda i.mudou { border: 2px solid #d00000; background: transparent; }
.legenda i.destaque { border: 2px solid #000; background: #888; }
.aviso-hora { top: 10px; left: 56px; margin: 0; }
</style>
