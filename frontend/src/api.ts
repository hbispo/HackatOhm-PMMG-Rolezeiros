import type {
  Cartao, Distribuicao, Faixa, FaixaCartao, HexFeature, Hexagonos, Ocorrencias, Viatura,
} from './types'
import type { FeatureCollection } from 'geojson'

// Sem VITE_API_URL o front usa os mocks de public/mock (gerados por scripts/gerar_mocks.py).
const API_URL: string | undefined = import.meta.env.VITE_API_URL
export const usandoMock = !API_URL

async function get<T>(rota: string, mock: string): Promise<T> {
  const url = API_URL ? `${API_URL}${rota}` : `${import.meta.env.BASE_URL}mock/${mock}`
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${res.status} em ${url}`)
  return res.json()
}

export const buscarTerritorio = () => get<FeatureCollection>('/territorio', 'territorio.json')
export const buscarHexagonos = () => get<Hexagonos>('/hexagonos', 'hexagonos.json')
export const buscarOcorrencias = () => get<Ocorrencias>('/ocorrencias', 'ocorrencias.json')
export const buscarFaixas = () => get<Faixa[]>('/faixas', 'faixas.json')
export const buscarViaturas = () => get<Viatura[]>('/viaturas', 'viaturas.json')

export async function calcularDistribuicao(
  viaturas: Viatura[], hexagonos: Hexagonos, faixas: Faixa[],
): Promise<Distribuicao> {
  if (!API_URL) return distribuicaoMock(viaturas, hexagonos, faixas)
  const res = await fetch(`${API_URL}/distribuicao`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ viaturas }),
  })
  if (!res.ok) throw new Error(`${res.status} em /distribuicao`)
  return res.json()
}

// ---------------------------------------------------------------------------
// Distribuição PROVISÓRIA, só para o front funcionar antes do backend.
// O algoritmo de verdade é do backend; isto aqui é deliberadamente simples.
// ---------------------------------------------------------------------------

function centro(h: HexFeature): [number, number] {
  const anel = h.geometry.coordinates[0].slice(0, 6)
  const lon = anel.reduce((s, p) => s + p[0], 0) / anel.length
  const lat = anel.reduce((s, p) => s + p[1], 0) / anel.length
  return [lon, lat]
}

function distanciaM(a: [number, number], b: [number, number]): number {
  const kLat = 111_320
  const kLon = 111_320 * Math.cos((a[1] * Math.PI) / 180)
  return Math.hypot((a[0] - b[0]) * kLon, (a[1] - b[1]) * kLat)
}

function distribuicaoMock(viaturas: Viatura[], hexagonos: Hexagonos, faixas: Faixa[]): Distribuicao {
  const livres = viaturas.filter((v) => v.disponivel)
  const hexes = hexagonos.features
  const centros = new Map(hexes.map((h) => [h.properties.id, centro(h)]))
  const vazio: Distribuicao = {
    atribuicoes: {}, cartoes: [],
    metricas: { cobertura_area_pct: 0, cobertura_risco_pct: 0, hex_descobertos: hexes.map((h) => h.properties.id) },
  }
  if (livres.length === 0) return vazio

  // Sementes: guloso, equilibrando score e distância às sementes já escolhidas.
  const sementes: HexFeature[] = []
  while (sementes.length < livres.length) {
    let melhor = hexes[0]
    let melhorValor = -1
    for (const h of hexes) {
      const c = centros.get(h.properties.id)!
      const d = sementes.length
        ? Math.min(...sementes.map((s) => distanciaM(c, centros.get(s.properties.id)!)))
        : 1
      const valor = (h.properties.score + 1) * d
      if (valor > melhorValor) { melhorValor = valor; melhor = h }
    }
    sementes.push(melhor)
  }

  // Cada hexágono vai para a semente mais próxima.
  const atribuicoes: Record<string, string[]> = Object.fromEntries(livres.map((v) => [v.id, []]))
  for (const h of hexes) {
    const c = centros.get(h.properties.id)!
    let i = 0
    let menor = Infinity
    sementes.forEach((s, k) => {
      const d = distanciaM(c, centros.get(s.properties.id)!)
      if (d < menor) { menor = d; i = k }
    })
    atribuicoes[livres[i].id].push(h.properties.id)
  }

  const scorePorId = new Map(hexes.map((h) => [h.properties.id, h.properties.score]))
  const ordenadas = [...faixas].sort((a, b) => a.ranking - b.ranking)

  const cartoes: Cartao[] = livres.map((v) => {
    const top = [...atribuicoes[v.id]]
      .sort((a, b) => scorePorId.get(b)! - scorePorId.get(a)!)
      .slice(0, 3)
    let pontoBaseClasse2 = 0
    const itens: FaixaCartao[] = []
    for (const f of ordenadas) {
      if (f.classe === 1 || (f.classe === 2 && pontoBaseClasse2 < 4)) {
        if (f.classe === 2) pontoBaseClasse2++
        itens.push({ hora: f.hora, classe: f.classe, modo: 'ponto_base', hex_ponto_base: null, raio_m: 1000 })
      } else if (f.classe === 2) {
        itens.push({ hora: f.hora, classe: 2, modo: 'entorno_2km', hex_ponto_base: top[0], raio_m: 2000 })
      } else {
        itens.push({ hora: f.hora, classe: 3, modo: 'entorno_3km', hex_ponto_base: top[0], raio_m: 3000 })
      }
    }
    itens.sort((a, b) => a.hora - b.hora)
    // Alterna as quadrículas na ordem cronológica: a mesma nunca cai em faixas consecutivas.
    let giro = 0
    for (const f of itens) {
      if (f.modo === 'ponto_base') f.hex_ponto_base = top[giro++ % top.length]
    }
    return { viatura_id: v.id, faixas: itens }
  })

  // Coberto = a até 1 km de algum ponto-base.
  const pontosBase = new Set(cartoes.flatMap((c) => c.faixas.filter((f) => f.modo === 'ponto_base').map((f) => f.hex_ponto_base!)))
  const basesC = [...pontosBase].map((id) => centros.get(id)!)
  const descobertos: string[] = []
  let riscoTotal = 0
  let riscoCoberto = 0
  for (const h of hexes) {
    riscoTotal += h.properties.score
    const coberto = basesC.some((b) => distanciaM(b, centros.get(h.properties.id)!) <= 1000)
    if (coberto) riscoCoberto += h.properties.score
    else descobertos.push(h.properties.id)
  }

  return {
    atribuicoes,
    cartoes,
    metricas: {
      cobertura_area_pct: Math.round((1000 * (hexes.length - descobertos.length)) / hexes.length) / 10,
      cobertura_risco_pct: Math.round((1000 * riscoCoberto) / Math.max(riscoTotal, 1)) / 10,
      hex_descobertos: descobertos,
    },
  }
}
