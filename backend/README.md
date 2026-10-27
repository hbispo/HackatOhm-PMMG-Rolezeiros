# Backend

Python + Pandas + GeoPandas (Guilherme).

- `HackatOhm.py`: o motor. Malha, classificação, distribuição das viaturas e Cartões-Programa.
  Rodando direto, executa os 3 cenários no terminal e salva os cartões em `saida/` (fora do git).
- `api.py`: camada FastAPI em cima do motor, sem regra de negócio. Guarda a frota em memória e
  converte tudo para GeoJSON em lat/lon. Contrato em [docs/api.md](../docs/api.md).

```bash
# da raiz do repositório
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
backend/.venv/bin/uvicorn api:app --app-dir backend --reload --port 8000   # API
backend/.venv/bin/python backend/HackatOhm.py                              # cenários no terminal
```

Mudou o formato de algum campo no motor? Atualize `docs/api.md` e `frontend/src/types.ts` juntos.
