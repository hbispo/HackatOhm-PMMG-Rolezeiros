# Guia da equipe e divisão de tarefas

Prazo: **1 semana**. Cada tarefa vira uma *issue* no GitHub com responsável e label
(`front`, `back`, `pesquisa`, `docs`, `dados`). Quem não usa Git pode mandar o texto para o Henrique,
que sobe no repositório.

## Quem faz o quê

| Pessoa | Frente |
|---|---|
| Henrique | Frontend (Vue + Leaflet), repositório, integração |
| Guilherme | Backend (Python, Pandas, GeoPandas): malha, classificação, distribuição, cartões |
| Thaís | Pesquisa acadêmica, perguntas à organização, documentação, apresentação |
| Vinicius | _A definir conforme o perfil_: dados/algoritmo **ou** pesquisa de OR + QA |
| Artur | _A definir conforme o perfil_: dados/algoritmo **ou** documentação + QA |

## Tarefas

### 1. Pesquisa acadêmica (Thaís; Vinicius/Artur podem ajudar)
Objetivo: embasar cada decisão do algoritmo com evidência, para usar na apresentação e na documentação.
Para cada estudo, um fichamento curto em `research/` usando o [modelo](../research/_modelo.md).

Ponto de partida (confirmar as referências completas ao fichar):
- **Hot spots policing**: Sherman & Weisburd (1995, Minneapolis) e as revisões sistemáticas
  de Braga et al. (Campbell Collaboration). O policiamento focado em pontos quentes reduz o crime?
- **Koper Curve** (Koper, 1995): a permanência ideal num hot spot fica em torno de 10 a 15 min.
  Isso embasa o ponto-base de 20 min e a alternância de quadrículas exigidos no edital.
- **Deslocamento × difusão de benefícios** (Weisburd et al., 2006): o crime "migra" para a área vizinha?
  Isso justifica a patrulha nas adjacências (raio de 1 km).
- **Philadelphia Foot Patrol Experiment** (Ratcliffe et al., 2011).
- **Modelos de cobertura da pesquisa operacional**: Maximal Covering Location Problem (Church &
  ReVelle, 1974), p-medianas, modelo Hypercube (Larson, 1974) para viaturas.
- **Predictive policing**: Mohler et al. (2015), Risk Terrain Modeling (Caplan & Kennedy).
- **Críticas e limitações**: viés nos dados de ocorrência, *feedback loop* do policiamento preditivo,
  questões éticas. Isso alimenta a seção de limitações.

Entregável: 6 a 10 fichamentos e um resumo de uma página, "o que a literatura diz e como usamos".

### 2. Perguntas para a organização (Thaís, no grupo do WhatsApp)
- Quantas viaturas e de quais tipos haverá no cenário de teste?
- Há 79 ocorrências exatamente no mesmo ponto (-19.8804683, -44.037681), e outros pontos com 45 e 29.
  É geocodificação padrão (ex.: endereço de uma unidade)? Devemos descartar esses pontos?
- 415 ocorrências têm hora cheia (hh:00:00). A hora é estimada?
- 71 ocorrências caem fora do limite da 39ª CIA. Devemos considerá-las?
- Os hexágonos devem ser recortados no limite da CIA ou podem extrapolar?
- Existe um formato esperado ou um modelo do Cartão-Programa?

### 3. Conteúdo do Cartão-Programa (Thaís)
Pensar como o policial que recebe o cartão: o que precisa estar nele, em que ordem, o que é
supérfluo. Um rascunho em papel (foto) ou no Figma já basta; o Henrique transforma em tela e PDF.

### 4. Análise exploratória dos dados (Vinicius/Artur, se programarem)
Notebook em `notebooks/`, importando os módulos do `backend/`:
- distribuição por hora, dia da semana e mês;
- ranking das 24 faixas pela incidência ponderada, que define as Classes 1, 2 e 3;
- tratamento dos pontos duplicados, da hora cheia e das ocorrências fora do limite;
- gráficos que entrem direto na apresentação.

### 5. Métricas e baseline (Vinicius/Artur, se programarem)
- % de área coberta e % do risco ponderado coberto, com e sem viaturas empenhadas.
- Comparar nossa estratégia com uma ingênua (todas as viaturas nos N hexágonos mais quentes),
  para mostrar numericamente o equilíbrio entre prioridade e cobertura.

### 6. Validador das regras do Cartão-Programa (Vinicius/Artur, se programarem)
Testes automáticos (pytest) sobre a saída do `POST /distribuicao`:
- 24 faixas por cartão: 8 da Classe 1, 8 da Classe 2 e 8 da Classe 3;
- a mesma quadrícula de ponto-base nunca aparece em faixas consecutivas (incluindo 23h → 0h);
- na Classe 2, exatamente 4 faixas de ponto-base e 4 de entorno de 2 km;
- o número de cartões é igual ao número de viaturas disponíveis.

### 7. QA e roteiro da demo (todos, no dia 6)
Percorrer os 3 cenários do edital e conferir cada item exigido (veja abaixo).

### 8. Documentação e apresentação (Thaís + quem estiver livre)
A documentação obrigatória fica em `docs/`: descrição da solução, arquitetura, tecnologias,
metodologia, critérios, instruções de execução, limitações e possibilidades de evolução.
A apresentação deve cobrir os **9 critérios de avaliação**, um a um.

## Checklist do edital

- [ ] README com nome da equipe, integrantes e descrição; `rimsa` como colaborador
- [ ] Mapa: área, hexágonos, classificação, ocorrências, viaturas, área de cada viatura, mudança após empenho
- [ ] Cenário 1 (todas disponíveis), cenário 2 (uma empenhada), cenário 3 (várias empenhadas)
- [ ] Cartões-Programa: um por viatura disponível, 24 faixas, regras das 3 classes
- [ ] Explicação do algoritmo e dos critérios
- [ ] Documentação: solução, arquitetura, tecnologias, metodologia, execução, limitações, evolução
- [ ] Somente tecnologias open source

## Cronograma

| Dia | Entrega |
|---|---|
| 1 | Repositório, contrato da API, issues criadas, perguntas enviadas à organização |
| 2–3 | Front com mock · back: malha + classificação · fichamentos |
| 4 | Distribuição + cartões integrados ao front |
| 5 | Cenários 2 e 3, métricas antes/depois, impressão dos cartões |
| 6 | Documentação, QA, ensaio da demo |
| 7 | Folga para bugs e apresentação |
