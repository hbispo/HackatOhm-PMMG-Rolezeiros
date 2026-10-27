# =====================================================================
# DESAFIO PMMG - backend do patrulhamento preventivo
# =====================================================================
#
# ESTADO ATUAL
#   Pronto:
#   - leitura do JSON de ocorrências e do GeoJSON da área (39ª CIA)
#   - malha hexagonal de 200 m e pontuação por hexágono e por hora
#   - níveis de prioridade dos hexágonos (baixa, média, alta, muito alta)
#   - classes das 24 faixas horárias (classe 1, 2 e 3)
#   - classe Viatura
#   - distribuição das viaturas com equilíbrio de carga
#   - redistribuição estável quando uma viatura fica indisponível
#   - os 3 cenários do desafio rodando no terminal
#   - Cartão-Programa de cada viatura disponível (classes 1, 2 e 3, alternância
#     das quadrículas, plano B da classe 3), com verificação das regras,
#     comparação entre cenários e saída em JSON (cartoes_cenarioN.json)
#   Parâmetros ajustáveis (nas constantes, logo abaixo dos imports):
#   - PESO_COBERTURA (0.3), TOLERANCIA_CARGA (0.25), CORTES_PERCENTIL
#   - frota de teste: QTD_ATENDIMENTO (3) e QTD_PREVENTIVAS (2)
#   - cartão-programa: LIMITAR_A_AREA_DA_VIATURA, QTD_QUADRICULAS_CLASSE3,
#     CANDIDATAS_POR_FAIXA
#
# O QUE FALTA (em ordem)
#   1. Corrigir as lacunas achadas na revisão contra o enunciado
#      - a classificação dos hexágonos (nivel) ainda não influencia a
#        distribuição, que usa a pontuação bruta (o enunciado pede explicar
#        como a classificação influencia a distribuição)
#      - o tipo da viatura (atendimento/preventiva) ainda não faz nada
#      - falta uma métrica de cobertura territorial (% de hexágonos e de pontos
#        a até 1, 2 e 3 km de uma viatura) pros cenários 1 e 2
#      - ocorrências a até ~60 m da borda do polígono: 7 são descartadas e ~45
#        são contadas. Sugestão: gerar a malha sobre a área ampliada em 100 m
#   2. API (FastAPI) pro front-end
#      - endpoints: malha, ocorrências, viaturas, cartões, indisponibilizar e
#        disponibilizar uma viatura
#      - converter os dados de volta pra lat/lon (to_crs 4326), porque o
#        Leaflet não usa metros
#   3. Mapa web (Leaflet)
#      - área, malha, classificação, ocorrências, viaturas, área de cada
#        viatura e a mudança depois que uma viatura sai
#   4. Documentação e entrega
#      - README com critérios, arquitetura e limitações
#      - requirements.txt
#   5. Pendências administrativas (instruções.txt)
#      - inscrição na ação de extensão
#      - repositório PRIVADO no GitHub com README (equipe, integrantes e
#        descrição da solução)
#      - adicionar o coordenador como membro do repositório (usuário: rimsa)
#      - entrar no grupo do WhatsApp
#
# DECISÕES PARA CONFIRMAR COM O COORDENADOR (perguntar no grupo)
#   - frota real do cenário (quantidade e tipos). Hoje o "tipo" da viatura
#     ainda não influencia nada na distribuição
#   - quais 4 das 8 faixas da classe 2 usam ponto-base. Assumi as 4 mais fortes
#     (constante FAIXAS_PONTO_BASE_CLASSE2)
#   - regra de alternância das quadrículas: "só poderá ser escolhida novamente
#     após a seleção de, no mínimo, outra quadrícula distinta" admite mais de
#     uma leitura
#   - se o raio de 1, 2 ou 3 km fica limitado à área da viatura ou pode passar
#     dela
#   - se vale impor um alcance máximo por viatura (no cenário 3 chegou a 3,3 km)
#
# SUPOSIÇÕES ADOTADAS NO CARTÃO-PROGRAMA (confirmar com o coordenador)
#   - quadrícula de destaque de cada faixa = hexágono da área da viatura com
#     mais pontos naquela hora (desempate pela pontuação total)
#   - alternância: nas faixas com ponto-base, o mesmo hexágono não pode ser
#     selecionado em seleções seguidas, e o dia é circular (a última não repete
#     a primeira). Entre as escolhas válidas fica a de maior pontuação
#   - classe 2 sem ponto-base: 2 km em volta do hexágono de maior incidência
#   - classe 3: 3 km em volta dos 3 hexágonos de maior incidência da faixa. Se a
#     área não teve ocorrência nessa hora, usa os destaques da classe 1
#   - a patrulha fica dentro da área da própria viatura. Por isso, nas faixas
#     de 3 km o polígono vira a área inteira dela (LIMITAR_A_AREA_DA_VIATURA)
#   - o ponto-base de 20 min pode ocorrer em qualquer momento da faixa (o
#     cartão não fixa o minuto de início)
#
# OBSERVAÇÕES DOS TESTES
#   - ao retirar uma viatura, as vizinhas absorvem a região e o alcance máximo
#     delas aumenta (custo de priorizar as áreas mais quentes)
#   - o equilíbrio é da carga combinada (ocorrências + área), então a fatia de
#     ocorrências por viatura ainda pode ser desigual
#   - a pontuação por hora de cada hexágono vem de poucas ocorrências (os
#     destaques ficam com 3 a 8 pontos na hora), então a escolha do destaque é
#     sensível a poucos registros
# =====================================================================

import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon

# ---------------------------------------------------------------
# configurações
# ---------------------------------------------------------------
CRS_GEO = "EPSG:4326"       # lat/lon normal
CRS_METROS = "EPSG:31983"   # usado pra medir distância em metros (região de BH)

DIAMETRO_HEX = 200          # metros, de ponta a ponta do hexágono

# peso de cada natureza (A até F)
PESOS = {"A": 4, "B": 5, "C": 1, "D": 1, "E": 2, "F": 3}

# níveis de prioridade dos hexágonos
NOMES_NIVEIS = ["baixa", "média", "alta", "muito alta"]
# percentis de corte, calculados só nos hexágonos que tiveram ocorrência:
# até 50% = baixa | 50-80% = média | 80-95% = alta | acima de 95% = muito alta
CORTES_PERCENTIL = [0.50, 0.80, 0.95]

# faixas horárias: 24 faixas de 1h, divididas em 3 classes de 8 faixas
FAIXAS_POR_CLASSE = 8
# o enunciado diz que 4 das 8 faixas da classe 2 usam ponto-base e as outras 4
# patrulham 2 km, mas não diz quais. Escolhi as 4 mais fortes pro ponto-base
FAIXAS_PONTO_BASE_CLASSE2 = 4

# viaturas do cenário de teste (trocar quando chegar o cenário de verdade)
QTD_ATENDIMENTO = 3   # atendem ocorrências, mas fazem preventivo quando estão livres
QTD_PREVENTIVAS = 2   # só policiamento preventivo

# equilíbrio entre prioridade e cobertura territorial (de 0 a 1):
# 0 = só olha onde tem ocorrência | 1 = só olha a área, divide o mapa igualmente
PESO_COBERTURA = 0.3
SEMENTE = 42          # pra o resultado ser sempre o mesmo

# quanto a carga de uma viatura pode fugir da média (0.25 = 25% a mais ou a menos).
# Quanto menor, mais parecida fica a carga entre as viaturas. None desliga o equilíbrio
TOLERANCIA_CARGA = 0.25

# cartão-programa (regras do enunciado)
PONTO_BASE_MIN = 20       # minutos parado na quadrícula em destaque
PATRULHA_MIN = 40         # minutos patrulhando nas adjacências
RAIO_KM = {"ponto_base": 1, "patrulha_2km": 2, "patrulha_3km": 3}   # raio por tipo de faixa
QTD_QUADRICULAS_CLASSE3 = 3   # quantas quadrículas de maior incidência entram na classe 3
CANDIDATAS_POR_FAIXA = 6      # hexágonos que concorrem ao destaque de cada faixa
# True = a patrulha fica dentro da área da própria viatura (as vizinhas cuidam do resto).
# False = o raio de 1/2/3 km pode passar pra área de outras viaturas
LIMITAR_A_AREA_DA_VIATURA = True

# nomes das colunas depois de ler o json (o latLon vira "latLon.lat" e "latLon.lon")
COL_LAT = "latLon.lat"
COL_LON = "latLon.lon"
COL_DATAHORA = "dataHora"
COL_NATUREZA = "natureza"

FORMATO_DATAHORA = "%d/%m/%Y %H:%M:%S"   # ex: 31/12/2025 20:07:13

PASTA = Path(__file__).parent
PASTA_DADOS = PASTA.parent / "data"     # dados do desafio ficam em /data na raiz do repositório
PASTA_SAIDA = PASTA / "saida"           # cartões gerados pelo script (fora do git)
ARQUIVO = PASTA_DADOS / "ocorrencias.txt"    # json das ocorrências (a extensão é .txt mesmo)
ARQUIVO_AREA = PASTA_DADOS / "39_cia.geojson"  # contorno da área atendida (39ª CIA)


# ---------------------------------------------------------------
# lendo os dados
# ---------------------------------------------------------------
def ler_json(caminho):
    """Lê o json e devolve um DataFrame comum.
    Funciona com lista de registros e também com GeoJSON."""
    with open(caminho, encoding="utf-8") as f:
        dados = json.load(f)

    # GeoJSON: tem "features" e cada uma tem "properties" e "geometry"
    if isinstance(dados, dict) and "features" in dados:
        df = pd.json_normalize([ft["properties"] for ft in dados["features"]])
        # pega lon/lat da geometria, se não vierem nas propriedades
        coords = [ft["geometry"]["coordinates"] for ft in dados["features"]]
        if COL_LON not in df.columns:
            df[COL_LON] = [c[0] for c in coords]
        if COL_LAT not in df.columns:
            df[COL_LAT] = [c[1] for c in coords]
        return df

    # o json tem as chaves "total" e "dados": as ocorrências ficam dentro de "dados".
    # pode ser um bloco só ou uma lista de blocos (páginas), então trato os dois
    blocos = dados if isinstance(dados, list) else [dados]
    registros = []
    for bloco in blocos:
        if isinstance(bloco, dict) and "dados" in bloco:
            conteudo = bloco["dados"]
            if isinstance(conteudo, str):   # às vezes o conteúdo vem como texto json
                conteudo = json.loads(conteudo)
            if isinstance(conteudo, dict):  # dicionário de registros {"1": {...}, ...}
                valores = list(conteudo.values())
                if all(isinstance(v, dict) for v in valores):
                    conteudo = valores
                else:
                    conteudo = [conteudo]
            registros += conteudo
        else:
            registros.append(bloco)

    return pd.json_normalize(registros)


def carregar_ocorrencias(caminho):
    df = ler_json(caminho)
    print("Colunas que vieram no json:", df.columns.tolist())

    # se algum nome estiver errado, mostra o primeiro registro pra eu acertar
    faltando = [c for c in (COL_LAT, COL_LON, COL_DATAHORA, COL_NATUREZA) if c not in df.columns]
    if faltando:
        print("Não achei essas colunas:", faltando)
        print("Primeiro registro:", df.iloc[0].to_dict() if len(df) else "(vazio)")
        raise SystemExit("Acerte COL_LAT, COL_LON, COL_DATAHORA e COL_NATUREZA no começo do arquivo.")

    # garante que lat/lon são números (às vezes vem texto com vírgula)
    for col in (COL_LAT, COL_LON):
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace(",", "."), errors="coerce"
        )

    df = df.dropna(subset=[COL_LAT, COL_LON, COL_NATUREZA]).copy()

    # peso de cada ocorrência
    df["peso"] = df[COL_NATUREZA].astype(str).str.strip().str.upper().map(PESOS)
    df = df.dropna(subset=["peso"])  # tira o que não for A-F

    # data e hora do fato (vem como "31/12/2025 20:07:13")
    quando = pd.to_datetime(df[COL_DATAHORA], format=FORMATO_DATAHORA, errors="coerce")
    df["datahora"] = quando
    df["hora"] = quando.dt.hour   # 0 a 23
    df = df.dropna(subset=["hora"])  # tira registro com data/hora inválida

    # vira GeoDataFrame e já converte pra metros
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[COL_LON], df[COL_LAT]),
        crs=CRS_GEO,
    ).to_crs(CRS_METROS)

    return gdf


def carregar_area(caminho):
    """Lê o GeoJSON da área atendida, converte pra metros e junta tudo
    numa geometria só (caso o arquivo tenha vários polígonos)."""
    area = gpd.read_file(caminho)
    if area.crs is None:
        area = area.set_crs(CRS_GEO)   # GeoJSON sem crs é lat/lon por padrão
    area = area.to_crs(CRS_METROS)
    return area.union_all()


# ---------------------------------------------------------------
# malha de hexágonos
# ---------------------------------------------------------------
def desenha_hexagono(cx, cy, raio):
    angulos = [math.radians(30 + 60 * i) for i in range(6)]
    pontos = [(cx + raio * math.cos(a), cy + raio * math.sin(a)) for a in angulos]
    return Polygon(pontos)


def criar_malha(limites, area=None, margem=200):
    minx, miny, maxx, maxy = limites
    minx -= margem
    miny -= margem
    maxx += margem
    maxy += margem

    raio = DIAMETRO_HEX / 2
    largura = math.sqrt(3) * raio   # largura de cada hexágono
    altura = 1.5 * raio             # distância entre uma linha e outra

    hexagonos = []
    centros = []
    for linha, y in enumerate(np.arange(miny, maxy + altura, altura)):
        # linhas ímpares ficam deslocadas meio hexágono
        desloc = largura / 2 if linha % 2 else 0
        for x in np.arange(minx + desloc, maxx + largura, largura):
            hexagonos.append(desenha_hexagono(x, y, raio))
            centros.append((x, y))

    malha = gpd.GeoDataFrame(
        {"cx": [c[0] for c in centros], "cy": [c[1] for c in centros]},
        geometry=hexagonos,
        crs=CRS_METROS,
    )

    # fica só com os hexágonos que tocam a área atendida
    if area is not None:
        malha = malha[malha.intersects(area)].reset_index(drop=True)

    malha["hex_id"] = range(len(malha))
    return malha


# ---------------------------------------------------------------
# ligando ocorrências aos hexágonos e calculando a pontuação
# ---------------------------------------------------------------
def associar_ocorrencias(ocorrencias, malha):
    juntou = gpd.sjoin(
        ocorrencias, malha[["hex_id", "geometry"]], how="inner", predicate="within"
    )
    return juntou.drop(columns="index_right")


def pontuar_hexagonos(ocorrencias_hex, malha):
    # pontuação total de cada hexágono
    total = ocorrencias_hex.groupby("hex_id")["peso"].sum().rename("score_total")

    # pontuação por hora (colunas h0, h1, ..., h23)
    por_hora = ocorrencias_hex.pivot_table(
        index="hex_id", columns="hora", values="peso", aggfunc="sum", fill_value=0
    )
    por_hora = por_hora.reindex(columns=range(24), fill_value=0).add_prefix("h")

    resultado = malha.merge(total, on="hex_id", how="left")
    resultado = resultado.merge(por_hora, on="hex_id", how="left")

    # hexágono sem ocorrência fica com 0
    colunas = ["score_total"] + list(por_hora.columns)
    resultado[colunas] = resultado[colunas].fillna(0)
    return resultado


def classificar_hexagonos(hexagonos):
    """Dá um nível de prioridade (1 a 4) pra cada hexágono, pela pontuação total."""
    # os cortes usam só os hexágonos com ocorrência. Se contasse os zerados,
    # eles (mais da metade da malha) puxariam todos os cortes pra baixo
    positivos = hexagonos.loc[hexagonos["score_total"] > 0, "score_total"]
    c1, c2, c3 = positivos.quantile(CORTES_PERCENTIL).tolist()

    faixas = [-np.inf, c1, c2, c3, np.inf]
    hexagonos["nivel"] = pd.cut(
        hexagonos["score_total"], bins=faixas, labels=[1, 2, 3, 4]
    ).astype(int)
    hexagonos["prioridade"] = hexagonos["nivel"].map(
        dict(enumerate(NOMES_NIVEIS, start=1))
    )

    print(f"Cortes de pontuação: baixa até {c1:.0f} | média até {c2:.0f} | "
          f"alta até {c3:.0f} | muito alta acima disso")
    return hexagonos


def classificar_faixas_horarias(ocorrencias_hex):
    """Ordena as 24 faixas de 1h pela pontuação das ocorrências e divide em 3 classes.
    Classe 1 = 8 faixas mais fortes, classe 2 = as 8 seguintes, classe 3 = as 8 mais fracas."""
    pontos = ocorrencias_hex.groupby(ocorrencias_hex["hora"].astype(int))["peso"].sum()

    faixas = pontos.reindex(range(24), fill_value=0).rename("pontos")
    faixas = faixas.rename_axis("hora").reset_index()

    # do maior pro menor. Se empatar, a hora mais cedo vem primeiro
    faixas = faixas.sort_values(["pontos", "hora"], ascending=[False, True])
    faixas = faixas.reset_index(drop=True)
    faixas["ranking"] = faixas.index + 1
    faixas["classe"] = faixas.index // FAIXAS_POR_CLASSE + 1

    def modo_da_faixa(linha):
        if linha["classe"] == 1:
            return "ponto_base"            # 20 min na quadrícula + 40 min num raio de 1 km
        if linha["classe"] == 2:
            posicao = linha["ranking"] - FAIXAS_POR_CLASSE   # 1 a 8 dentro da classe 2
            if posicao <= FAIXAS_PONTO_BASE_CLASSE2:
                return "ponto_base"
            return "patrulha_2km"          # patrulha no entorno de até 2 km
        return "patrulha_3km"              # classe 3: patrulha no entorno de até 3 km

    faixas["modo"] = faixas.apply(modo_da_faixa, axis=1)

    print("Faixas horárias (da mais forte pra mais fraca):")
    print(faixas[["ranking", "hora", "pontos", "classe", "modo"]].to_string(index=False))

    # devolve ordenado por hora, fica mais fácil de consultar depois
    return faixas.sort_values("hora").reset_index(drop=True)


# ---------------------------------------------------------------
# viaturas
# ---------------------------------------------------------------
@dataclass
class Viatura:
    id: str
    tipo: str = "atendimento"        # "atendimento" ou "preventiva"
    disponivel: bool = True
    centro: tuple = None             # (x, y) em metros: onde a área dela está centrada
    hex_base: int = None             # hexágono central da área dela
    hexagonos: list = field(default_factory=list)   # hexágonos que ela cobre

    def indisponibilizar(self):
        """Viatura foi empenhada numa ocorrência e saiu do preventivo."""
        self.disponivel = False
        self.centro = None
        self.hex_base = None
        self.hexagonos = []

    def disponibilizar(self):
        self.disponivel = True


def criar_viaturas(qtd_atendimento, qtd_preventivas):
    viaturas = []
    for i in range(qtd_atendimento + qtd_preventivas):
        tipo = "atendimento" if i < qtd_atendimento else "preventiva"
        viaturas.append(Viatura(id=f"VTR-{i + 1:02d}", tipo=tipo))
    return viaturas


def _distancias2(xy, centros):
    """Distância ao quadrado de cada hexágono até cada centro (matriz n x k)."""
    return ((xy[:, None, :] - np.asarray(centros)[None, :, :]) ** 2).sum(axis=2)


def _atribuir(d2, pesos):
    """Decide qual viatura fica com cada hexágono. Por padrão é a mais perto,
    mas se alguma ficar sobrecarregada eu 'encolho' a área dela e aumento a das
    que estão com pouca carga, até ficar dentro da tolerância."""
    k = d2.shape[1]
    rotulos = d2.argmin(axis=1)
    if TOLERANCIA_CARGA is None or k == 1:
        return rotulos

    alvo = pesos.sum() / k
    escala = d2.min(axis=1).mean()
    ajuste = np.zeros(k)
    for _ in range(300):
        carga = np.bincount(rotulos, weights=pesos, minlength=k)
        erro = (carga - alvo) / alvo
        if np.abs(erro).max() <= TOLERANCIA_CARGA:
            break
        ajuste -= 0.05 * escala * erro   # sobrecarregada perde área, a leve ganha
        rotulos = (d2 - ajuste).argmin(axis=1)
    return rotulos


def _kmeans_ponderado(xy, pesos, centros, iteracoes=100):
    """K-means onde cada hexágono conta com o seu peso. Parte dos centros que
    foram passados e devolve os centros finais, os rótulos e o custo."""
    centros = np.array(centros, dtype=float)
    k = len(centros)

    for _ in range(iteracoes):
        rotulos = _atribuir(_distancias2(xy, centros), pesos)
        novos = centros.copy()
        for j in range(k):
            membros = rotulos == j
            if membros.any():
                novos[j] = np.average(xy[membros], axis=0, weights=pesos[membros])
        if np.allclose(novos, centros, rtol=0, atol=1.0):   # mexeu menos de 1 metro
            break
        centros = novos

    d2 = _distancias2(xy, centros)
    rotulos = _atribuir(d2, pesos)
    custo = (pesos * d2[np.arange(len(xy)), rotulos]).sum()
    return centros, rotulos, custo


def _centros_sorteados(xy, pesos, k, rng):
    """Escolha inicial dos centros (estilo k-means++, sorteando pelo peso)."""
    centros = [xy[rng.choice(len(xy), p=pesos / pesos.sum())]]
    while len(centros) < k:
        prob = pesos * _distancias2(xy, centros).min(axis=1)
        centros.append(xy[rng.choice(len(xy), p=prob / prob.sum())])
    return centros


def _ponto_mais_descoberto(xy, pesos, centros):
    """Hexágono que mais 'pede' uma viatura: peso alto e longe dos centros atuais."""
    return xy[(pesos * _distancias2(xy, centros).min(axis=1)).argmax()]


def distribuir_viaturas(hexagonos, viaturas, tentativas=10):
    """Divide a malha em uma área pra cada viatura disponível.
    Cada hexágono pesa: (1 - PESO_COBERTURA) * sua parte das ocorrências
    + PESO_COBERTURA * uma parte igual da área. Assim as áreas de maior prioridade
    ficam menores (mais atenção), mas nenhum canto do mapa fica sem viatura."""
    ativas = [v for v in viaturas if v.disponivel]
    k = len(ativas)
    if k == 0:
        raise ValueError("Nenhuma viatura disponível")

    xy = hexagonos[["cx", "cy"]].to_numpy(float)
    score = hexagonos["score_total"].to_numpy(float)
    pesos = (1 - PESO_COBERTURA) * score / score.sum() + PESO_COBERTURA / len(score)

    conhecidos = [v.centro for v in ativas if v.centro is not None]
    if not conhecidos:
        # primeira distribuição: tenta vários pontos de partida e fica com o melhor
        rng = np.random.default_rng(SEMENTE)
        resultados = [
            _kmeans_ponderado(xy, pesos, _centros_sorteados(xy, pesos, k, rng))
            for _ in range(tentativas)
        ]
        centros, rotulos, _ = min(resultados, key=lambda r: r[2])
    else:
        # já existia distribuição: cada viatura parte de onde estava, assim as áreas
        # mudam pouco. Viatura que está voltando entra no ponto mais descoberto
        existentes = list(conhecidos)
        partida = []
        for v in ativas:
            if v.centro is None:
                novo = _ponto_mais_descoberto(xy, pesos, existentes)
                existentes.append(tuple(novo))
                partida.append(novo)
            else:
                partida.append(v.centro)
        centros, rotulos, _ = _kmeans_ponderado(xy, pesos, partida)

    hexagonos = hexagonos.copy()
    hexagonos["viatura"] = None
    linhas = []
    for j, viatura in enumerate(ativas):
        idx = np.where(rotulos == j)[0]
        # hexágono-base: o da área dela que fica mais perto do centro
        d2 = ((xy[idx] - centros[j]) ** 2).sum(axis=1)
        pos_base = idx[d2.argmin()]
        base = int(hexagonos["hex_id"].iloc[pos_base])

        viatura.centro = (float(centros[j][0]), float(centros[j][1]))
        viatura.hex_base = base
        viatura.hexagonos = hexagonos["hex_id"].iloc[idx].tolist()
        hexagonos.loc[hexagonos.index[idx], "viatura"] = viatura.id

        dist = np.sqrt(((xy[idx] - xy[pos_base]) ** 2).sum(axis=1))
        linhas.append({
            "viatura": viatura.id,
            "tipo": viatura.tipo,
            "hex_base": base,
            "hexagonos": len(idx),
            "pontos": score[idx].sum(),
            "% dos pontos": round(100 * score[idx].sum() / score.sum(), 1),
            "dist_max_km": round(dist.max() / 1000, 2),
        })

    print("Distribuição das viaturas:")
    print(pd.DataFrame(linhas).to_string(index=False))
    return hexagonos


def indisponibilizar_e_redistribuir(hexagonos, viaturas, ids):
    """Tira as viaturas de `ids` do preventivo e redistribui as que sobraram."""
    antes = hexagonos["viatura"].copy()
    descobertos = antes.isin(ids)
    pontos = hexagonos.loc[descobertos, "score_total"].sum()
    total = hexagonos["score_total"].sum()

    for v in viaturas:
        if v.id in ids:
            v.indisponibilizar()

    print(f"Viatura(s) empenhada(s): {', '.join(ids)}")
    print(f"Região que ficou descoberta: {descobertos.sum()} hexágonos, "
          f"{pontos:.0f} pontos ({100 * pontos / total:.1f}% do total)")

    novo = distribuir_viaturas(hexagonos, viaturas)

    mudaram = (novo["viatura"] != antes).sum()
    print(f"Hexágonos que mudaram de viatura: {mudaram} "
          f"({descobertos.sum()} da região descoberta + {mudaram - descobertos.sum()} ajustados nas vizinhas)")
    return novo


# ---------------------------------------------------------------
# cartão-programa
# ---------------------------------------------------------------
def _ganho_por_hexagono(zona, hora):
    """Quanto vale cada hexágono da área nessa faixa. Conta a pontuação da própria
    hora; a pontuação total entra só como desempate (por isso o peso pequeno)."""
    total = zona["score_total"].to_numpy(float)
    return zona[f"h{hora}"].to_numpy(float) + 0.5 * total / (total.sum() + 1)


def _top_candidatos(ganho, qtd):
    return [int(i) for i in np.argsort(-ganho, kind="stable")[:qtd]]


def _escolher_alternando(candidatos, ganhos):
    """candidatos[i] = posições dos hexágonos que concorrem na i-ésima faixa com
    ponto-base (em ordem do dia) e ganhos[i] = quanto vale cada um.
    Escolhe um por faixa somando o maior ganho possível, sem repetir o mesmo hexágono
    em seleções seguidas. A última escolha do dia também não pode ser igual à primeira,
    porque o cartão se repete todo dia."""
    n = len(candidatos)
    if n == 0:
        return []

    def melhor_caminho(fechar_ciclo):
        melhor = None
        for s, inicio in enumerate(candidatos[0]):
            # dp[hexágono] = (melhor soma até aqui, caminho escolhido)
            dp = {inicio: (ganhos[0][s], [inicio])}
            for i in range(1, n):
                novo = {}
                for c, hex_c in enumerate(candidatos[i]):
                    if fechar_ciclo and i == n - 1 and hex_c == inicio:
                        continue
                    opcoes = [v for h, v in dp.items() if h != hex_c]
                    if not opcoes:
                        continue
                    soma, caminho = max(opcoes, key=lambda v: v[0])
                    novo[hex_c] = (soma + ganhos[i][c], caminho + [hex_c])
                dp = novo
                if not dp:
                    break
            for soma, caminho in dp.values():
                if melhor is None or soma > melhor[0]:
                    melhor = (soma, caminho)
        return melhor

    resultado = melhor_caminho(True) or melhor_caminho(False)
    if resultado is None:
        # só sobrou um candidato por faixa, não dá pra alternar
        return [c[int(np.argmax(g))] for c, g in zip(candidatos, ganhos)]
    return resultado[1]


def gerar_cartao(viatura, hexagonos, faixas):
    """Monta o cartão-programa de uma viatura: uma linha pra cada uma das 24 faixas."""
    zona = hexagonos[hexagonos["hex_id"].isin(viatura.hexagonos)].reset_index(drop=True)
    ids = zona["hex_id"].to_numpy()
    xy = zona[["cx", "cy"]].to_numpy(float)
    ids_da_area = set(int(i) for i in ids)

    # universo onde a patrulha pode acontecer
    if LIMITAR_A_AREA_DA_VIATURA:
        univ_ids, univ_xy = ids, xy
    else:
        univ_ids = hexagonos["hex_id"].to_numpy()
        univ_xy = hexagonos[["cx", "cy"]].to_numpy(float)

    def hexagonos_no_raio(posicoes, raio_km):
        perto = np.zeros(len(univ_xy), dtype=bool)
        for pos in posicoes:
            perto |= ((univ_xy - xy[pos]) ** 2).sum(axis=1) <= (raio_km * 1000) ** 2
        return sorted(int(i) for i in univ_ids[perto])

    info = faixas.set_index("hora")
    ganhos = {h: _ganho_por_hexagono(zona, h) for h in range(24)}

    # 1) faixas com ponto-base (classe 1 e as 4 da classe 2): hexágono de destaque,
    #    alternando pra não repetir em seleções seguidas
    horas_pb = [h for h in range(24) if info.loc[h, "modo"] == "ponto_base"]
    candidatos = [_top_candidatos(ganhos[h], CANDIDATAS_POR_FAIXA) for h in horas_pb]
    ganhos_cand = [ganhos[h][c] for h, c in zip(horas_pb, candidatos)]
    destaque_pb = dict(zip(horas_pb, _escolher_alternando(candidatos, ganhos_cand)))

    # destaques da classe 1 (plano B da classe 3)
    destaques_classe1 = []
    for h in horas_pb:
        if info.loc[h, "classe"] == 1 and destaque_pb[h] not in destaques_classe1:
            destaques_classe1.append(destaque_pb[h])

    linhas = []
    for h in range(24):
        modo = info.loc[h, "modo"]
        classe = int(info.loc[h, "classe"])
        score_h = zona[f"h{h}"].to_numpy(float)
        raio = RAIO_KM[modo]
        origem = "maior incidência na faixa"

        if modo == "ponto_base":
            destaque = [destaque_pb[h]]
            ponto_base, patrulha = PONTO_BASE_MIN, PATRULHA_MIN
        elif modo == "patrulha_2km":
            destaque = [int(np.argmax(ganhos[h]))]
            ponto_base, patrulha = 0, 60
        else:
            # classe 3: entorno das quadrículas de maior incidência da faixa.
            # Se a área não teve incidência nessa hora, usa as quadrículas da classe 1
            top = _top_candidatos(ganhos[h], QTD_QUADRICULAS_CLASSE3)
            destaque = [i for i in top if score_h[i] > 0]
            if not destaque:
                destaque = destaques_classe1 or top[:1]
                origem = "quadrículas da classe 1 (sem incidência na faixa)"
            ponto_base, patrulha = 0, 60

        if modo != "patrulha_3km" and score_h[destaque[0]] == 0:
            origem = "maior incidência total da área (sem ocorrência na faixa)"

        area_patrulha = hexagonos_no_raio(destaque, raio)
        n = len(area_patrulha)
        if modo == "ponto_base":
            descricao = (f"Ponto-base de {PONTO_BASE_MIN} min no hexágono {int(ids[destaque[0]])} "
                         f"(em qualquer momento da faixa) + {PATRULHA_MIN} min de patrulha "
                         f"num raio de {raio} km ({n} hexágonos)")
        elif modo == "patrulha_2km":
            descricao = (f"Patrulhamento preventivo no entorno de até {raio} km do hexágono "
                         f"{int(ids[destaque[0]])} ({n} hexágonos)")
        else:
            descricao = (f"Patrulhamento preventivo no entorno de até {raio} km de "
                         f"{len(destaque)} hexágono(s) de destaque ({n} hexágonos)")

        linhas.append({
            "hora": h,
            "faixa": f"{h:02d}:00-{h:02d}:59",
            "classe": classe,
            "modo": modo,
            "raio_km": raio,
            "ponto_base_min": ponto_base,
            "patrulha_min": patrulha,
            "hexagonos_destaque": [int(ids[i]) for i in destaque],
            "pontos_faixa": float(score_h[destaque].sum()),
            "origem_destaque": origem,
            "hexagonos_patrulha": area_patrulha,
            "pct_da_area": round(100 * len(set(area_patrulha) & ids_da_area) / len(zona), 1),
            "descricao": descricao,
        })

    return {
        "viatura": viatura.id,
        "tipo": viatura.tipo,
        "hex_base": viatura.hex_base,
        "qtd_hexagonos_area": len(zona),
        "hexagonos_area": sorted(ids_da_area),
        "faixas": linhas,
    }


def gerar_cartoes(hexagonos, viaturas, faixas):
    """Um cartão pra cada viatura disponível (indexado pelo id da viatura)."""
    return {
        v.id: gerar_cartao(v, hexagonos, faixas)
        for v in viaturas if v.disponivel
    }


def verificar_cartoes(cartoes, viaturas):
    """Confere se os cartões seguem as regras do enunciado. Devolve a lista de problemas."""
    problemas = []
    disponiveis = {v.id for v in viaturas if v.disponivel}
    if set(cartoes) != disponiveis:
        problemas.append("a quantidade de cartões não bate com as viaturas disponíveis")

    for vid, cartao in cartoes.items():
        f = cartao["faixas"]
        area = set(cartao["hexagonos_area"])
        if len(f) != 24:
            problemas.append(f"{vid}: o cartão não tem 24 faixas")
            continue

        c1 = [x for x in f if x["classe"] == 1]
        c2 = [x for x in f if x["classe"] == 2]
        c3 = [x for x in f if x["classe"] == 3]
        if not (len(c1) == len(c2) == len(c3) == FAIXAS_POR_CLASSE):
            problemas.append(f"{vid}: as classes não têm {FAIXAS_POR_CLASSE} faixas cada")
        if any(x["modo"] != "ponto_base" for x in c1):
            problemas.append(f"{vid}: classe 1 com faixa sem ponto-base")
        if sum(x["modo"] == "ponto_base" for x in c2) != FAIXAS_PONTO_BASE_CLASSE2:
            problemas.append(f"{vid}: classe 2 sem {FAIXAS_PONTO_BASE_CLASSE2} faixas de ponto-base")
        if any(x["modo"] not in ("ponto_base", "patrulha_2km") for x in c2):
            problemas.append(f"{vid}: classe 2 com modo inesperado")
        if any(x["modo"] != "patrulha_3km" for x in c3):
            problemas.append(f"{vid}: classe 3 com faixa que não é de 3 km")

        # alternância: o mesmo hexágono não pode ser selecionado em seguida
        # (o dia é circular: depois da última faixa vem a primeira)
        seq = [x["hexagonos_destaque"][0] for x in f if x["modo"] == "ponto_base"]
        if len(set(seq)) > 1:
            for a, b in zip(seq, seq[1:] + seq[:1]):
                if a == b:
                    problemas.append(f"{vid}: hexágono {a} repetido em seleções seguidas")

        for x in f:
            if x["modo"] == "ponto_base" and x["ponto_base_min"] + x["patrulha_min"] != 60:
                problemas.append(f"{vid}: faixa {x['faixa']} com ciclo diferente de 60 min")
            if not set(x["hexagonos_destaque"]) <= area:
                problemas.append(f"{vid}: destaque fora da área na faixa {x['faixa']}")
            if LIMITAR_A_AREA_DA_VIATURA and not set(x["hexagonos_patrulha"]) <= area:
                problemas.append(f"{vid}: patrulha fora da área na faixa {x['faixa']}")
    return problemas


def imprimir_cartao(cartao):
    print(f"\n--- Cartão-Programa {cartao['viatura']} ({cartao['tipo']}) | "
          f"hexágono-base {cartao['hex_base']} | área: {cartao['qtd_hexagonos_area']} hexágonos ---")
    linhas = []
    for f in cartao["faixas"]:
        if f["ponto_base_min"]:
            atividade = f"ponto-base {f['ponto_base_min']}' + patrulha {f['patrulha_min']}'"
        else:
            atividade = f"patrulha {f['patrulha_min']}'"
        linhas.append({
            "faixa": f["faixa"],
            "classe": f["classe"],
            "atividade": atividade,
            "raio_km": f["raio_km"],
            "destaque": ",".join(str(i) for i in f["hexagonos_destaque"]),
            "pontos": f["pontos_faixa"],
            "hex_patrulha": len(f["hexagonos_patrulha"]),
            "% da área": f["pct_da_area"],
        })
    print(pd.DataFrame(linhas).to_string(index=False))


def comparar_cartoes(antes, depois):
    """Mostra o que mudou nos cartões das viaturas que continuaram disponíveis."""
    print("O que mudou nos cartões (de 24 faixas):")
    linhas = []
    for vid, novo in depois.items():
        velho = antes.get(vid)
        if velho is None:
            continue
        pares = list(zip(velho["faixas"], novo["faixas"]))
        linhas.append({
            "viatura": vid,
            "destaque mudou": sum(set(a["hexagonos_destaque"]) != set(b["hexagonos_destaque"]) for a, b in pares),
            "área de patrulha mudou": sum(set(a["hexagonos_patrulha"]) != set(b["hexagonos_patrulha"]) for a, b in pares),
            "hexágonos da área": f"{velho['qtd_hexagonos_area']} -> {novo['qtd_hexagonos_area']}",
        })
    print(pd.DataFrame(linhas).to_string(index=False))
    cancelados = [vid for vid in antes if vid not in depois]
    if cancelados:
        print("Cartões cancelados (viatura indisponível):", ", ".join(cancelados))


def salvar_cartoes(cartoes, caminho):
    """Salva os cartões em JSON (é daqui que o front-end vai ler depois)."""
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(cartoes, f, ensure_ascii=False, indent=2)


def montar_cartoes_do_cenario(nome, hexagonos, viaturas, faixas, anteriores=None, imprimir=False):
    cartoes = gerar_cartoes(hexagonos, viaturas, faixas)
    problemas = verificar_cartoes(cartoes, viaturas)

    print(f"\nCartões-Programa gerados: {len(cartoes)} "
          f"(viaturas disponíveis: {sum(v.disponivel for v in viaturas)})")
    print("Verificação das regras do enunciado:", "OK" if not problemas else problemas)

    if imprimir:
        for cartao in cartoes.values():
            imprimir_cartao(cartao)
    if anteriores:
        comparar_cartoes(anteriores, cartoes)

    PASTA_SAIDA.mkdir(exist_ok=True)
    salvar_cartoes(cartoes, PASTA_SAIDA / f"cartoes_{nome}.json")
    return cartoes


# ---------------------------------------------------------------
# rodando
# ---------------------------------------------------------------
if __name__ == "__main__":
    ocorrencias = carregar_ocorrencias(ARQUIVO)
    area = carregar_area(ARQUIVO_AREA)

    # a malha cobre a área inteira, não só onde teve ocorrência
    malha = criar_malha(area.bounds, area)

    # ocorrência que caiu fora da malha some aqui no sjoin
    ocorrencias_hex = associar_ocorrencias(ocorrencias, malha)
    hexagonos = pontuar_hexagonos(ocorrencias_hex, malha)
    hexagonos = classificar_hexagonos(hexagonos)
    faixas = classificar_faixas_horarias(ocorrencias_hex)

    print("Ocorrências lidas:", len(ocorrencias))
    print("Ocorrências dentro da área:", len(ocorrencias_hex))
    print("Hexágonos na malha:", len(hexagonos))
    print("Hexágonos com ocorrência:", (hexagonos["score_total"] > 0).sum())
    print(hexagonos.nlargest(5, "score_total")[["hex_id", "score_total"]])

    # quantos hexágonos e quantos pontos ficaram em cada nível
    resumo = hexagonos.groupby(["nivel", "prioridade"]).agg(
        hexagonos=("hex_id", "count"), pontos=("score_total", "sum")
    )
    resumo["% dos pontos"] = (100 * resumo["pontos"] / resumo["pontos"].sum()).round(1)
    print(resumo)

    # ---- cenários do desafio ----
    viaturas = criar_viaturas(QTD_ATENDIMENTO, QTD_PREVENTIVAS)

    print("\n=== Cenário 1: todas as viaturas disponíveis ===")
    hexagonos = distribuir_viaturas(hexagonos, viaturas)
    cartoes1 = montar_cartoes_do_cenario("cenario1", hexagonos, viaturas, faixas, imprimir=True)

    print("\n=== Cenário 2: uma viatura indisponível ===")
    hexagonos = indisponibilizar_e_redistribuir(hexagonos, viaturas, ["VTR-02"])
    cartoes2 = montar_cartoes_do_cenario("cenario2", hexagonos, viaturas, faixas, anteriores=cartoes1)

    print("\n=== Cenário 3: duas viaturas indisponíveis ===")
    hexagonos = indisponibilizar_e_redistribuir(hexagonos, viaturas, ["VTR-01"])
    cartoes3 = montar_cartoes_do_cenario("cenario3", hexagonos, viaturas, faixas, anteriores=cartoes2)