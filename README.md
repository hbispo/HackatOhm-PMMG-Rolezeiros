# Rolezeiros — Hackathon PMMG 2026

**Policiamento preventivo orientado por dados** · 39ª CIA PM / 18º BPM

## Equipe

| Integrante | Papel |
|---|---|
| Henrique _(sobrenome)_ | Frontend, gestão do repositório |
| Guilherme _(sobrenome)_ | Backend (Python, Pandas, GeoPandas) |
| Thaís _(sobrenome)_ | Pesquisa, documentação, apresentação |
| Vinicius _(sobrenome)_ | Dados e algoritmo |
| Artur _(sobrenome)_ | Dados e algoritmo |

> ⚠️ Completar com os nomes completos (exigência do edital, item 2a).

## A solução

Protótipo de apoio à decisão que transforma o histórico de ocorrências de 2025 em uma
estratégia de patrulhamento preventivo que se adapta à disponibilidade das viaturas:

1. **Malha hexagonal** de 200 m (lado de 100 m) recortada no limite da 39ª CIA. Cada ocorrência
   é associada ao seu hexágono.
2. **Classificação de prioridade** (baixa, média, alta, muito alta) pela incidência ponderada
   (pesos A=4, B=5, C=1, D=1, E=2, F=3).
3. **Distribuição das viaturas**, equilibrando prioridade e cobertura territorial.
4. **Cartões-Programa**, um por viatura: 24 faixas horárias em 3 classes, conforme as regras do desafio.
5. **Redistribuição dinâmica**: quando uma ou mais viaturas são empenhadas, o sistema mostra o
   impacto na cobertura e recalcula as áreas e os cartões das viaturas restantes.

## Estrutura

```
frontend/   Vue 3 + Vite + TypeScript + Leaflet (mapa, painel de viaturas, cartões)
backend/    Python + Pandas + GeoPandas (+ FastAPI): malha, classificação, distribuição
data/       ocorrencias.txt (1.605 ocorrências) e 39_cia.geojson (limite da CIA)
docs/       contrato da API, metodologia, arquitetura, limitações, evolução
research/   fichamentos da pesquisa acadêmica
notebooks/  análise exploratória
```

## Como executar

### Frontend
```bash
cd frontend
npm install
npm run dev
```
Por padrão o front usa os **mocks** em `frontend/public/mock/`. Para apontar para o backend:
`VITE_API_URL=http://localhost:8000 npm run dev`.

### Backend
_A definir pelo Guilherme._

## Tecnologias
Somente código aberto: Vue, Vite, Leaflet, OpenStreetMap, Python, Pandas, GeoPandas, Shapely, FastAPI.

## Documentação
- [Contrato da API](docs/api.md)
- [Guia da equipe e divisão de tarefas](docs/equipe.md)
- Metodologia, limitações e evolução: _em `docs/`, a escrever_

## Licença
[MIT](LICENSE)
