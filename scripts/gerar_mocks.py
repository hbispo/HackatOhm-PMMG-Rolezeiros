"""Gera os mocks do frontend (frontend/public/mock/) a partir de data/.

Python puro, sem GeoPandas: é só para o front trabalhar enquanto o backend não fica pronto.
A malha usa projeção equiretangular local, que é suficiente na escala de uma companhia.
Uso: python3 scripts/gerar_mocks.py
"""
import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DADOS = RAIZ / "data"
SAIDA = RAIZ / "frontend" / "public" / "mock"

PESOS = {"A": 4, "B": 5, "C": 1, "D": 1, "E": 2, "F": 3}
LADO_M = 100  # 200 m entre vértices opostos

territorio = json.loads((DADOS / "39_cia.geojson").read_text())
anel = territorio["features"][0]["geometry"]["coordinates"][0]
ocorrencias = json.loads((DADOS / "ocorrencias.txt").read_text())[0]["dados"]

lon0 = sum(p[0] for p in anel) / len(anel)
lat0 = sum(p[1] for p in anel) / len(anel)
M_LAT = 111_320
M_LON = 111_320 * math.cos(math.radians(lat0))


def para_m(lon, lat):
    return (lon - lon0) * M_LON, (lat - lat0) * M_LAT


def para_ll(x, y):
    return round(lon0 + x / M_LON, 7), round(lat0 + y / M_LAT, 7)


def dentro(x, y, poligono):
    c = False
    j = len(poligono) - 1
    for i in range(len(poligono)):
        xi, yi = poligono[i]
        xj, yj = poligono[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


anel_m = [para_m(*p) for p in anel]
xs, ys = [p[0] for p in anel_m], [p[1] for p in anel_m]

# Hexágonos "pointy-top" em coordenadas axiais (q, r).
W = math.sqrt(3) * LADO_M


def centro(q, r):
    return W * (q + r / 2), 1.5 * LADO_M * r


def hex_de(x, y):
    q = (math.sqrt(3) / 3 * x - y / 3) / LADO_M
    r = (2 / 3 * y) / LADO_M
    s = -q - r
    rq, rr, rs = round(q), round(r), round(s)
    dq, dr, ds = abs(rq - q), abs(rr - r), abs(rs - s)
    if dq > dr and dq > ds:
        rq = -rr - rs
    elif dr > ds:
        rr = -rq - rs
    return rq, rr


def vertices(q, r):
    cx, cy = centro(q, r)
    pts = [para_ll(cx + LADO_M * math.cos(math.radians(60 * i - 30)),
                   cy + LADO_M * math.sin(math.radians(60 * i - 30))) for i in range(6)]
    return [list(p) for p in pts + pts[:1]]


rmin, rmax = int(min(ys) / (1.5 * LADO_M)) - 2, int(max(ys) / (1.5 * LADO_M)) + 2
celulas = {}
for r in range(rmin, rmax + 1):
    for q in range(int(min(xs) / W) - abs(r) - 2, int(max(xs) / W) + abs(r) + 2):
        if dentro(*centro(q, r), anel_m):
            celulas[(q, r)] = f"h_{len(celulas):04d}"

contagem = defaultdict(Counter)
pontos = []
faixa_score = Counter()
for o in ocorrencias:
    lon, lat = o["latLon"]["lon"], o["latLon"]["lat"]
    chave = hex_de(*para_m(lon, lat))
    hid = celulas.get(chave)
    dh = datetime.strptime(o["dataHora"], "%d/%m/%Y %H:%M:%S")
    faixa_score[dh.hour] += PESOS[o["natureza"]]
    if hid:
        contagem[hid][o["natureza"]] += 1
    pontos.append({
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"id": o["id"][:12], "natureza": o["natureza"],
                       "data_hora": dh.isoformat(), "hora": dh.hour, "hex_id": hid},
    })

scores = {hid: sum(PESOS[n] * c for n, c in contagem[hid].items()) for hid in celulas.values()}
positivos = sorted(s for s in scores.values() if s > 0)


def quantil(p):
    return positivos[min(len(positivos) - 1, int(p * len(positivos)))]


q50, q80, q95 = quantil(0.5), quantil(0.8), quantil(0.95)


def prioridade(s):
    if s >= q95:
        return "muito_alta"
    if s >= q80:
        return "alta"
    if s >= q50:
        return "media"
    return "baixa"


hexagonos = {"type": "FeatureCollection", "features": [
    {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [vertices(q, r)]},
     "properties": {"id": hid, "score": scores[hid], "prioridade": prioridade(scores[hid]),
                    "total": sum(contagem[hid].values()),
                    "por_natureza": {n: contagem[hid][n] for n in PESOS}}}
    for (q, r), hid in celulas.items()]}

ranking = sorted(range(24), key=lambda h: -faixa_score[h])
faixas = [{"hora": h, "score": faixa_score[h], "classe": ranking.index(h) // 8 + 1,
           "ranking": ranking.index(h) + 1} for h in range(24)]

viaturas = [{"id": f"VTR-{i:02d}", "nome": f"VTR {i:02d}",
             "tipo": "atendimento" if i <= 2 else "preventiva", "disponivel": True}
            for i in range(1, 6)]

SAIDA.mkdir(parents=True, exist_ok=True)
for nome, conteudo in {
    "territorio.json": territorio,
    "hexagonos.json": hexagonos,
    "ocorrencias.json": {"type": "FeatureCollection", "features": pontos},
    "faixas.json": faixas,
    "viaturas.json": viaturas,
}.items():
    (SAIDA / nome).write_text(json.dumps(conteudo, ensure_ascii=False, separators=(",", ":")))

fora = sum(1 for p in pontos if p["properties"]["hex_id"] is None)
print(f"{len(celulas)} hexágonos, {len(pontos)} ocorrências ({fora} fora da malha)")
print("prioridades:", Counter(f["properties"]["prioridade"] for f in hexagonos["features"]))
print("classe 1:", sorted(f["hora"] for f in faixas if f["classe"] == 1))
