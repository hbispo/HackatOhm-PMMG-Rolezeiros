// Tipos espelhando docs/api.md. Alterou o contrato? Altere aqui também.
import type { Feature, FeatureCollection, Point, Polygon } from 'geojson'

export type Natureza = 'A' | 'B' | 'C' | 'D' | 'E' | 'F'
export type Prioridade = 'baixa' | 'média' | 'alta' | 'muito alta'
export type TipoViatura = 'atendimento' | 'preventiva'
export type Modo = 'ponto_base' | 'patrulha_2km' | 'patrulha_3km'
export type Classe = 1 | 2 | 3

export interface HexProps {
  hex_id: number
  score_total: number
  nivel: 1 | 2 | 3 | 4
  prioridade: Prioridade
  total: number
  por_natureza: Record<Natureza, number>
  por_hora: number[]
}
export type Hexagonos = FeatureCollection<Polygon, HexProps>
export type HexFeature = Feature<Polygon, HexProps>

export interface OcorrenciaProps {
  id: string
  natureza: Natureza
  data_hora: string
  hora: number
  hex_id: number | null
}
export type Ocorrencias = FeatureCollection<Point, OcorrenciaProps>

export interface Faixa {
  hora: number
  pontos: number
  ranking: number
  classe: Classe
  modo: Modo
}

export interface Viatura {
  id: string
  tipo: TipoViatura
  disponivel: boolean
  hex_base: number | null
}

export interface FaixaCartao {
  hora: number
  faixa: string
  classe: Classe
  modo: Modo
  raio_km: number
  ponto_base_min: number
  patrulha_min: number
  hexagonos_destaque: number[]
  pontos_faixa: number
  origem_destaque: string
  hexagonos_patrulha: number[]
  pct_da_area: number
  descricao: string
}

export interface Cartao {
  viatura: string
  tipo: TipoViatura
  hex_base: number
  qtd_hexagonos_area: number
  hexagonos_area: number[]
  faixas: FaixaCartao[]
}

export interface Carga {
  viatura: string
  hexagonos: number
  pontos: number
  pct_pontos: number
  dist_max_km: number
}

export interface Mudanca {
  acao: 'empenhar' | 'liberar'
  viaturas: string[]
  hex_descobertos: number[]
  pct_pontos_descobertos: number
  hex_mudaram: number[]
}

export interface Estado {
  cenario: number
  viaturas: Viatura[]
  atribuicoes: Record<string, number[]>
  cartoes: Record<string, Cartao>
  carga: Carga[]
  problemas: string[]
  mudanca: Mudanca | null
}
