# Checklist do `.env` de produção

Serve para preparar o `back_end/.env` **do servidor de produção** (nunca o de desenvolvimento) e
para confirmar cada ponto antes de abrir a primeira escola. Complementa `RUNBOOK.md` e o "Parecer
go/no-go" de `PLANO_PRODUCAO.md`. Comentários completos de cada variável: `back_end/.env.example`.

Depois de preencher, corre o verificador (não imprime valores, só o estado de cada regra):

```bash
cd back_end
python scripts/verificar_env_producao.py
```

## 0. Regras gerais

- [ ] O `.env` de produção é um ficheiro **novo**, criado no servidor. Não se copia o de desenvolvimento.
- [ ] O `.env` **nunca** vai para o git (já está no `.gitignore`) nem para chats/tickets.
- [ ] **Todos os segredos de produção são novos.** As chaves do ambiente de desenvolvimento (passwords
      do Postgres, PayPal sandbox, Anthropic, reCAPTCHA, JWT) apareceram em ecrãs e logs de trabalho —
      trata-as como comprometidas e **não** as reutilizes em produção.
- [ ] O back-end **não** corre com `--reload`: depois de alterar o `.env`, reiniciar o processo
      (ver `RUNBOOK.md`, secção 4).
- [ ] Permissões do ficheiro restritas ao utilizador que corre o serviço (`chmod 600 .env` em Linux).

## 1. Bloqueadores — sem isto NÃO se abre a primeira escola

| ✔ | Variável | O que pôr | Como confirmar |
|---|---|---|---|
| [ ] | `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL` (+ `SMTP_FROM_NAME`, `SMTP_USE_TLS=true`) | Conta SMTP real (o e-mail de **ativação de conta** só existe por e-mail: sem SMTP nenhuma escola nova entra). Domínio com SPF/DKIM para não cair em spam. | Registar uma escola de teste e receber o e-mail de ativação numa caixa real. O log **não** pode dizer `SMTP não configurado`. |
| [ ] | `JWT_SECRET_KEY` | Valor aleatório longo, **exclusivo de produção**: `python -c "import secrets; print(secrets.token_urlsafe(64))"`. A app arranca com qualquer valor (inclusive o placeholder do `.env.example`), por isso esta verificação é humana. | O verificador acusa placeholders/valores curtos. Trocar este valor invalida todas as sessões abertas. |
| [ ] | `DATABASE_URL`, `DATABASE_URL_SISTEMA`, `DATABASE_URL_MIGRACOES` | Três roles distintos (`app_tenant` sem BYPASSRLS, `app_sistema` com BYPASSRLS, `postgres`/superuser só para migrações), com **passwords fortes e novas**, apontando para o Postgres de produção. Criar os roles com `scripts/criar_roles_rls.sql` **antes** de correr `alembic upgrade head`. | `GET /api/v1/health` = 200. Teste de isolamento: `pytest tests/test_rls_isolamento.py` contra uma base de teste com os mesmos roles. |
| [ ] | `S3_BUCKET`, `S3_ENDPOINT_URL` (vazio se AWS), `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` | Bucket **fora** do servidor da base de dados, com credenciais só para esse bucket. Sem isto os backups e os ficheiros ficam em disco local e um redeploy/perda do servidor apaga tudo. | Subir um logótipo em Configurações e ver o objeto no bucket; o log de arranque **não** pode dizer `S3_BUCKET não definido`. |
| [ ] | `FRONTEND_URL` | URL público do front-end (`https://…`), usado nos links dos e-mails de ativação e de redefinição de senha. | O link do e-mail de ativação abre a página certa. |
| [ ] | `CORS_ALLOWED_ORIGINS` | Só as origens reais do front-end, separadas por vírgula. **Nunca** deixar o default `http://localhost:4200`. | O front-end de produção consegue fazer login (sem erro CORS na consola do browser). |

## 2. Fortemente recomendado

| ✔ | Variável | O que pôr | Notas |
|---|---|---|---|
| [ ] | `RECAPTCHA_SITE_KEY`, `RECAPTCHA_SECRET_KEY` | Chaves **v3** criadas para o **domínio de produção** (uma chave por domínio). | Sem elas o registo e os leads públicos ficam só com rate limiting. O log mostra `reCAPTCHA recusou um pedido:` quando bloqueia. |
| [ ] | `SENTRY_DSN`, `SENTRY_ENVIRONMENT=production` | Projeto Sentry de produção. | Sem isto os erros só existem no stdout do processo. |
| [ ] | `BACKUP_RETENCAO_DIAS` | 14 por omissão; ajustar conforme o espaço do bucket. | Backup diário às 03:00; verificar o primeiro na manhã seguinte (ver checklist 4). |
| [ ] | `PG_DUMP_PATH`, `PG_RESTORE_PATH` | Só se `pg_dump`/`pg_restore` não estiverem no `PATH` do servidor. **Versão do cliente ≥ versão do servidor Postgres.** | `pg_dump --version` no servidor. |
| [ ] | `DB_POOL_SIZE` + `DB_POOL_MAX_OVERFLOW` | 20 + 20 por omissão = 40 ligações. Têm de caber no `max_connections` do Postgres (menos as ligações de migração/backup/administração). | Só relevante se o Postgres for pequeno. |
| [ ] | `LOGIN_HISTORICO_RETENCAO_DIAS`, `NOTIFICACOES_LIDAS_RETENCAO_DIAS`, `TOKENS_RETENCAO_DIAS` | 365 / 180 / 30 por omissão — limpeza diária às 04:00. **Valores técnicos: confirmar com o jurista** e alinhar com a política publicada. | |
| [ ] | `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DIAS` | 20 min / 7 dias por omissão — manter. | |

## 3. Opcionais no piloto (decidir e registar)

| ✔ | Variável | Decisão |
|---|---|---|
| [ ] | `REDIS_URL` | Vazio é correto **só com uma instância**. Definir assim que houver mais de uma. |
| [ ] | `PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_MODE`, `PAYPAL_WEBHOOK_ID` | O PayPal **não aceita Kwanza**; para escolas em AOA a via é a transferência bancária. Se for usado (escolas em EUR/USD): credenciais **live** só com `PAYPAL_MODE=live`, e o Webhook criado na app PayPal. Vazio = a opção some/falha de forma controlada. |
| [ ] | `ANTHROPIC_API_KEY`, `PROF_VIRTUAL_MODELO` | Só se o Prof. Virtual e o Suporte Virtual forem oferecidos no piloto. Vazio = respondem 503 ("não configurado"). Cada mensagem tem custo real (há rate limiting por IP). |
| [ ] | `SMS_WEBHOOK_URL`, `SMS_WEBHOOK_TOKEN` | Só com um gateway SMS. Vazio = SMS só registado nos logs. |
| [ ] | `UPLOAD_DIR` | Irrelevante com `S3_BUCKET` definido. |

## 4. Depois do primeiro arranque em produção

- [ ] `alembic upgrade head` correu sem erros (a imagem Docker já o faz no arranque).
- [ ] Criar a primeira conta Super Admin: `python seed_super_admin.py` (password forte, guardada num gestor de passwords).
- [ ] `GET /api/v1/health` = 200 e o log de arranque **não** tem os avisos `S3_BUCKET não definido`,
      `SMTP não configurado`, `RECAPTCHA_SECRET_KEY não definida` (ou cada um está aí de propósito).
- [ ] Registar uma escola de teste ponta a ponta (registo → e-mail de ativação recebido → login).
- [ ] `python scripts/backup_manual.py` grava um `.dump` em `_backups/` **no bucket** (não em `uploads/`).
- [ ] **Na manhã seguinte:** existe um backup **agendado** (03:00) no bucket. Este passo nunca foi
      observado — só o backup manual foi provado.
- [ ] Ensaiar o restauro desse backup numa base nova (`RUNBOOK.md`, secção 5).
- [ ] Preencher os contactos e o URL de produção no `RUNBOOK.md`.
