# Gestão Académica

SaaS multi-tenant de gestão escolar: académico (cursos/turmas/matrículas),
diário de classe, financeiro (contratos, faturas, PayPal), CRM de
captação, RH de professores, comunicações, documentos em PDF, horários,
BI com risco de evasão, LMS com exames, billing SaaS com período de
teste, mapa de permissões editável e tabela de propinas.

- **Back-end**: FastAPI (Python) + PostgreSQL, com isolamento entre
  escolas garantido a duas camadas — filtro por `tenant_id` no código
  E Row-Level Security real no Postgres (ver `back_end/app/database/session.py`).
- **Front-end**: Angular 21 (standalone, zoneless) + NgRx, Tailwind.

## Estado do projeto

Este é um produto em desenvolvimento ativo, funcionalmente amplo mas
**ainda não pronto para produção sem supervisão** — falta sobretudo
infraestrutura, não funcionalidades. Ver o plano de trabalho em curso
mais abaixo.

---

## A correr tudo com Docker (a via mais rápida)

```bash
cp back_end/.env.example back_end/.env   # não é lido pelo docker-compose,
                                          # mas mantém o ficheiro presente para outras ferramentas
docker compose up --build
```

Sobe Postgres (com os roles/RLS já criados automaticamente), Redis,
back-end, front-end (Angular SSR) e um nginx como ponto de entrada
único — **http://localhost** já com tudo ligado (a app Angular chama a
API com caminhos relativos, o nginx encaminha `/api/*` para o back-end
e o resto para o front-end, por isso não há CORS nenhum a negociar
neste caminho).

Não é uma receita de produção tal e qual (passwords fixas no
`docker-compose.yml`, sem TLS) — ver `docker-compose.yml` e
`deploy/nginx.conf` para os detalhes, e a secção de variáveis de
ambiente abaixo para o que muda num deploy real.

---

## A correr localmente (sem Docker)

### Pré-requisitos
- Python 3.13+ e um venv
- Node 22+
- PostgreSQL 17 (local ou remoto)

### Back-end

```bash
cd back_end
python -m venv venv
./venv/Scripts/activate        # Windows (Git Bash: source venv/Scripts/activate)
pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env           # preencher com os valores reais
```

Criar os dois roles Postgres usados para o Row-Level Security (uma vez
por base de dados) — ligado como superuser:

```bash
psql -U postgres -d academic_db -f scripts/criar_roles_rls.sql
```

Aplicar as migrações e arrancar:

```bash
alembic upgrade head
python -m uvicorn main:app --reload --port 8000
```

`GET http://localhost:8000/api/v1/health` confirma que está no ar E que
consegue mesmo falar com a base de dados (não só que o processo está vivo).
`http://localhost:8000/docs` tem a documentação interativa (Swagger).

Para criar a primeira conta Super Admin: `python seed_super_admin.py`.

**Redis (`REDIS_URL`) e Sentry (`SENTRY_DSN`) são opcionais** — em
branco, o back-end funciona da mesma forma, mas com duas limitações só
seguras para UMA instância: o limitador de tentativas de login conta
em memória local (cada instância à parte, um atacante distribuído
entre várias nunca bate no limite) e o agendador da régua de cobrança
não tem lock partilhado (com mais de uma instância, cada uma dispara o
job à mesma hora, duplicando e-mails). Ver `.env.example` para os
detalhes de cada um.

**Storage de ficheiros (`S3_BUCKET`) — sem isto, cai para disco local**,
só correto para UMA instância (cada instância teria o seu próprio
disco, e um redeploy apaga tudo) — ver `app/core/storage.py`. Para
correr localmente sem depender de uma conta AWS, um MinIO isolado (sem
subir o `docker-compose.yml` inteiro) resolve:

```bash
docker run -d --name gacademic-minio \
  -e MINIO_ROOT_USER=minio_admin -e MINIO_ROOT_PASSWORD=minio_dev_apenas \
  -p 9000:9000 -p 9001:9001 -v gacademic_minio_data:/data \
  quay.io/minio/minio:latest server /data --console-address ":9001"

# criar o bucket uma única vez:
docker run --rm --network host --entrypoint /bin/sh quay.io/minio/mc:latest -c \
  "mc alias set local http://localhost:9000 minio_admin minio_dev_apenas && mc mb -p local/gestao-academica"
```

Depois, em `.env`: `S3_BUCKET=gestao-academica`, `S3_ENDPOINT_URL=http://localhost:9000`,
`S3_ACCESS_KEY=minio_admin`, `S3_SECRET_KEY=minio_dev_apenas` (mesmas
credenciais já usadas pelo `docker-compose.yml`). Consola web do MinIO
em `http://localhost:9001`. Em produção, isto é antes um bucket AWS
S3/equivalente gerido — a imagem oficial `minio/minio` no Docker Hub
pode levar a "pull access denied" por limite de pulls anónimos; `quay.io/minio/minio`
é o mesmo projeto, espelhado, sem esse limite.

### Front-end

```bash
cd gacademic
npm install
npm start        # http://localhost:4200, aponta para o back-end em :8000
```

Build de produção: `npx ng build` — gera `dist/gacademic/{browser,server}`.

---

## Testes

### Back-end (pytest, contra Postgres real — não mocks)

RLS só se testa mesmo contra um Postgres real; por isso a suite usa uma
base de dados **separada** da de desenvolvimento (`academic_db_test`),
nunca a que tem dados reais/manuais.

```bash
cd back_end
python scripts/criar_db_teste.py      # uma vez só, cria a BD de teste + grants
cp .env.test.example .env.test        # preencher com as mesmas passwords de app_tenant/app_sistema do .env

# aplicar as migrações à base de teste (ver .env.test para os valores):
DATABASE_URL_MIGRACOES=<...academic_db_test> alembic upgrade head

pytest -v
```

O que já está coberto (ver `back_end/tests/`):
- **Isolamento RLS entre escolas** — inclui um teste que consulta a
  base de dados diretamente, sem filtro de `tenant_id` na query, para
  provar que é o próprio Postgres a bloquear, não só o código da app.
- Login, RBAC (perfil errado é recusado) e o limitador de tentativas
  de login (anti força-bruta).
- O fluxo de negócio principal ponta a ponta: Curso → Série → Turma →
  Aluno → Matrícula → Contrato Financeiro → Faturas geradas
  automaticamente.

Isto é o núcleo, não a cobertura completa — os módulos de CRM, LMS, BI,
documentos/PDF e o webhook de pagamento ainda não têm testes
automatizados.

### Front-end
`npm test` (Vitest, via `ng test`) — cobre hoje só o arranque da app
(`App`, `src/app/app.spec.ts`): cria sem sessão guardada, e restaura a
sessão a partir do `localStorage` ao arrancar. O scaffold original do
Angular CLI (`imports: [App]`, à procura de um `<h1>` que nunca existiu
neste projeto) nunca tinha sido atualizado — falhava com `NG0201: No
provider found for Store` assim que se corria `ng test` a sério, e por
isso nunca esteve ligado ao CI. Cobertura ainda mínima — guardas de
rota, componentes de feature e stores NgRx ainda não têm testes
próprios.

## CI

`.github/workflows/ci.yml` corre em cada push/PR para `main`:
- a suite de pytest acima, duas vezes (com Postgres efémero) — uma sem
  Redis (fallback em memória) e outra com Redis real, para os dois
  caminhos do limitador de login/lock do scheduler ficarem cobertos;
- `ng test`/`ng build` de produção — o `ng build` foi precisamente o
  comando que esteve partido, sem ninguém notar, até este ser
  corrigido; o `ng test` só passou a correr em CI depois de corrigido
  (ver secção "Testes" acima);
- build das duas imagens Docker (`docker/build-push-action`, sem
  publicar) — para um `Dockerfile` partido também deixar de poder
  passar despercebido.

---

## Backup e Restauro

Backup diário da base de dados (`pg_dump`, formato `-Fc`), disparado
automaticamente às 03:00 pelo agendador interno (`back_end/app/core/scheduler.py`)
e enviado para o mesmo storage S3-compatível já usado para
logótipos/anexos (`back_end/app/core/storage.py`, `S3_BUCKET` em
`.env`). **Sem `S3_BUCKET` configurado, o backup cai para disco local**
— só correto em desenvolvimento; em produção isso anula a proteção,
porque um backup que vive no mesmo servidor que protege não sobrevive
à perda desse servidor. Retenção configurável via
`BACKUP_RETENCAO_DIAS` (14 dias por omissão) — backups mais antigos são
apagados automaticamente a seguir a cada backup novo.

`pg_dump`/`pg_restore` não vêm no `PATH` por omissão numa instalação
Windows do Postgres — apontar `PG_DUMP_PATH`/`PG_RESTORE_PATH` no `.env`
para o executável completo se for esse o caso (ver `.env.example`).

**Disparar um backup manualmente** (testar a configuração sem esperar
pelas 03:00, ou tirar um extra antes de uma operação arriscada):

```bash
cd back_end
python scripts/backup_manual.py
```

**Restaurar um backup.** Por omissão, o script recusa-se a restaurar
por cima de `academic_db`/`academic_db_test` sem `--confirmar-alvo-existente`
— o uso normal é sempre para uma base de dados nova, criada só para o
ensaio:

```bash
python scripts/restaurar_db.py --chave _backups/academic_db_20260920_073646.dump \
    --bd-destino academic_db_drill --criar-bd
```

Restauro real (disaster recovery, por cima de uma base já existente):

```bash
python scripts/restaurar_db.py --chave _backups/<...>.dump \
    --bd-destino academic_db --confirmar-alvo-existente
```

**Procedimento testado** (2026-09-20): backup real de `academic_db`
(76 tabelas, 3644 linhas) → restauro numa base de ensaio nova
(`academic_db_restore_drill`) → contagem de tabelas e linhas confirmada
idêntica à origem → base de ensaio removida. Um backup nunca restaurado
não é um backup, é uma promessa — por isso este passo faz parte do
próprio trabalho de implementar a funcionalidade, não fica para depois.

---

## Plano de trabalho em curso

Auditoria honesta feita em 2026-08: o projeto tem uma cobertura
funcional incomum para o estádio em que está, mas não está pronto para
autoatendimento de milhares de escolas sem supervisão da equipa. Fases,
por ordem de dependência:

1. ✅ **Rede de segurança** — testes automatizados dos caminhos
   críticos + CI a correr em cada push + este README.
2. ✅ **Infraestrutura multi-instância** — limitador de login e lock
   do scheduler passam a Redis quando `REDIS_URL` está definida (com
   fallback documentado para memória local); Sentry opcional
   (`SENTRY_DSN`); CORS deixa de estar fixo em `localhost:4200`
   (`CORS_ALLOWED_ORIGINS`); `/api/v1/health` passa a confirmar também
   a ligação à base de dados; Docker (`Dockerfile` em cada serviço +
   `docker-compose.yml` com nginx como ponto de entrada único) —
   verificado ponta a ponta: registo → login → dashboard, através do
   stack completo em contentores. Métricas/dashboards de uptime em si
   ainda não existem (Sentry cobre erros, não latência/disponibilidade).
3. **Pagamentos e conformidade fiscal** — sair do sandbox do PayPal;
   moeda/via de pagamento locais consoante o mercado; faturação com
   validade fiscal.
4. **Armazenamento e comunicação** — upload de ficheiros (LMS,
   documentos, fotos); canal WhatsApp/SMS.
5. **Segurança de sessão** — refresh/revogação de JWT, 2FA no Super
   Admin.
6. **Legal** — política de privacidade e retenção de dados (a
   plataforma trata dados de menores).
7. **Escala** — teste de carga contra volumes realistas antes de
   qualquer promessa comercial de "milhares de escolas".
