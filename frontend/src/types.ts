// Tipos espelhando docs/api.md. Alterou o contrato? Altere aqui também.
import type { Feature, FeatureCollection, Point, Polygon } from 'geojson'

export type Natureza = 'A' | 'B' | 'C' | 'D' | 'E' | 'F'
export type Prioridade = 'baixa' | 'media' | 'alta' | 'muito_alta'
export type TipoViatura = 'atendimento' | 'preventiva'
export type Modo = 'ponto_base' | 'entorno_2km' | 'entorno_3km'

export interface HexProps {
  id: string
  score: number
  prioridade: Prioridade
  total: number
  por_natureza: Record<Natureza, number>
}
export type Hexagonos = FeatureCollection<Polygon, HexProps>
export type HexFeature = Feature<Polygon, HexProps>

export interface OcorrenciaProps {
  id: string
  natureza: Natureza
  data_hora: string
  hora: number
  hex_id: string | null
}
export type Ocorrencias = FeatureCollection<Point, OcorrenciaProps>

export interface Faixa {
  hora: number
  score: number
  classe: 1 | 2 | 3
  ranking: number
}

export interface Viatura {
  id: string
  nome: string
  tipo: TipoViatura
  disponivel: boolean
}

export interface FaixaCartao {
  hora: number
  classe: 1 | 2 | 3
  modo: Modo
  hex_ponto_base: string | null
  raio_m: number
}

export interface Cartao {
  viatura_id: string
  faixas: FaixaCartao[]
}

export interface Metricas {
  cobertura_area_pct: number
  cobertura_risco_pct: number
  hex_descobertos: string[]
}

export interface Distribuicao {
  atribuicoes: Record<string, string[]>
  cartoes: Cartao[]
  metricas: Metricas
}

export const PESOS: Record<Natureza, number> = { A: 4, B: 5, C: 1, D: 1, E: 2, F: 3 }
