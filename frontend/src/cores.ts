import type { Modo, Prioridade } from './types'

export const COR_PRIORIDADE: Record<Prioridade, string> = {
  baixa: '#fde9a8',
  média: '#fdae61',
  alta: '#e34a33',
  'muito alta': '#7a0177',
}

export const ROTULO_PRIORIDADE: Record<Prioridade, string> = {
  baixa: 'Baixa',
  média: 'Média',
  alta: 'Alta',
  'muito alta': 'Muito alta',
}

export const ROTULO_MODO: Record<Modo, string> = {
  ponto_base: 'Ponto-base',
  patrulha_2km: 'Patrulha 2 km',
  patrulha_3km: 'Patrulha 3 km',
}

const PALETA_VIATURAS = ['#1f77b4', '#2ca02c', '#9467bd', '#ff7f0e', '#17becf', '#8c564b', '#e377c2', '#bcbd22']

export function corViatura(id: string, todas: { id: string }[]): string {
  const i = todas.findIndex((v) => v.id === id)
  return PALETA_VIATURAS[(i < 0 ? 0 : i) % PALETA_VIATURAS.length]
}
