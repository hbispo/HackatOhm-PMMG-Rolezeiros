# Contrato da API (frontend ↔ backend)

Versão 0 — proposta. Mudanças: abrir PR alterando este arquivo **e** os mocks em
`frontend/public/mock/`, para o front e o back não divergirem.

- Base URL: `http://localhost:8000` (FastAPI). CORS liberado para `http://localhost:5173`.
- Todas as geometrias em **GeoJSON, EPSG:4326** (`[lon, lat]`). Cálculos de distância no backend em
  métrica (SIRGAS 2000 / UTM 23S, EPSG:31983).
- Nomes de campos em `snake_case`, em português.

## Enumerações

| Campo | Valores |
|---|---|
| `natureza` | `A` `B` `C` `D` `E` `F` |
| `prioridade` | `baixa` `media` `alta` `muito_alta` |
| `tipo` (viatura) | `atendimento` (faz prevenção quando livre) · `preventiva` |
| `classe` (faixa) | `1` `2` `3` |
| `modo` (atividade) | `ponto_base` (20 min ponto-base + 40 min patrulha em 1 km) · `entorno_2km` · `entorno_3km` |

---

## `GET /territorio`
Limite da 39ª CIA. `FeatureCollection` com 1 `Polygon` (o próprio `39_cia.geojson`).

## `GET /hexagonos`
`FeatureCollection` de polígonos hexagonais (200 m entre vértices opostos).

```json
{
  "type": "Feature",
  "geometry": { "type": "Polygon", "coordinates": [[[-44.03, -19.86], "..."]] },
  "properties": {
    "id": "h_0123",
    "score": 37,
    "prioridade": "alta",
    "total": 11,
    "por_natureza": { "A": 2, "B": 0, "C": 0, "D": 0, "E": 1, "F": 8 }
  }
}
```

## `GET /ocorrencias?natureza=A,B&hora=20`
Filtros opcionais (`hora` = 0–23). `FeatureCollection` de pontos:
`properties: { id, natureza, data_hora (ISO 8601), hora, hex_id }`.

## `GET /faixas`
As 24 faixas horárias ordenadas pela incidência ponderada.

```json
[{ "hora": 10, "score": 312, "classe": 1, "ranking": 1 }]
```

## `GET /viaturas`
Frota padrão do cenário (até a organização informar a real).

```json
[{ "id": "VTR-01", "nome": "VTR 01", "tipo": "preventiva", "disponivel": true }]
```

## `POST /distribuicao`
Calcula a distribuição para um conjunto de viaturas. É chamado de novo a cada empenho ou liberação.

Request:
```json
{ "viaturas": [{ "id": "VTR-01", "tipo": "preventiva", "disponivel": false }] }
```

Response:
```json
{
  "atribuicoes": { "VTR-02": ["h_0123", "h_0124"], "VTR-03": ["h_0200"] },
  "cartoes": [
    {
      "viatura_id": "VTR-02",
      "faixas": [
        {
          "hora": 10,
          "classe": 1,
          "modo": "ponto_base",
          "hex_ponto_base": "h_0123",
          "raio_m": 1000,
          "area_patrulha": { "type": "Polygon", "coordinates": ["..."] }
        }
      ]
    }
  ],
  "metricas": {
    "cobertura_area_pct": 72.5,
    "cobertura_risco_pct": 91.0,
    "hex_descobertos": ["h_0300"]
  }
}
```

Regras que o backend garante nos `cartoes` (e que o validador deve testar):
- Classe 1 (8 faixas): `modo = ponto_base`; o mesmo `hex_ponto_base` não se repete em faixas
  consecutivas da mesma viatura.
- Classe 2 (8 faixas): 4 com `ponto_base` (mesma regra de alternância) e 4 com `entorno_2km`.
- Classe 3 (8 faixas): `entorno_3km` das quadrículas de maior incidência da faixa; se não houver,
  das quadrículas da Classe 1.
