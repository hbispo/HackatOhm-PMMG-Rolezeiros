import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type { FeatureCollection } from 'geojson'
import * as api from '../api'
import type { Distribuicao, Faixa, Hexagonos, Ocorrencias, Viatura } from '../types'

export const usePlano = defineStore('plano', () => {
  const territorio = shallowRef<FeatureCollection | null>(null)
  const hexagonos = shallowRef<Hexagonos | null>(null)
  const ocorrencias = shallowRef<Ocorrencias | null>(null)
  const faixas = ref<Faixa[]>([])
  const viaturas = ref<Viatura[]>([])
  const distribuicao = shallowRef<Distribuicao | null>(null)
  // Distribuição antes do último empenho, para mostrar o antes/depois.
  const anterior = shallowRef<Distribuicao | null>(null)
  const carregando = ref(true)
  const erro = ref<string | null>(null)
  const horaSelecionada = ref<number | null>(null)
  const viaturaSelecionada = ref<string | null>(null)

  const disponiveis = computed(() => viaturas.value.filter((v) => v.disponivel))

  async function carregar() {
    try {
      const [t, h, o, f, v] = await Promise.all([
        api.buscarTerritorio(), api.buscarHexagonos(), api.buscarOcorrencias(),
        api.buscarFaixas(), api.buscarViaturas(),
      ])
      territorio.value = t
      hexagonos.value = h
      ocorrencias.value = o
      faixas.value = f
      viaturas.value = v
      await redistribuir()
    } catch (e) {
      erro.value = String(e)
    } finally {
      carregando.value = false
    }
  }

  async function redistribuir() {
    if (!hexagonos.value) return
    anterior.value = distribuicao.value
    distribuicao.value = await api.calcularDistribuicao(viaturas.value, hexagonos.value, faixas.value)
  }

  async function alternarDisponibilidade(id: string) {
    const v = viaturas.value.find((x) => x.id === id)
    if (!v) return
    v.disponivel = !v.disponivel
    if (!v.disponivel && viaturaSelecionada.value === id) viaturaSelecionada.value = null
    await redistribuir()
  }

  // Cenários do edital: 1 = todas disponíveis, 2 = uma empenhada, 3 = várias empenhadas.
  async function aplicarCenario(n: 1 | 2 | 3) {
    const empenhadas = n === 1 ? 0 : n === 2 ? 1 : 2
    // Recalcula a partir do cenário 1, para o antes/depois sempre comparar com a frota completa.
    viaturas.value.forEach((v) => { v.disponivel = true })
    distribuicao.value = null
    await redistribuir()
    if (empenhadas === 0) { anterior.value = null; return }
    viaturas.value.forEach((v, i) => { v.disponivel = i >= empenhadas })
    await redistribuir()
  }

  return {
    territorio, hexagonos, ocorrencias, faixas, viaturas, distribuicao, anterior,
    carregando, erro, horaSelecionada, viaturaSelecionada, disponiveis,
    carregar, redistribuir, alternarDisponibilidade, aplicarCenario,
  }
})
