# Imagem de produção do back-end (FastAPI + Uvicorn).
#
# NOTA HONESTA: o CMD corre `alembic upgrade head` a cada arranque do
# container, antes de subir o servidor — simples e suficiente para uma
# única instância (o caso de docker-compose.yml na raiz do repo). Com
# várias instâncias a arrancar ao mesmo tempo (deploy real,
# autoscaling), migrações concorrentes são um risco real — nessa
# escala, correr `alembic upgrade head` como um passo de release
# separado, ANTES de subir instâncias novas, é a forma correta; isto
# fica documentado aqui, não escondido.
FROM python:3.13-slim

WORKDIR /app

# libpq-dev/gcc só para o caso de alguma dependência precisar de
# compilar (a maioria já vem em wheel pré-compilado) — mantém a imagem
# final ainda assim pequena por não instalar mais do que isto.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Utilizador não-root — a app só precisa de rede (Postgres/Redis), não
# de privilégios de root para nada.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).status==200 else 1)"

CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000"]
