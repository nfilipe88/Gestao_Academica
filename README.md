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
infraestrutura (deploy automatizado, monitorização), não funcionalidades.
Ver o plano de trabalho em curso mais abaixo.

---

## A correr localmente

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

`GET http://localhost:8000/api/v1/health` confirma que está no ar.
`http://localhost:8000/docs` tem a documentação interativa (Swagger).

Para criar a primeira conta Super Admin: `python seed_super_admin.py`.

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
`npm test` (Vitest) — só o scaffold gerado pelo Angular CLI existe hoje;
a suite real do front-end ainda está por escrever.

## CI

`.github/workflows/ci.yml` corre em cada push/PR para `main`: a suite
de pytest acima (com Postgres efémero) e `ng build` de produção —
precisamente o comando que esteve partido, sem ninguém notar, até este
ser corrigido.

---

## Plano de trabalho em curso

Auditoria honesta feita em 2026-08: o projeto tem uma cobertura
funcional incomum para o estádio em que está, mas não está pronto para
autoatendimento de milhares de escolas sem supervisão da equipa. Fases,
por ordem de dependência:

1. **Rede de segurança** (em curso) — testes automatizados dos
   caminhos críticos + CI a correr em cada push + este README.
2. **Infraestrutura multi-instância** — o limitador de login e o
   agendador da régua de cobrança são hoje in-process/em memória
   (documentado no próprio código); Sentry/métricas; Docker.
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
