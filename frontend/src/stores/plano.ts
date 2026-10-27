import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'
import type { FeatureCollection } from 'geojson'
import * as api from '../api'
import type { Estado, Faixa, Hexagonos, Ocorrencias } from '../types'

export const usePlano = defineStore('plano', () => {
  const territorio = shallowRef<FeatureCollection | null>(null)
  const hexagonos = shallowRef<Hexagonos | null>(null)
  const ocorrencias = shallowRef<Ocorrencias | null>(null)
  const faixas = ref<Faixa[]>([])
  const estado = shallowRef<Estado | null>(null)
  const carregando = ref(true)
  const ocupado = ref(false)
  const erro = ref<string | null>(null)
  const horaSelecionada = ref<number | null>(null)
  const viaturaSelecionada = ref<string | null>(null)

  const viaturas = computed(() => estado.value?.viaturas ?? [])
  const disponiveis = computed(() => viaturas.value.filter((v) => v.disponivel))
  const cartoes = computed(() => Object.values(estado.value?.cartoes ?? {}))

  async function carregar() {
    try {
      const [t, h, o, f, e] = await Promise.all([
        api.buscarTerritorio(), api.buscarHexagonos(), api.buscarOcorrencias(),
        api.buscarFaixas(), api.buscarEstado(),
      ])
      territorio.value = t
      hexagonos.value = h
      ocorrencias.value = o
      faixas.value = f
      estado.value = e
    } catch (e) {
      erro.value = `${e}. O backend está rodando na porta 8000?`
    } finally {
      carregando.value = false
    }
  }

  // Toda ação no backend devolve o estado completo da frota.
  async function executar(acao: () => Promise<Estado>) {
    ocupado.value = true
    erro.value = null
    try {
      estado.value = await acao()
      if (viaturaSelecionada.value && !estado.value.cartoes[viaturaSelecionada.value]) {
        viaturaSelecionada.value = null
      }
    } catch (e) {
      erro.value = String(e)
    } finally {
      ocupado.value = false
    }
  }

  function alternarDisponibilidade(id: string) {
    const v = viaturas.value.find((x) => x.id === id)
    if (!v) return
    return executar(() => (v.disponivel ? api.empenhar(id) : api.liberar(id)))
  }

  const aplicarCenario = (n: 1 | 2 | 3) => executar(() => api.aplicarCenario(n))

  return {
    territorio, hexagonos, ocorrencias, faixas, estado, carregando, ocupado, erro,
    horaSelecionada, viaturaSelecionada, viaturas, disponiveis, cartoes,
    carregar, alternarDisponibilidade, aplicarCenario,
  }
})
