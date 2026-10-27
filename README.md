# Rolezeiros — HackatOhm PMMG 2026

**Policiamento preventivo orientado por dados** · 39ª CIA PM / 18º BPM

## Equipe

| Integrante | Papel |
|---|---|
| Henrique Bispo dos Santos | Frontend, gestão do repositório |
| Guilherme Augusto Reis Correa | Backend (Python, Pandas, GeoPandas) |
| Thaís Lorrane Oliveira | Pesquisa, documentação, apresentação |
| Vinícius Januário Luciano Lopes | Dados e algoritmo |
| Arthur Nicholls Mendes | Dados e algoritmo |

## A solução

Protótipo de apoio à decisão que transforma o histórico de ocorrências de 2025 em uma
estratégia de patrulhamento preventivo que se adapta à disponibilidade das viaturas:

1. **Malha hexagonal** de 200 m (1.069 hexágonos) sobre o limite da 39ª CIA. Cada ocorrência
   é associada ao seu hexágono.
2. **Classificação de prioridade** (baixa, média, alta, muito alta) pela incidência ponderada
   (pesos A=4, B=5, C=1, D=1, E=2, F=3).
3. **Distribuição das viaturas** por k-means ponderado: 70% prioridade (a pontuação com peso maior
   para os níveis altos) e 30% território, com carga menor para as viaturas de atendimento, que
   podem ser empenhadas a qualquer momento.
4. **Cartões-Programa**, um por viatura: 24 faixas horárias em 3 classes, conforme as regras do desafio.
5. **Redistribuição dinâmica**: quando uma ou mais viaturas são empenhadas, o sistema mostra o
   impacto na cobertura (% dos hexágonos e dos pontos a até 1, 2 e 3 km de uma viatura) e
   recalcula as áreas e os cartões das viaturas restantes.

Com as 5 viaturas, 82% da pontuação histórica fica a até 1 km de uma viatura. Com 2 viaturas
empenhadas, 98% ainda fica a até 2 km. Detalhes em [docs/solucao.md](docs/solucao.md).

## Estrutura

```
frontend/   Vue 3 + Vite + TypeScript + Leaflet (mapa, painel de viaturas, cartões)
backend/    HackatOhm.py (motor: malha, classificação, distribuição, cartões) + api.py (FastAPI)
data/       ocorrencias.txt (1.605 ocorrências) e 39_cia.geojson (limite da CIA)
docs/       contrato da API, metodologia, arquitetura, limitações, evolução
research/   fichamentos da pesquisa acadêmica
notebooks/  análise exploratória
```

## Como executar

Precisa de Python 3.9+ e Node 20+. Rode os comandos a partir da raiz do repositório.

### 1. Backend (porta 8000)
```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn api:app --app-dir backend --reload --port 8000
```
Documentação interativa da API: http://localhost:8000/docs.
Para ver os 3 cenários só no terminal: `backend/.venv/bin/python backend/HackatOhm.py`.

### 2. Frontend (porta 5173)
```bash
cd frontend
npm install
npm run dev
```
O Vite redireciona `/api` para o backend na porta 8000, então os dois precisam estar rodando.

## Tecnologias
Somente código aberto: Vue, Vite, Leaflet, OpenStreetMap, Python, Pandas, GeoPandas, Shapely, FastAPI.

## Documentação
- **[Documentação da solução](docs/solucao.md)**: descrição, arquitetura, tecnologias, metodologia,
  critérios, execução, limitações e evolução
- [Contrato da API](docs/api.md)
- [Guia da equipe e divisão de tarefas](docs/equipe.md)

## Licença
[MIT](LICENSE)
