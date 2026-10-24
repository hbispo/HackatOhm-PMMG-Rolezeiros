<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import L from 'leaflet'
import { usePlano } from '../stores/plano'
import { COR_PRIORIDADE, ROTULO_PRIORIDADE, corViatura } from '../cores'
import type { HexFeature, Prioridade } from '../types'

const plano = usePlano()
const el = ref<HTMLDivElement>()
const colorirPor = ref<'prioridade' | 'viatura'>('prioridade')
const mostrarOcorrencias = ref(false)

let mapa: L.Map
const renderer = L.canvas({ padding: 0.5 })
const camadaTerritorio = L.layerGroup()
const camadaHex = L.layerGroup()
const camadaOcorrencias = L.layerGroup()
const camadaViaturas = L.layerGroup()

function donoDoHex(): Map<string, string> {
  const dono = new Map<string, string>()
  for (const [vid, ids] of Object.entries(plano.distribuicao?.atribuicoes ?? {})) {
    for (const id of ids) dono.set(id, vid)
  }
  return dono
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
  const dono = donoDoHex()
  const descobertos = new Set(plano.distribuicao?.metricas.hex_descobertos ?? [])
  // Hexágonos que estavam cobertos antes do último empenho e agora não estão.
  const antes = new Set(plano.anterior?.metricas.hex_descobertos ?? [])
  const afetados = plano.anterior ? new Set([...descobertos].filter((id) => !antes.has(id))) : new Set<string>()

  L.geoJSON(plano.hexagonos, {
    style: (f) => {
      const p = (f as HexFeature).properties
      const vid = dono.get(p.id)
      const selecionado = plano.viaturaSelecionada && vid === plano.viaturaSelecionada
      const base = colorirPor.value === 'viatura' && vid
        ? corViatura(vid, plano.viaturas)
        : COR_PRIORIDADE[p.prioridade]
      return {
        renderer,
        color: afetados.has(p.id) ? '#d00000' : selecionado ? '#000' : '#ffffff',
        weight: afetados.has(p.id) ? 2 : selecionado ? 1.5 : 0.5,
        fillColor: base,
        fillOpacity: plano.viaturaSelecionada && !selecionado ? 0.15 : p.score > 0 || colorirPor.value === 'viatura' ? 0.6 : 0.2,
      }
    },
    onEachFeature: (f, layer) => {
      const p = (f as HexFeature).properties
      const vid = dono.get(p.id)
      const naturezas = Object.entries(p.por_natureza).filter(([, n]) => n > 0).map(([k, n]) => `${k}: ${n}`).join(' · ')
      layer.bindTooltip(
        `<b>${p.id}</b> · ${ROTULO_PRIORIDADE[p.prioridade]}<br>` +
        `Score ${p.score} · ${p.total} ocorrências${naturezas ? `<br>${naturezas}` : ''}` +
        `<br>Viatura: ${vid ?? '—'}${descobertos.has(p.id) ? ' · <span style="color:#d00000">descoberto</span>' : ''}`,
        { sticky: true },
      )
      layer.on('click', () => { if (vid) plano.viaturaSelecionada = plano.viaturaSelecionada === vid ? null : vid })
    },
  }).addTo(camadaHex)
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
  if (!plano.distribuicao || !plano.hexagonos) return
  const porId = new Map(plano.hexagonos.features.map((h) => [h.properties.id, h]))
  for (const c of plano.distribuicao.cartoes) {
    // Posição: ponto-base da hora selecionada, ou da faixa de maior incidência.
    const faixa = plano.horaSelecionada !== null
      ? c.faixas.find((f) => f.hora === plano.horaSelecionada)
      : c.faixas.find((f) => f.modo === 'ponto_base')
    const hex = faixa?.hex_ponto_base ? porId.get(faixa.hex_ponto_base) : undefined
    if (!hex) continue
    const centro = L.polygon(hex.geometry.coordinates[0].map(([lon, lat]) => [lat, lon] as [number, number])).getBounds().getCenter()
    const cor = corViatura(c.viatura_id, plano.viaturas)
    if (faixa) {
      L.circle(centro, { radius: faixa.raio_m, color: cor, weight: 1.5, dashArray: '4 4', fill: false, interactive: false })
        .addTo(camadaViaturas)
    }
    L.marker(centro, {
      icon: L.divIcon({
        className: 'marcador-viatura',
        html: `<span style="background:${cor}">${c.viatura_id.replace('VTR-', '')}</span>`,
        iconSize: [26, 26],
      }),
    })
      .bindTooltip(`${c.viatura_id} · ${faixa?.modo.replace('_', ' ') ?? ''}`)
      .on('click', () => { plano.viaturaSelecionada = c.viatura_id })
      .addTo(camadaViaturas)
  }
}

function desenharTudo() {
  desenharHexagonos()
  desenharOcorrencias()
  desenharViaturas()
}

onMounted(() => {
  mapa = L.map(el.value!, { preferCanvas: true }).setView([-19.875, -44.04], 14)
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap',
  }).addTo(mapa)
  camadaTerritorio.addTo(mapa)
  camadaHex.addTo(mapa)
  camadaOcorrencias.addTo(mapa)
  camadaViaturas.addTo(mapa)
  desenharTerritorio()
  desenharTudo()
})

onBeforeUnmount(() => mapa?.remove())

watch(() => plano.territorio, desenharTerritorio)
watch(
  () => [plano.hexagonos, plano.distribuicao, plano.viaturaSelecionada, plano.horaSelecionada, colorirPor.value, mostrarOcorrencias.value],
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
      <div v-if="plano.anterior"><i class="afetado" /> Descoberto após empenho</div>
    </div>
  </div>
</template>

<style scoped>
.mapa-wrap { position: relative; height: 100%; }
.mapa { height: 100%; }
.controles, .legenda {
  position: absolute; z-index: 500; background: var(--superficie); border-radius: 6px;
  padding: 8px 10px; box-shadow: 0 1px 4px rgb(0 0 0 / 0.25); font-size: 13px;
}
.controles { top: 10px; right: 10px; display: flex; gap: 12px; align-items: center; }
.legenda { bottom: 20px; right: 10px; display: grid; gap: 4px; }
.legenda i { display: inline-block; width: 14px; height: 14px; vertical-align: -2px; margin-right: 4px; border-radius: 2px; }
.legenda i.afetado { border: 2px solid #d00000; background: transparent; }
</style>
