# =====================================================================
# API (FastAPI) do patrulhamento preventivo
# =====================================================================
#
# Camada fina em cima do HackatOhm.py: aqui não tem regra de negócio, só
# carregamento, estado da frota em memória e conversão pra JSON em lat/lon.
# Contrato em docs/api.md.
#
# Rodar (da raiz do repositório):
#   backend/.venv/bin/uvicorn api:app --app-dir backend --reload --port 8000
# Documentação interativa: http://localhost:8000/docs
# =====================================================================

import json
import threading

import geopandas as gpd
import numpy as np
from fastapi import FastAPI, HTTPException

import HackatOhm as motor

app = FastAPI(title="HackatOhm PMMG · Rolezeiros", version="0.1.0")

# o estado da frota é compartilhado e o FastAPI roda rotas síncronas em threads
_trava = threading.Lock()


# ---------------------------------------------------------------
# dados fixos (carregados uma vez, na subida do servidor)
# ---------------------------------------------------------------
def _carregar_base():
    ocorrencias = motor.carregar_ocorrencias(motor.ARQUIVO)
    area = motor.carregar_area(motor.ARQUIVO_AREA)
    malha = motor.criar_malha(area.bounds, area)
    ocorrencias_hex = motor.associar_ocorrencias(ocorrencias, malha)
    hexagonos = motor.pontuar_hexagonos(ocorrencias_hex, malha)
    hexagonos = motor.classificar_hexagonos(hexagonos)
    faixas = motor.classificar_faixas_horarias(ocorrencias_hex)

    # contagem por natureza, só pra exibir no mapa
    por_natureza = (
        ocorrencias_hex.groupby(["hex_id", motor.COL_NATUREZA]).size()
        .unstack(fill_value=0).reindex(columns=list(motor.PESOS), fill_value=0)
    )
    hexagonos = hexagonos.merge(por_natureza, left_on="hex_id", right_index=True, how="left")
    hexagonos[list(motor.PESOS)] = hexagonos[list(motor.PESOS)].fillna(0).astype(int)

    # left join: a ocorrência fora da malha também aparece no mapa (com hex_id null)
    ocorrencias = gpd.sjoin(
        ocorrencias, malha[["hex_id", "geometry"]], how="left", predicate="within"
    ).drop(columns="index_right")

    return area, hexagonos, ocorrencias, faixas


def _feature_collection(gdf, colunas):
    return json.loads(gdf[colunas + ["geometry"]].to_crs(motor.CRS_GEO).to_json(drop_id=True))


AREA, HEX_BASE, OCORRENCIAS, FAIXAS = _carregar_base()
XY = dict(zip(HEX_BASE["hex_id"], HEX_BASE[["cx", "cy"]].to_numpy(float)))

TERRITORIO = _feature_collection(gpd.GeoDataFrame(geometry=[AREA], crs=motor.CRS_METROS), [])

_hex = HEX_BASE.copy()
_hex["total"] = _hex[list(motor.PESOS)].sum(axis=1)
_hex["por_natureza"] = _hex[list(motor.PESOS)].to_dict("records")
_hex["por_hora"] = _hex[[f"h{h}" for h in range(24)]].astype(float).values.tolist()
HEXAGONOS = _feature_collection(
    _hex, ["hex_id", "score_total", "nivel", "prioridade", "total", "por_natureza", "por_hora"]
)

_oc = OCORRENCIAS.copy()
_oc["id"] = _oc["id"].str[:12]
_oc["data_hora"] = _oc["datahora"].dt.strftime("%Y-%m-%dT%H:%M:%S")
_oc["hora"] = _oc["hora"].astype(int)
_oc["hex_id"] = _oc["hex_id"].astype("Int64")
OCORRENCIAS_GEOJSON = _feature_collection(_oc, ["id", motor.COL_NATUREZA, "data_hora", "hora", "hex_id"])

FAIXAS_JSON = [
    {"hora": int(f.hora), "pontos": float(f.pontos), "ranking": int(f.ranking),
     "classe": int(f.classe), "modo": f.modo}
    for f in FAIXAS.itertuples()
]


# ---------------------------------------------------------------
# estado da frota
# ---------------------------------------------------------------
class Estado:
    def __init__(self):
        self.cenario = 1
        self.viaturas = []
        self.hexagonos = None
        self.cartoes = {}
        self.mudanca = None

    def reiniciar(self):
        """Volta pro cenário 1: frota completa, distribuição do zero."""
        self.viaturas = motor.criar_viaturas(motor.QTD_ATENDIMENTO, motor.QTD_PREVENTIVAS)
        self.hexagonos = motor.distribuir_viaturas(HEX_BASE, self.viaturas)
        self.cartoes = motor.gerar_cartoes(self.hexagonos, self.viaturas, FAIXAS)
        self.cenario = 1
        self.mudanca = None

    def atribuicoes(self):
        return {
            v.id: [int(h) for h in v.hexagonos]
            for v in self.viaturas if v.disponivel
        }

    def _aplicar(self, acao, ids, funcao):
        """Roda uma mudança na frota e registra o que mudou no mapa."""
        antes = dict(zip(self.hexagonos["hex_id"], self.hexagonos["viatura"]))
        self.hexagonos = funcao()
        self.cartoes = motor.gerar_cartoes(self.hexagonos, self.viaturas, FAIXAS)
        depois = dict(zip(self.hexagonos["hex_id"], self.hexagonos["viatura"]))

        descobertos = [int(h) for h, v in antes.items() if v in ids] if acao == "empenhar" else []
        pontos = HEX_BASE.set_index("hex_id")["score_total"]
        self.mudanca = {
            "acao": acao,
            "viaturas": ids,
            "hex_descobertos": descobertos,
            "pct_pontos_descobertos": round(100 * float(pontos[descobertos].sum()) / float(pontos.sum()), 1),
            "hex_mudaram": [int(h) for h in depois if depois[h] != antes.get(h)],
        }

    def empenhar(self, ids):
        self._aplicar("empenhar", ids, lambda: motor.indisponibilizar_e_redistribuir(
            self.hexagonos, self.viaturas, ids))

    def liberar(self, vid):
        def funcao():
            next(v for v in self.viaturas if v.id == vid).disponibilizar()
            return motor.distribuir_viaturas(self.hexagonos, self.viaturas)
        self._aplicar("liberar", [vid], funcao)

    def carga(self):
        """Mesma tabela que o HackatOhm.py imprime na distribuição."""
        score = HEX_BASE.set_index("hex_id")["score_total"]
        total = float(score.sum())
        linhas = []
        for v in self.viaturas:
            if not v.disponivel:
                continue
            pts = float(score[v.hexagonos].sum())
            base = XY[v.hex_base]
            alcance = max(float(np.hypot(*(XY[h] - base))) for h in v.hexagonos)
            linhas.append({
                "viatura": v.id,
                "hexagonos": len(v.hexagonos),
                "pontos": pts,
                "pct_pontos": round(100 * pts / total, 1),
                "dist_max_km": round(alcance / 1000, 2),
            })
        return linhas

    def json(self):
        return {
            "cenario": self.cenario,
            "viaturas": [
                {"id": v.id, "tipo": v.tipo, "disponivel": v.disponivel,
                 "hex_base": None if v.hex_base is None else int(v.hex_base)}
                for v in self.viaturas
            ],
            "atribuicoes": self.atribuicoes(),
            "cartoes": self.cartoes,
            "carga": self.carga(),
            "problemas": motor.verificar_cartoes(self.cartoes, self.viaturas),
            "mudanca": self.mudanca,
        }


estado = Estado()
estado.reiniciar()


def _viatura(vid):
    v = next((v for v in estado.viaturas if v.id == vid), None)
    if v is None:
        raise HTTPException(404, f"Viatura {vid} não existe")
    return v


# ---------------------------------------------------------------
# rotas
# ---------------------------------------------------------------
@app.get("/territorio")
def territorio():
    return TERRITORIO


@app.get("/hexagonos")
def hexagonos():
    return HEXAGONOS


@app.get("/ocorrencias")
def ocorrencias():
    return OCORRENCIAS_GEOJSON


@app.get("/faixas")
def faixas():
    return FAIXAS_JSON


@app.get("/estado")
def ver_estado():
    with _trava:
        return estado.json()


@app.post("/viaturas/{vid}/empenhar")
def empenhar(vid: str):
    with _trava:
        v = _viatura(vid)
        if not v.disponivel:
            raise HTTPException(409, f"{vid} já está empenhada")
        if sum(x.disponivel for x in estado.viaturas) == 1:
            raise HTTPException(409, "Não dá pra empenhar a última viatura disponível")
        estado.empenhar([vid])
        return estado.json()


@app.post("/viaturas/{vid}/liberar")
def liberar(vid: str):
    with _trava:
        v = _viatura(vid)
        if v.disponivel:
            raise HTTPException(409, f"{vid} já está disponível")
        estado.liberar(vid)
        return estado.json()


@app.post("/cenarios/{n}")
def cenario(n: int):
    """Os 3 cenários do edital, iguais aos do HackatOhm.py. O "antes" da
    mudança é sempre a frota completa (cenário 1)."""
    if n not in (1, 2, 3):
        raise HTTPException(404, "Cenários: 1, 2 ou 3")
    with _trava:
        estado.reiniciar()
        if n >= 2:
            ids = ["VTR-02"] if n == 2 else ["VTR-02", "VTR-01"]
            estado.empenhar(ids)
        estado.cenario = n
        return estado.json()
