import type { FeatureCollection } from 'geojson'
import type { Estado, Faixa, Hexagonos, Ocorrencias } from './types'

// Em dev o Vite redireciona /api para o backend (vite.config.ts).
const API_URL: string = import.meta.env.VITE_API_URL ?? '/api'

async function pedir<T>(rota: string, metodo: 'GET' | 'POST' = 'GET'): Promise<T> {
  const res = await fetch(`${API_URL}${rota}`, { method: metodo })
  if (!res.ok) {
    const corpo = await res.json().catch(() => null)
    throw new Error(corpo?.detail ?? `${res.status} em ${rota}`)
  }
  return res.json()
}

export const buscarTerritorio = () => pedir<FeatureCollection>('/territorio')
export const buscarHexagonos = () => pedir<Hexagonos>('/hexagonos')
export const buscarOcorrencias = () => pedir<Ocorrencias>('/ocorrencias')
export const buscarFaixas = () => pedir<Faixa[]>('/faixas')
export const buscarEstado = () => pedir<Estado>('/estado')

export const empenhar = (id: string) => pedir<Estado>(`/viaturas/${id}/empenhar`, 'POST')
export const liberar = (id: string) => pedir<Estado>(`/viaturas/${id}/liberar`, 'POST')
export const aplicarCenario = (n: 1 | 2 | 3) => pedir<Estado>(`/cenarios/${n}`, 'POST')
