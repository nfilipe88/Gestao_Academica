# Plano de Produção — 15 Dias até à Primeira Escola Real

## Contexto

Duas auditorias completas (técnica/segurança e de produto, ver histórico) confirmaram que a lacuna
não é funcional — a cobertura de módulos já é ampla e a maioria das regras de negócio bate certo
com o documento de arquitetura original. A lacuna é de **infraestrutura, segurança operacional e
um meio de pagamento real para o mercado angolano**. Este plano ataca só isso, na ordem que reduz
o risco mais cedo, e propositadamente **deixa de fora** tudo o que o roteiro do próprio projeto já
tinha adiado para depois desta fase (multi-instância, 2FA, CI/CD com deploy automático, modelo de
ML real, e-assinatura) — nada disso bloqueia um piloto supervisionado numa única instância bem
cuidada.

**Regra de ouro do plano**: nenhuma escola real entra na plataforma antes do Dia 15. Os dias 1-14
são só para a equipa, com dados de teste.

**Nota sobre o calendário**: 15 dias corridos, não 15 dias úteis — inclui dois fins de semana. Estão
marcados como dias de buffer/testes mais leves, não como dias de folga — num sprint desta natureza
normalmente não há folga real, mas o trabalho de fim de semana é o mais fácil de adiar sem risco se
algo a meio da semana atrasar.

---

## Semana 1 — O maior risco primeiro: pagamento (Dias 1-5)

Pagamento é tratado primeiro de propósito: é o único item deste plano que não é "só código" — exige
uma decisão de produto/negócio (que meio de pagamento a plataforma vai realmente suportar em
Angola) antes de haver alguma coisa para programar. Se isto atrasar, atrasa o plano inteiro; por
isso começa no Dia 1, não a meio.

- [x] **Dia 1 — Decisão de pagamento + rate limiting em paralelo.** ✅ Decisão tomada (transferência
  bancária com conciliação manual, via (a)). Rate limiting por IP acrescentado a `POST
  /auth/registo` (5/hora) e a `POST /public/{tenant_id}/leads` (10/hora), reaproveitando
  `excedeu_limite`. CAPTCHA: Google reCAPTCHA v3 integrado (score anti-bot silencioso, sem puzzle
  visual) nos dois mesmos endpoints — `app/core/recaptcha.py`, chave pública servida via `GET
  /public/config`, ativa só quando `RECAPTCHA_SECRET_KEY` está configurada (fallback aberto em
  dev/testes). 4 pontos do frontend atualizados (registo, captar-lead, escola pública, assistente
  de matrícula). Falta só o utilizador criar as chaves reais em
  https://www.google.com/recaptcha/admin antes de produção.
  Decisão de produto (não código): qual o meio de pagamento real a suportar primeiro — as opções
  mais prováveis para o mercado são (a) transferência bancária com referência gerada pela
  plataforma + conciliação manual pela Secretaria (o "MVP pragmático" — quase nenhum código novo,
  reaproveita `FaturaMensalidade`/`status_pagamento` já existentes, só sem o webhook automático do
  PayPal), ou (b) um gateway local tipo Multicaixa Express, se houver acesso comercial a uma conta
  em 15 dias (mais trabalho, mais valor). **Decidir isto é a única tarefa do Dia 1 que não pode ser
  minha** — precisa de confirmação do lado do negócio antes de eu programar a via errada.
  Em paralelo (não depende da decisão acima): rate limiting + CAPTCHA em `POST /auth/registo` e no
  endpoint público de leads do CRM (`app/api/v1/crm.py`) — já sabemos exatamente onde falta,
  reaproveitando o `excedeu_limite` já usado em `login`/`esqueci-senha`.

- [x] **Dia 2-3 — Implementar o meio de pagamento escolhido.** ✅ Transferência bancária em
  destaque no Portal (IBAN, valor, referência), auto-relato "já paguei" pelo Responsável
  (`pagamento_reportado_em`/`_referencia`, aditivo — sem novo estado em `status_pagamento`),
  notificação à Secretaria, PayPal mantido como alternativa secundária.
  Se for a via (a): novo endpoint para gerar a referência de transferência + ecrã na Secretaria
  para marcar uma fatura como paga manualmente (com o valor/data confirmados), substituindo o
  `gerar-cobranca` do PayPal como via principal (o PayPal pode continuar disponível como
  alternativa, não precisa de ser removido). Se for a via (b): integração real com o gateway
  escolhido, seguindo o mesmo padrão já existente em `app/core/paypal.py` (captura no servidor,
  nunca confiar no frontend, verificação de assinatura no webhook).

- [x] **Dia 4 — Testar o fluxo de pagamento ponta a ponta.** ✅ Verificado ao vivo por completo
  (reportar pagamento → badge "aguarda confirmação" → notificação à Secretaria → Marcar Pago →
  recibo emitido) + 3 testes automatizados novos; régua de cobrança confirmada a ignorar faturas já
  reportadas.
  Criar uma fatura → gerar cobrança pelo novo meio → confirmar pagamento (manual ou via webhook) →
  confirmar que a régua de cobrança (RN04) já não avisa depois de pago → confirmar que o recibo
  gerado reflete o meio de pagamento correto.

- [ ] **Dia 5 — Buffer de pagamento + arrancar o backup.**
  Absorver o que sobrar do pagamento (historicamente a tarefa mais imprevisível do plano). Se
  terminar cedo, começar já o script de backup do Dia 6.

---

## Semana 2 — Segurança operacional e legal (Dias 6-10)

- [x] **Dia 6 — Backup e restauro.** ✅ `pg_dump` diário às 03:00 via o agendador já existente
  (`app/core/scheduler.py`), reaproveitando o storage S3-compatível já existente
  (`app/core/storage.py`) — com retenção configurável (`BACKUP_RETENCAO_DIAS`, 14 dias por
  omissão). Scripts `backup_manual.py`/`restaurar_db.py` (este último recusa por omissão
  restaurar por cima de `academic_db`/`academic_db_test`, precisa de `--confirmar-alvo-existente`).
  **Restauro completo testado de verdade** (2026-09-20): backup real de `academic_db` (76 tabelas,
  3644 linhas) → restaurado numa base de ensaio nova → contagens confirmadas idênticas → base de
  ensaio removida. Documentado em `README.md`, secção "Backup e Restauro". 5 testes automatizados
  novos (orquestração + retenção, sem precisar de Postgres/S3 reais).

- [x] **Dia 7 — Storage real para ficheiros (eliminar o fallback local).** ✅ MinIO real (via Docker,
  `quay.io/minio/minio` — a imagem `minio/minio` no Docker Hub deu "pull access denied" por limite
  de pulls anónimos) a correr para o ambiente nativo/sem-Docker, `S3_BUCKET` configurado em `.env`.
  Verificado ao vivo com um pedido HTTP real (`PUT /configuracoes/logotipo`): o ficheiro apareceu no
  bucket MinIO (`mc ls`), nada de novo em disco local. Nova função `storage.listar_ficheiros`
  (usada pela retenção de backups do Dia 6). Passo reproduzível documentado em `README.md`.
  `docker-compose.yml` já tinha isto coberto para o caminho containerizado (Fase 2 anterior) — este
  passo fechou a mesma lacuna para quem corre o back-end nativamente.

- [x] **Dia 8 — Guardas de RBAC no frontend + suite de testes ligada ao CI.** ✅ Novo
  `perfilGuard(...perfis)` (`core/guards/perfil.guard.ts`), aplicado a todas as rotas filhas
  sensíveis em `app.routes.ts` — mesma partição já usada no menu lateral
  (`dashboard-layout.component.html`), cada uma com o RBAC do backend citado. Redireciona para a
  "casa" certa de cada perfil (`SUPER_ADMIN`→`/admin`, `ALUNO`/`RESPONSAVEL`→`/portal`, staff→
  `/dashboard`), não sempre para `/dashboard` (que nem todos os perfis conseguem abrir). Verificado
  ao vivo: ALUNO a navegar direto a `/financeiro` cai em `/portal`; GESTOR a navegar direto a
  `/admin` cai em `/dashboard`. `NG0201` em `app.spec.ts` corrigido (faltavam `provideStore`/
  `provideRouter`/`provideHttpClient` no `TestBed` — o scaffold original do Angular CLI nunca tinha
  sido atualizado) e reescrito com 2 testes reais (arranque sem sessão, restauro de sessão a partir
  do `localStorage`); `ng test` acrescentado ao `ci.yml`.

- [x] **Dia 9 — Desativar em vez de eliminar (retenção legal) + limite de alunos do plano.** ✅
  Decisão do utilizador (alterou o plano original de "hard delete faseado"): a lei angolana exige
  reter os dados 15 anos, por isso **nada é eliminado, só desativado**. (1) Escola: o
  Desativar/Ativar do Super Admin já existia como Suspender/Reativar (`PATCH /admin/tenants/{id}/status`)
  — rótulos e mensagens passaram a Desativar/Ativar/"Desativada", sem apagar nada (testado:
  desativar → login bloqueado → ativar → alunos intactos). (2) Aluno: nova coluna `aluno.ativo`,
  `PATCH /alunos/{id}/ativo` só para o Gestor — desativar suspende o login do aluno, liberta a vaga no
  plano e deixa notas/matrículas/faturas intactas; não pode ser matriculado enquanto desativado;
  filtro Ativos/Desativados + badge na lista. (3) Limite de alunos do plano
  (`app/core/limites_plano.py`): `PlanoSaaS.limite_alunos` passa a ser aplicado (403 com mensagem clara)
  ao criar aluno, converter lead do CRM, importar mini-pautas, aprovar transferência e reativar aluno;
  só conta alunos ativos (a faturação por aluno também). (4) Isenção: `Tenant.isento_limite_alunos`,
  `PATCH /admin/tenants/{id}/isencao-limite-alunos` só para o Super Admin (botão "Isentar" na coluna
  Alunos do painel, que agora mostra `ativos / limite`). 9 testes novos. **Fica por fazer**: o rascunho
  de política de privacidade/retenção (precisa de revisão legal — não é algo que eu possa certificar).

- [ ] **Dia 10 — Limpeza de dados de teste + arrumar o repositório.**
  (O "limite de alunos" foi antecipado para o Dia 9.) Limpar os dados de teste acumulados no tenant
  partilhado usado durante o desenvolvimento (ex.: o "Boletim de Notas" personalizado esquecido lá,
  responsável/contrato/IBAN de teste do pagamento). Começar a arrumar os ficheiros por commitar.

---

## Semana 3 — Estabilização e ensaio geral (Dias 11-15)

- [ ] **Dia 11 — Consolidar o repositório.**
  Rever e commitar o trabalho pendente em blocos lógicos (não um único commit gigante), criar uma
  tag/branch de release para esta fase, e escrever um runbook operacional curto para quem vai
  acompanhar o piloto: como criar um tenant novo, o que verificar todos os dias, como reagir a um
  incidente (quem contactar, onde estão os logs, como fazer o restauro de backup se precisar).

- [ ] **Dia 12 — Teste de fumo com volume realista.**
  Não é teste de carga a sério (isso continua corretamente adiado para depois do piloto) — é
  popular a plataforma com um número de escolas/turmas/alunos/faturas parecido com o que as 10
  escolas de teste vão realmente gerar, e confirmar que nada degrada de forma óbvia (tempos de
  resposta do Diário, da Pauta, dos relatórios de Indicadores).

- [ ] **Dia 13 — Suite de testes completa + code freeze de novas funcionalidades.**
  Correr tudo (backend + frontend, agora já ligado ao CI), corrigir o que aparecer. A partir daqui,
  zero funcionalidades novas até abrir às escolas — só correções do que os dias seguintes
  revelarem.

- [ ] **Dia 14 — Ensaio geral.**
  Simular, com a equipa a acompanhar como se fosse uma escola real: registo → configuração inicial
  → matrícula de alunos → lançamento de notas/faltas → geração de fatura → pagamento pelo novo meio
  → emissão de um documento (declaração/recibo) → notificação a chegar e a levar ao sítio certo.
  Qualquer tropeço encontrado aqui é a última oportunidade de corrigir antes de uma escola real
  sentir o mesmo tropeço.

- [ ] **Dia 15 — Revisão go/no-go + abertura controlada.**
  Rever o runbook, confirmar que o backup do Dia 6 continua a correr e que o restauro ainda
  funciona, e só então abrir a plataforma às primeiras escolas de teste — uma de cada vez, não as
  10 ao mesmo tempo, para poder observar cada onboarding isoladamente.

---

## Depois dos 15 dias — os dois portões seguintes

O pedido original juntava "15 dias" a "10 escolas de teste" e "50 escolas piloto" como se fossem a
mesma data. Não devem ser — cada fase só deve abrir com um sinal real da fase anterior, não por
calendário:

- **Fase de teste (10 escolas)**: abrir uma escola de cada vez ao longo de alguns dias depois do
  Dia 15, não todas de uma vez. Critério para avançar à fase seguinte: pelo menos 1-2 semanas de
  utilização real sem incidente grave (perda de dados, pagamento que não concilia, acesso indevido
  entre escolas), e o backup/restauro validado outra vez já com dados reais em jogo.
- **Fase piloto (50 escolas)**: só depois desse sinal positivo. Nessa altura, e só nessa altura,
  vale a pena reabrir os itens conscientemente adiados neste plano — sobretudo infraestrutura
  multi-instância (se o volume justificar mais do que uma instância) e automação de deploy — porque
  aí sim o custo de os continuar a adiar passa a ser maior do que o custo de os construir.

---

## O que este plano deliberadamente não inclui, e porquê

- **Deploy automatizado (CD)** — o CI já corre testes e builda as imagens; para uma abertura
  controlada e lenta como esta, um deploy manual (ou por script, sem *pipeline* completo) é mais
  seguro do que automatizar algo que só vai correr algumas vezes nas próximas semanas.
- **Multi-instância / Redis obrigatório** — numa única instância bem cuidada, com 10-50 escolas,
  as limitações já documentadas no código ("só correto com UMA instância") deixam de ser um risco.
- **2FA no Super Admin, modelo de ML real, e-assinatura no CRM** — nenhum bloqueia um piloto
  supervisionado; continuam no roteiro do projeto para depois.
- **Faturação fiscal certificada** — sai fora de âmbito de propósito; o recibo já avisa
  explicitamente que não tem valor fiscal, e resolver isto a sério é uma decisão de conformidade
  por mercado, não uma tarefa de 15 dias.
