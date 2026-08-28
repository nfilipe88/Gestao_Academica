# Imagem de produção do front-end — build multi-stage: compila com
# Node, mas a imagem final só leva o resultado do build (server.mjs +
# os ficheiros estáticos), nunca o node_modules de desenvolvimento nem
# o código-fonte.
FROM node:22-slim AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npx ng build

FROM node:22-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=4000
# Proteção SSRF do Angular SSR (recusa pedidos cujo cabeçalho Host não
# esteja nesta lista) — inclui o próprio healthcheck abaixo, que fala
# com o container em localhost:4000 sem passar pelo nginx. Um deploy
# real deve sobrepor isto (ver docker-compose.yml) com o domínio
# público verdadeiro, nunca confiar só neste valor.
ENV NG_ALLOWED_HOSTS=localhost:4000

# server.mjs (ver dist/gacademic/server/server.mjs) resolve a pasta de
# ficheiros estáticos como "../browser" relativo à sua própria
# localização — as duas pastas têm de ficar exatamente como o build as
# gerou, uma ao lado da outra.
COPY --from=build /app/dist/gacademic/server ./server
COPY --from=build /app/dist/gacademic/browser ./browser

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 4000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD node -e "fetch('http://localhost:4000/').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"

CMD ["node", "server/server.mjs"]
