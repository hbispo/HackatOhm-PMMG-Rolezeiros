# Contrato da API (frontend ↔ backend)

Versão 0.1. A API é uma camada fina ([backend/api.py](../backend/api.py)) em cima do motor do
Guilherme ([backend/HackatOhm.py](../backend/HackatOhm.py)), e os nomes dos campos são os dele.
Mudou algum campo? Atualize este arquivo e `frontend/src/types.ts` no mesmo PR.

- Base: `http://localhost:8000`. No front, o Vite redireciona `/api/*` para lá (sem CORS).
- Swagger gerado pelo FastAPI: `http://localhost:8000/docs`.
- Geometrias em **GeoJSON, EPSG:4326** (`[lon, lat]`). O motor calcula em metros (EPSG:31983)
  e a API converte na saída.
- `hex_id` é **inteiro**.
- A frota fica **em memória no servidor**: a redistribuição parte de onde cada viatura estava,
  para as áreas mudarem pouco. Reiniciar o servidor volta ao cenário 1.

## Enumerações

| Campo | Valores |
|---|---|
| `natureza` | `A` `B` `C` `D` `E` `F` (pesos 4, 5, 1, 1, 2, 3) |
| `nivel` / `prioridade` | `1` `baixa` · `2` `média` · `3` `alta` · `4` `muito alta` |
| `tipo` (viatura) | `atendimento` · `preventiva` |
| `classe` (faixa) | `1` `2` `3` |
| `modo` (faixa) | `ponto_base` (20 min parado + 40 min de patrulha em 1 km) · `patrulha_2km` · `patrulha_3km` |

---

## Dados fixos

### `GET /territorio`
`FeatureCollection` com o polígono da 39ª CIA.

### `GET /hexagonos`
`FeatureCollection` com os 1.069 hexágonos da malha (200 m entre vértices opostos).

```json
"properties": {
  "hex_id": 344,
  "score_total": 37.0,
  "nivel": 4,
  "prioridade": "muito alta",
  "total": 11,
  "por_natureza": { "A": 2, "B": 0, "C": 0, "D": 0, "E": 1, "F": 8 },
  "por_hora": [0, 0, 3, "... 24 valores: pontuação ponderada em cada hora"]
}
```

### `GET /ocorrencias`
`FeatureCollection` de pontos. `hex_id` é `null` para as 7 ocorrências que caem fora da malha.

```json
"properties": { "id": "85d04607235a", "natureza": "E", "data_hora": "2025-12-31T20:07:13", "hora": 20, "hex_id": 344 }
```

### `GET /faixas`
As 24 faixas horárias, em ordem de hora.

```json
[{ "hora": 10, "pontos": 312.0, "ranking": 1, "classe": 1, "modo": "ponto_base" }]
```

---

## Estado da frota

Todas as rotas abaixo devolvem o mesmo objeto **Estado**:

```json
{
  "cenario": 2,
  "viaturas": [{ "id": "VTR-01", "tipo": "atendimento", "disponivel": true, "hex_base": 940 }],
  "atribuicoes": { "VTR-01": [12, 13, 40] },
  "cartoes": { "VTR-01": { "...": "Cartão, ver abaixo" } },
  "carga": [{ "viatura": "VTR-01", "hexagonos": 244, "pontos": 1148.0, "pct_pontos": 23.7, "dist_max_km": 2.44 }],
  "problemas": [],
  "mudanca": {
    "acao": "empenhar",
    "viaturas": ["VTR-02"],
    "hex_descobertos": [500, 501],
    "pct_pontos_descobertos": 26.7,
    "hex_mudaram": [500, 501, 620]
  }
}
```

- `atribuicoes` e `cartoes` só têm viaturas disponíveis. `hex_base` é `null` nas empenhadas.
- `carga`: hexágonos, pontos e alcance (distância do hexágono-base ao hexágono mais longe) de cada viatura.
- `problemas`: saída de `verificar_cartoes()`. Lista vazia quer dizer que as regras do edital foram cumpridas.
- `mudanca`: o que a última ação mudou. É `null` no cenário 1.
  - `hex_descobertos`: área que era das viaturas empenhadas (vazia ao liberar).
  - `hex_mudaram`: hexágonos que trocaram de viatura (descobertos + ajustes nas vizinhas).

### `GET /estado`
Estado atual.

### `POST /viaturas/{id}/empenhar`
Tira a viatura do preventivo e redistribui as restantes.
`404` se a viatura não existe; `409` se já está empenhada ou se é a última disponível.

### `POST /viaturas/{id}/liberar`
A viatura volta ao preventivo, entrando pelo ponto mais descoberto. `409` se já está disponível.

### `POST /cenarios/{n}`
Os cenários do edital, a partir da frota completa (3 de atendimento + 2 preventivas):

| n | Viaturas empenhadas |
|---|---|
| 1 | nenhuma |
| 2 | VTR-02 |
| 3 | VTR-02 e VTR-01, de uma vez |

No cenário 3 a `mudanca` compara com a frota completa. O script do Guilherme empenha uma
viatura de cada vez, então os números podem diferir um pouco da saída dele no terminal.

---

## Cartão-Programa

Um por viatura disponível, com as 24 faixas em ordem de hora.

```json
{
  "viatura": "VTR-01",
  "tipo": "atendimento",
  "hex_base": 941,
  "qtd_hexagonos_area": 226,
  "hexagonos_area": [12, 13],
  "faixas": [
    {
      "hora": 7,
      "faixa": "07:00-07:59",
      "classe": 1,
      "modo": "ponto_base",
      "raio_km": 1,
      "ponto_base_min": 20,
      "patrulha_min": 40,
      "hexagonos_destaque": [1005],
      "pontos_faixa": 6.0,
      "origem_destaque": "maior incidência na faixa",
      "hexagonos_patrulha": [980, 1005, 1006],
      "pct_da_area": 35.4,
      "descricao": "Ponto-base de 20 min no hexágono 1005 (em qualquer momento da faixa) + 40 min de patrulha num raio de 1 km (80 hexágonos)"
    }
  ]
}
```

Regras garantidas pelo motor (e checadas em `problemas`):
- Classe 1: 8 faixas, todas `ponto_base`.
- Classe 2: 8 faixas, sendo 4 `ponto_base` (as 4 de maior incidência) e 4 `patrulha_2km`.
- Classe 3: 8 faixas `patrulha_3km`, em volta das quadrículas de maior incidência da faixa; sem
  incidência, em volta dos destaques da Classe 1.
- O mesmo hexágono de ponto-base nunca é escolhido em seleções seguidas, e o dia é circular.
- Com `LIMITAR_A_AREA_DA_VIATURA = True`, a patrulha fica dentro da área da própria viatura.

## Ainda não existe

- Métrica de cobertura territorial (% de hexágonos e de pontos a até 1, 2 e 3 km de uma viatura).
  Está na lista de pendências do `HackatOhm.py`.
