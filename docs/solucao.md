# Documentação da solução — Equipe Rolezeiros

HackatOhm PMMG 2026 · Policiamento preventivo orientado por dados · 39ª CIA PM / 18º BPM

Este documento cobre a documentação mínima pedida no edital: descrição, arquitetura,
tecnologias, metodologia, critérios, execução, limitações e evolução.

## 1. Descrição da solução

Protótipo de apoio à decisão que transforma as 1.605 ocorrências de 2025 da 39ª CIA em uma
estratégia de patrulhamento preventivo que se adapta às viaturas disponíveis.

A aplicação web mostra:
- **Mapa:** o território, a malha de hexágonos, a classificação de prioridade, as ocorrências, as
  viaturas e a área de cada uma.
- **Cartões-Programa:** um por viatura disponível, com as 24 faixas horárias. Ao clicar numa
  faixa, o mapa mostra a área de patrulha e a quadrícula de destaque de cada viatura naquela hora.
- **Demonstração dinâmica:** os botões *Empenhar* e *Liberar* (ou os atalhos dos cenários 1, 2 e 3)
  recalculam a distribuição. O mapa destaca o que mudou e o painel mostra a cobertura antes e
  depois, além da verificação automática das regras do edital.
- **Como funciona:** botão no topo com o resumo da metodologia.

## 2. Arquitetura

```
data/ (ocorrencias.txt, 39_cia.geojson)
   │
   ▼
backend/HackatOhm.py   motor: malha → pontuação → classificação → distribuição → cartões → verificação
   │  (funções Python, sem estado)
   ▼
backend/api.py         FastAPI: guarda a frota em memória, converte para GeoJSON lat/lon
   │  HTTP/JSON (contrato em docs/api.md)
   ▼
frontend/              Vue 3 + Leaflet: mapa, painel de viaturas e cobertura, cartões
```

- O **motor** pode rodar sozinho no terminal (`python backend/HackatOhm.py`): executa os 3 cenários
  e salva os cartões em JSON.
- A **API** carrega os dados uma vez na subida. Cada ação (empenhar, liberar, cenário) chama o
  motor e devolve o estado completo: viaturas, áreas, cartões, carga, cobertura, mudança e
  problemas. Uma ação leva cerca de 50 ms.
- O **front** é uma SPA que conversa com a API pelo proxy do Vite (`/api` → porta 8000).

## 3. Tecnologias utilizadas

Todas de código aberto:

| Camada | Tecnologias |
|---|---|
| Motor | Python 3.9+, Pandas, NumPy, GeoPandas, Shapely |
| API | FastAPI, Uvicorn |
| Front | Vue 3, Pinia, TypeScript, Vite, Leaflet |
| Mapa base | OpenStreetMap |

## 4. Metodologia

### 4.1 Malha hexagonal
A área é convertida para metros (SIRGAS 2000 / UTM 23S, EPSG:31983) e coberta por hexágonos de
200 m entre vértices opostos (lado de 100 m). Ficam os **1.069 hexágonos** que tocam o polígono da
CIA. Cada ocorrência é associada ao seu hexágono por *spatial join*: 1.598 das 1.605 caem na malha
(veja as limitações).

### 4.2 Pontuação e classificação dos hexágonos
Cada ocorrência soma o peso da natureza (A=4, B=5, C=1, D=1, E=2, F=3). O hexágono acumula a
pontuação total e a pontuação de cada uma das 24 horas.

A prioridade usa **percentis calculados só nos hexágonos com ocorrência**. Se os zerados entrassem,
eles seriam mais da metade da malha e puxariam todos os cortes para baixo:

| Nível | Percentil | Fator na distribuição |
|---|---|---|
| Baixa | até 50% (e hexágonos sem ocorrência) | 1,0 |
| Média | 50% a 80% | 1,25 |
| Alta | 80% a 95% | 1,5 |
| Muito alta | acima de 95% | 2,0 |

### 4.3 Classes das faixas horárias
As 24 faixas de 1 hora são ordenadas pela pontuação total das ocorrências naquela hora. As 8
maiores formam a **Classe 1**, as 8 seguintes a **Classe 2** e as 8 menores a **Classe 3**. Na
Classe 2, as 4 faixas de maior incidência usam ponto-base e as outras 4, patrulha em 2 km.

### 4.4 Distribuição das viaturas
Usamos um **k-means ponderado com equilíbrio de carga**:

1. **Peso de cada hexágono:**
   `peso = 0,7 × (pontuação × fator do nível) / total + 0,3 × 1 / nº de hexágonos`.
   A primeira parcela é a **prioridade**; é por ela que a classificação orienta as viaturas, porque
   os hexágonos de nível alto pesam mais que a soma bruta das ocorrências e atraem as viaturas. A
   segunda parcela é o **território**: todo hexágono vale alguma coisa, então nenhuma região fica
   sem viatura. O equilíbrio é controlado por `PESO_COBERTURA = 0,3`.
2. **Agrupamento:** os hexágonos são agrupados em *k* áreas (k = viaturas disponíveis),
   minimizando a distância ponderada até o centro de cada área. A primeira distribuição testa 10
   pontos de partida (estilo k-means++) e fica com o melhor, com semente fixa para ser reproduzível.
3. **Equilíbrio de carga pelo tipo de viatura:** cada viatura tem uma carga-alvo proporcional à
   capacidade do seu tipo. A de **atendimento** pode ser empenhada a qualquer momento e fica com
   **75%** da carga de uma **preventiva**. Se alguma área foge mais de 25% do alvo, as fronteiras
   são ajustadas: a área sobrecarregada encolhe e a leve cresce.
4. **Hexágono-base:** o hexágono de cada área mais perto do seu centro.

Comparamos variantes com as mesmas métricas de cobertura (seção 5). A combinação **fator de nível
+ capacidade por tipo** teve a melhor cobertura a 1 km nos cenários 1 e 3 e ficou praticamente
igual à versão sem esses ajustes no cenário 2 (64,5% contra 65,1% dos pontos).

### 4.5 Cartão-Programa
Para cada viatura e cada faixa:
- **Quadrícula de destaque:** o hexágono da área da viatura com mais pontos naquela hora (a
  pontuação total desempata).
- **Classe 1 e as 4 faixas de ponto-base da Classe 2:** ponto-base de 20 min na quadrícula de
  destaque, em qualquer momento da faixa, + 40 min de patrulha num raio de 1 km. A escolha das
  quadrículas é feita por programação dinâmica: maximiza a pontuação total do dia sem repetir a
  mesma quadrícula em seleções seguidas. O dia é tratado como circular (a última faixa não repete a
  primeira).
- **Outras 4 faixas da Classe 2:** patrulha no entorno de 2 km da quadrícula de maior incidência.
- **Classe 3:** patrulha no entorno de 3 km das 3 quadrículas de maior incidência da faixa. Se a
  área não teve ocorrência naquela hora, usa as quadrículas da Classe 1.
- A patrulha fica **dentro da área da própria viatura**; as vizinhas cuidam do resto.

Cada cartão traz identificação, tipo, hexágono-base, área, e por faixa: classe, atividade, tempos,
raio, quadrículas de destaque, hexágonos a patrulhar, % da área coberta e uma descrição em texto.

### 4.6 Redistribuição dinâmica
Ao empenhar uma viatura, o sistema:
1. marca a viatura como indisponível e a retira da estratégia;
2. identifica a região afetada (os hexágonos que eram dela) e a fatia de pontos que estava lá;
3. redistribui as restantes **a partir de onde cada uma estava**;
4. regenera os cartões das viaturas restantes;
5. mede a nova cobertura e compara com a anterior;
6. roda a verificação automática das regras.

Ao liberar, a viatura volta pelo ponto mais descoberto do mapa.

## 5. Critérios utilizados e resultados

**Cobertura territorial:** % dos hexágonos e % dos pontos cujo centro está a até 1, 2 e 3 km do
hexágono-base de alguma viatura disponível.

| Cenário | Viaturas | Até 1 km (hex / pontos) | Até 2 km | Até 3 km |
|---|---|---|---|---|
| 1 · todas disponíveis | 5 | 50,5% / 81,8% | 96,6% / 99,6% | 100% / 100% |
| 2 · VTR-02 empenhada | 4 | 42,0% / 64,5% | 92,4% / 99,5% | 99,7% / 100% |
| 3 · VTR-02 e VTR-01 empenhadas | 3 | 31,9% / 49,8% | 88,3% / 98,4% | 98,8% / 100% |

- Com as 5 viaturas, **82% da pontuação** fica a até 1 km de uma viatura e praticamente todo o
  território fica a até 2 km.
- No cenário 2, a área da VTR-02 tinha 84 hexágonos e 18% dos pontos. Depois da redistribuição,
  **99,5% dos pontos** continuam a até 2 km de uma viatura.
- No cenário 3, com 40% menos viaturas, a estratégia ainda cobre **98,4% dos pontos a até 2 km**.

**Regras do Cartão-Programa:** verificadas automaticamente a cada mudança (`verificar_cartoes`):
- 24 faixas por cartão, divididas 8/8/8 entre as classes;
- Classe 1 só com ponto-base; Classe 2 com 4 ponto-base + 4 de 2 km; Classe 3 só com 3 km;
- ciclo de 60 min nas faixas de ponto-base;
- sem quadrícula repetida em seleções seguidas;
- destaques e patrulha dentro da área da viatura;
- um cartão por viatura disponível.

A verificação passa nos 3 cenários e em todas as sequências de empenhar e liberar que testamos.

## 6. Instruções para execução

Requisitos: Python 3.9+ e Node 20+. A partir da raiz do repositório:

```bash
# backend (porta 8000)
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn api:app --app-dir backend --reload --port 8000

# frontend (porta 5173), em outro terminal
cd frontend
npm install
npm run dev
```

Abra http://localhost:5173. A documentação interativa da API fica em http://localhost:8000/docs.
Para rodar só o motor no terminal: `backend/.venv/bin/python backend/HackatOhm.py`.

## 7. Limitações identificadas

- **Frota de teste:** a organização não informou a frota real. Usamos 3 viaturas de atendimento e
  2 preventivas (`QTD_ATENDIMENTO` e `QTD_PREVENTIVAS` no `HackatOhm.py`).
- **Qualidade dos dados:**
  - 79 ocorrências estão exatamente no mesmo ponto, e outros pontos se repetem 45 e 29 vezes.
    Provavelmente é geocodificação padrão, e isso infla alguns hexágonos.
  - 415 ocorrências têm hora cheia (hh:00:00), o que sugere hora estimada.
  - 7 ocorrências a até ~60 m da borda ficam fora da malha. Gerar a malha sobre a área ampliada em
    100 m resolveria.
- **Poucos registros por hora:** as quadrículas de destaque de cada faixa têm de 3 a 8 pontos
  naquela hora, então a escolha é sensível a poucos registros.
- **Estabilidade × cobertura:** a redistribuição parte das posições anteriores, mas o reequilíbrio
  pode mudar boa parte do mapa. No cenário 3, 641 hexágonos trocam de viatura. Limitar o
  movimento das viaturas mudaria menos hexágonos, mas, nos nossos testes, piorou a cobertura a
  1 km de ~50% para ~39% dos pontos e fez uma viatura chegar a 5 km do seu hexágono-base. Ficamos
  com a cobertura.
- **Cobertura por distância em linha reta** até o hexágono-base, sem malha viária nem tempo de
  deslocamento.
- **Interpretações a confirmar com a organização:**
  - quais 4 faixas da Classe 2 usam ponto-base (usamos as 4 de maior incidência);
  - a leitura da regra de alternância das quadrículas;
  - se o raio de patrulha pode passar da área da própria viatura;
  - se deve haver um alcance máximo por viatura (hoje chega a 3,5 km).
- **Distribuição sem horário:** as áreas são as mesmas nas 24 horas; só os cartões variam por faixa.
- **Estado em memória:** reiniciar a API volta ao cenário 1. Não há usuários nem persistência
  (é uma prova de conceito).

## 8. Possibilidades de evolução

- **Distribuição por turno:** áreas diferentes para cada classe de faixa horária, usando a
  pontuação por hora que o motor já calcula.
- **Malha viária:** distância e tempo de deslocamento pelas ruas do OpenStreetMap (OSMnx), no lugar
  da linha reta, para a cobertura e para as rotas de patrulha.
- **Rotas no cartão:** sequência de deslocamento entre as quadrículas.
- **Otimização exata:** comparar com um modelo de máxima cobertura (MCLP) ou p-medianas resolvido
  com um solver aberto (OR-Tools, PuLP), usando a mesma métrica de cobertura.
- **Peso temporal:** dar mais peso a ocorrências recentes e testar a previsão em meses separados
  (treinar em jan–set, avaliar em out–dez).
- **Tratamento dos pontos duplicados**, depois de a organização confirmar a origem deles.
- **Empenho com duração:** simular a viatura voltando automaticamente depois de um tempo médio de
  atendimento.
- **Exportar os cartões em PDF** e integrar com o despacho em tempo real.
