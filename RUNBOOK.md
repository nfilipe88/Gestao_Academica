# Runbook operacional — piloto supervisionado

Para quem acompanha o piloto no dia a dia. Assume **uma única instância** do back-end (ver
`README.md` e `PLANO_PRODUCAO.md`). Onde diz **[PREENCHER]**, falta informação que só a equipa
tem (contactos, URLs de produção) — não está inventada aqui.

## 1. Contactos e endereços

| O quê | Valor |
|---|---|
| Responsável técnico / quem acordar num incidente | **[PREENCHER]** |
| Contacto comercial (isenções, mudança de plano) | **[PREENCHER]** |
| URL da aplicação em produção | **[PREENCHER]** |
| Painel Sentry (erros) | **[PREENCHER]** — só ativo se `SENTRY_DSN` estiver definido |

## 2. Criar uma escola nova (tenant)

Duas vias, ambas acabam com um Gestor por ativar (o login recusa-se até o e-mail de ativação ser
clicado):

- **Auto-serviço**: a escola regista-se em `/registo` (limitado a 5 registos/hora por IP e
  protegido por reCAPTCHA v3 quando `RECAPTCHA_SECRET_KEY` está definida).
- **Pelo Super Admin** (`/admin` → "Nova instituição"): a via recomendada no piloto — a equipa
  decide quem entra.

Depois de criada, no painel Super Admin:
1. **Assinatura**: atribuir um plano (define o preço por aluno e o `limite_alunos`). Sem
   assinatura ativa não há limite de alunos.
2. **Validade da licença**: definir a data (o job diário alerta a aproximar-se e suspende a escola
   ao expirar; 15+ dias de atraso bloqueiam novas matrículas).
3. Se a escola precisar de ultrapassar o limite de alunos por acordo: botão **"Isentar"** na
   coluna Alunos.
4. Pedir ao Gestor da escola para configurar o **Ano Letivo** e o **IBAN** em Configurações (a
   transferência bancária é o meio de pagamento principal; sem IBAN o Portal mostra "contacte a
   secretaria").

## 3. Verificações diárias (5 minutos)

1. `GET /api/v1/health` responde 200 (confirma processo **e** ligação à base de dados).
2. **Backup de ontem existe**: o job corre às 03:00. Listar no bucket `_backups/` (deve haver um
   `academic_db_AAAAMMDD_HHMMSS.dump` recente) ou correr `python scripts/backup_manual.py` se
   houver dúvidas. Sem `S3_BUCKET` o backup fica no mesmo disco — **não conta**.
3. Logs do back-end sem `Falha ao executar o backup diário` nem `exception` repetidas. Não há
   ficheiro de log próprio: é o stdout/stderr do processo (ou `docker compose logs backend`).
4. Sentry (se ativo): erros novos desde ontem.
5. Painel Super Admin: escolas perto de expirar a licença; Tickets de Suporte por responder.
6. Jobs diários: 03:00 backup · 07:00 validade de licenças · 08:00 régua de cobrança.

## 4. Incidentes

**Primeiro passo, sempre**: confirmar que o processo apanhou o código/configuração certos — o
back-end corre sem `--reload`, por isso alterar código ou `.env` só tem efeito depois de reiniciar
(no Windows, matar a árvore inteira: `taskkill /PID <pid> /T /F`).

| Sintoma | Causa provável / o que fazer |
|---|---|
| Tudo devolve 5xx, `/health` falha | Base de dados em baixo ou credenciais erradas. Ver logs; `pg_isready`. |
| Uma escola não consegue entrar | Estado "Desativada" (suspensão manual ou licença expirada) — Painel Super Admin → **Ativar** / renovar validade. Nada é apagado ao desativar. |
| "Limite de N aluno(s) do plano atingido" | Comportamento esperado. Desativar alunos que saíram, mudar de plano, ou **Isentar** (Super Admin). |
| Utilizador diz que "o token é inválido" logo depois de a escola ser reativada | Tokens emitidos no mesmo segundo da desativação são revogados; pedir para voltar a iniciar sessão. |
| Uploads (logótipo, anexos) falham | MinIO/S3 em baixo ou credenciais erradas (`S3_*`). Ver `docker ps` / consola MinIO em `:9001`. |
| Formulários públicos devolvem 429 | Rate limiting a funcionar (registo 5/h, leads 10/h por IP). Esperar, ou investigar abuso. |
| Formulários públicos devolvem 400 "Verificação de segurança falhou" | reCAPTCHA recusou o pedido (score < 0.5). O log tem `reCAPTCHA recusou um pedido:` com o motivo. |
| Um pedido de documento fica em "pendente de pagamento" | Pagamento por transferência: a Secretaria confirma em Documentos → **Marcar paga** (o PayPal só serve moedas que aceita; Kwanza não). Depois o PDF fica disponível ao Responsável. |
| PDFs (documentos) com erro | Modelo personalizado inválido — em Documentos, repor o modelo ao padrão; o layout nativo é sempre a reserva. |

**Nunca eliminar dados** para "resolver" um incidente: a lei angolana exige reter os dados 15 anos.
Desativar é sempre reversível; apagar não. Não há endpoint de eliminação de escolas ou alunos, de
propósito.

## 5. Restaurar a base de dados a partir de um backup

Procedimento testado (2026-09-20). Detalhes e comandos em `README.md`, secção "Backup e Restauro".
Resumo:

1. **Ensaiar sempre primeiro** numa base nova, sem tocar na real:
   `python scripts/restaurar_db.py --chave _backups/<ficheiro>.dump --bd-destino academic_db_drill --criar-bd`
2. Comparar contagens de tabelas/linhas com o esperado.
3. Só num desastre real: parar o back-end, restaurar por cima com `--confirmar-alvo-existente`
   (o script recusa isto por omissão), voltar a arrancar o back-end e correr `alembic upgrade head`.
4. Pedir a todos os utilizadores para reiniciarem sessão.

Perde-se tudo o que aconteceu **depois** do backup escolhido (no máximo ~24 h — backups diários).
Avisar as escolas afetadas.

## 6. Variáveis de ambiente que importam em produção

Ver `back_end/.env.example` (comentado). **SMTP é obrigatório**: sem ele, o e-mail de ativação de conta nunca chega e nenhuma escola nova consegue entrar (o token só existe no e-mail). Mínimo para o piloto: `SMTP_*`, `DATABASE_URL*`, `JWT_SECRET_KEY`
(**trocar o valor de desenvolvimento**), `S3_*` (backups e ficheiros fora do servidor),
`RECAPTCHA_*`, SMTP para e-mails de ativação/lembretes, `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`.
`REDIS_URL` é opcional com uma só instância. Os segredos do `.env` de desenvolvimento **não** são
os de produção e nunca vão para o git.

## 7. Limitações conhecidas do piloto

- Uma única instância; sem alta disponibilidade nem réplica da base de dados.
- Pagamentos: transferência bancária com conciliação manual pela Secretaria; PayPal só como
  alternativa. Sem gateway local automático.
- Política de privacidade e retenção **ainda por escrever/rever juridicamente**.
- Sem 2FA no Super Admin; sem CD automático.
