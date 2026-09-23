# Política de Privacidade e Retenção de Dados — RASCUNHO PARA REVISÃO JURÍDICA

> **ESTADO: RASCUNHO. NÃO PUBLICAR NEM ASSUMIR COMO CONFORME.**
> Escrito por quem construiu a plataforma, a partir do que o código **realmente faz** (secção C).
> Não é aconselhamento jurídico. Todo o texto marcado **[JURISTA]** é uma decisão ou uma
> afirmação legal que só um profissional com conhecimento da legislação angolana de proteção de
> dados pode confirmar. Todo o texto marcado **[EQUIPA]** é informação que só a equipa tem
> (nome da entidade, contactos). Nenhuma referência legal aqui foi verificada.

---

# PARTE A — Nota para o jurista

## A.1 O que precisamos de si

1. Rever a **Parte B** (texto para os utilizadores) e dizer o que falta, o que está errado e o que
   tem de ser escrito de outra forma.
2. Responder às **perguntas abertas** (A.3).
3. Dizer-nos se há **obrigações formais** que a plataforma tem de cumprir antes de tratar dados
   reais (notificação/registo junto da autoridade de proteção de dados, autorizações para
   transferências internacionais, nomeação de responsável de proteção de dados, etc.). **[JURISTA]**

## A.2 Resumo factual da plataforma (para se situar)

- SaaS multi-escola: cada escola (a "instituição") gere os seus alunos, notas, faltas,
  comportamento, faturação, comunicados e documentos. Os dados de uma escola são isolados dos das
  outras (isolamento por escola na aplicação **e** ao nível da base de dados).
- **Titulares de dados**: alunos (na maioria **menores**), responsáveis/encarregados de educação,
  professores e funcionários da escola, candidatos (leads) que preenchem formulários públicos, e
  visitantes do site da plataforma.
- **A plataforma nunca elimina** escolas nem alunos: só os **desativa** (decisão da equipa: a
  legislação exigiria conservar os dados 15 anos antes de qualquer arquivo **[JURISTA: confirmar o
  prazo, a lei que o impõe, o que conta como "arquivo" e se o prazo varia por tipo de dado]**).
- Localização dos servidores: **[EQUIPA: onde ficam a base de dados, o storage e os backups — país e
  fornecedor]**.
- Subcontratantes/terceiros que recebem dados: ver B.5 (Google, PayPal, Anthropic, Sentry, SMTP,
  fornecedor de storage/alojamento).

## A.3 Perguntas abertas

1. **Papéis.** Assumimos: a **escola** é responsável pelo tratamento dos dados dos seus alunos,
   responsáveis e professores; a **plataforma** é **subcontratante** desses dados e
   **responsável pelo tratamento** apenas dos dados da própria relação comercial (contas de
   Gestor, faturação da plataforma, pedidos de suporte, visitantes do site). Está correto? Precisamos de um
   **contrato de subcontratação** entre a plataforma e cada escola? Onde entra (nos termos de
   serviço, no registo)? **[JURISTA]**
2. **Fundamento de licitude.** Para dados de menores e de encarregados de educação, o fundamento é
   contrato/obrigação legal da escola, ou consentimento? Quem recolhe o consentimento — a escola? A
   plataforma pode mostrá-lo? **[JURISTA]**
3. **Consentimento parental/menores.** Há idade mínima a partir da qual o menor pode consentir?
   Como deve ser tratada a foto de perfil de um aluno menor (usada em cartão de acesso)? **[JURISTA]**
4. **Retenção vs. direito ao apagamento.** Se um titular pedir a eliminação e a lei exigir
   conservar 15 anos, o texto da B.8 explica isto — está juridicamente correto? Após os 15 anos, o
   que fazer (arquivo, anonimização, eliminação)? **[JURISTA]**
5. **Dados sensíveis.** O registo de comportamento (positivo/negativo) e o "risco de evasão" são
   dados sensíveis ou de categoria especial? Há dados de saúde (não recolhemos campos de saúde, mas
   um texto livre de comportamento/comunicado pode conter)? **[JURISTA]**
6. **Transferências internacionais** (Google, PayPal, Anthropic, Sentry — sedes fora de Angola):
   que mecanismo/autorização é exigido? Precisamos de consentimento expresso? **[JURISTA]**
7. **Decisões automatizadas.** O "risco de evasão" é calculado por **regras** (não IA) e serve de
   alerta à escola; o "Prof. Virtual" é um assistente de IA para o aluno. Alguma destas coisas
   exige informação/direito de oposição específico? **[JURISTA]**
8. **Prazos de resposta a direitos dos titulares** e **prazo de notificação de violações** à
   autoridade e aos titulares. **[JURISTA]**
9. **Cookies/armazenamento local.** Guardamos apenas dados de sessão no navegador (B.10) — precisa
   de aviso/consentimento? **[JURISTA]**
10. **Autoridade competente e contactos** (nome, morada, como apresentar queixa). **[JURISTA]**

---

# PARTE B — Texto da política (versão para os utilizadores)

*(Escrito em linguagem simples. Substituir os campos **[EQUIPA]**/**[JURISTA]** antes de publicar.)*

## B.1 Quem somos e que papel temos

Esta política explica como são tratados os dados pessoais na plataforma **[EQUIPA: nome da
plataforma e da entidade legal, NIF, morada, e-mail de contacto de proteção de dados]** ("a
Plataforma").

- Cada **escola** que usa a Plataforma decide **que dados dos seus alunos, encarregados de
  educação e professores** recolhe e **para quê**: a escola é a responsável por esses dados.
- A **Plataforma** trata esses dados **em nome da escola**, apenas para lhe fornecer o serviço e
  seguindo as suas instruções (subcontratante).
- A Plataforma é **ela própria responsável** pelos dados da sua relação comercial: contas de
  Gestor/administradores, faturação, pedidos de suporte e visitantes do seu site. **[JURISTA]**

**Se é aluno, encarregado de educação ou professor**, o primeiro contacto para exercer os seus
direitos é a **escola**. Se a escola não responder, pode contactar-nos em **[EQUIPA]**.

## B.2 Que dados tratamos

| Quem | Dados |
|---|---|
| **Alunos** | Nome, data de nascimento, número de matrícula interna, número de documento de identificação (opcional), foto de perfil (para o cartão de acesso), documentos anexados pela escola (ex.: cartão/BI, certificado de habilitações), matrículas e turmas, presenças e faltas, avaliações e notas, trabalhos e exames online (respostas e classificações), registos de comportamento, pedidos de documentos, histórico escolar, e — se a escola criar acesso ao Portal — e-mail e credenciais de acesso. |
| **Encarregados de educação / responsáveis** | Nome, telefone, e-mail, número de documento (opcional), grau de parentesco, qual é o responsável financeiro; contrato, faturas, pagamentos (incluindo referência de transferências que indique) e comunicações recebidas/enviadas. |
| **Professores e funcionários** | Nome, e-mail, perfil de acesso, turmas/disciplinas atribuídas, lançamentos de notas e presenças, ações registadas na plataforma. |
| **Candidatos (formulário público da escola)** | Nome e contactos do responsável, nome e data de nascimento do candidato, curso de interesse, mensagem, documentos enviados na candidatura, aceitação do regulamento. |
| **Visitantes do site da Plataforma** | Mensagens enviadas pelo formulário de contacto/suporte e pelo assistente virtual de suporte. |
| **Todos os utilizadores com conta** | Palavra-passe (guardada só sob a forma de *hash*, nunca em texto legível), endereço IP e tipo de navegador de cada início de sessão, e um registo de ações administrativas sobre contas. |

## B.3 Para que usamos os dados e com que fundamento **[JURISTA]**

| Finalidade | Fundamento proposto (a confirmar) |
|---|---|
| Gerir a matrícula, o percurso escolar, as avaliações, as faltas e a faturação do aluno | Execução do contrato/serviço de ensino; obrigação legal da escola **[JURISTA]** |
| Comunicar com encarregados de educação e alunos (comunicados, lembretes de propina, avisos) | Execução do contrato; interesse legítimo da escola **[JURISTA]** |
| Emitir documentos (declarações, certificados, histórico, boletins) | Pedido do titular; obrigação legal **[JURISTA]** |
| Segurança da conta (início de sessão, limites de tentativas, prevenção de abuso e robôs) | Interesse legítimo em proteger o serviço **[JURISTA]** |
| Cobrança da mensalidade da Plataforma às escolas | Execução do contrato |
| Apoio ao cliente | Execução do contrato / interesse legítimo |
| Assistente de estudo (Prof. Virtual) | **[JURISTA]** — ver B.5; funcionalidade opcional, ativada pela escola |

Não vendemos dados pessoais nem os usamos para publicidade.

## B.4 Crianças e menores

Grande parte dos titulares são **menores**. Os dados dos alunos são introduzidos e geridos pela
escola e pelos encarregados de educação; o aluno só tem acesso ao Portal se a escola lhe criar
conta. Os menores não podem registar escolas nem contas de Gestor. A foto de perfil do aluno é
enviada pela escola/família e usada no cartão de acesso. **[JURISTA: regras de consentimento e
idade mínima.]**

## B.5 Com quem partilhamos dados

Só partilhamos dados com prestadores necessários ao serviço, por ordem de sensibilidade:

| Prestador | Para quê | Dados que recebe | Onde fica **[EQUIPA/JURISTA]** |
|---|---|---|---|
| **Alojamento e base de dados** | Guardar tudo | Todos os dados da plataforma | [EQUIPA] |
| **Storage de ficheiros (S3 ou equivalente)** | Logótipos, anexos, documentos dos alunos, **cópias de segurança diárias** | Ficheiros e cópias completas da base de dados | [EQUIPA] |
| **Fornecedor de e-mail (SMTP)** | E-mails de ativação de conta, redefinição de palavra-passe, avisos e lembretes | Nome, e-mail e o conteúdo da mensagem | [EQUIPA] |
| **Google reCAPTCHA** | Distinguir pessoas de robôs no registo de escolas e nos formulários públicos | Endereço IP, dados do navegador e sinais de comportamento no formulário | EUA **[JURISTA]** |
| **PayPal** (opcional) | Pagamento em moedas que o PayPal aceita | Valor, referência do pedido e dados de pagamento do próprio pagador (introduzidos diretamente no PayPal) | [JURISTA] |
| **Anthropic** (opcional) | Assistentes de IA: "Prof. Virtual" (ajuda a estudar a partir de um material de aula) e assistente de suporte do site | O texto que o utilizador escreve na conversa e o texto do material de aula em causa. **Não enviamos o nome do aluno**, mas o utilizador pode escrever dados pessoais no texto livre. **[JURISTA]** | EUA |
| **Sentry** (opcional) | Detetar e corrigir erros | Detalhes técnicos de erros; configurado **sem dados pessoais identificáveis por omissão** | [EQUIPA] |

Podemos ainda divulgar dados quando a lei o exigir ou a pedido de autoridade competente. **[JURISTA]**

## B.6 Transferências para fora de Angola **[JURISTA]**

Alguns prestadores acima têm servidores fora de Angola. **[Texto sobre o mecanismo legal aplicável e
autorizações, a redigir pelo jurista.]**

## B.7 Quanto tempo guardamos os dados

- **Não eliminamos** alunos nem escolas. Quando uma escola deixa de usar a Plataforma ou um aluno
  sai, os registos são **desativados**: deixam de ter acesso e deixam de contar para o plano, mas o
  histórico (matrículas, notas, faturas, documentos) **é conservado**.
- Conservamos os dados **durante [15] anos** por exigência legal **[JURISTA: prazo, fundamento e
  o que acontece depois — arquivo, anonimização ou eliminação]**.
- **Cópias de segurança**: mantemos as **últimas [14] cópias diárias** e apagamos automaticamente as
  mais antigas. Por isso, dados corrigidos ou alterados podem subsistir nas cópias até esse prazo.
- **Registos de início de sessão** (IP e navegador), **tokens de sessão/redefinição de palavra-passe**
  e **notificações**: **[EQUIPA/JURISTA: prazo a definir — hoje não há eliminação automática]**.
- Dados de **candidatos** que nunca se tornam alunos: **[JURISTA: prazo]** (hoje ficam no CRM da escola).

## B.8 Os seus direitos

Pode pedir **acesso**, **retificação**, **oposição** e, quando a lei o permitir, **eliminação** ou
**limitação** do tratamento dos seus dados, e retirar o consentimento quando este for o
fundamento. **[JURISTA: lista exata de direitos e prazos.]**

**Importante — retenção obrigatória:** quando a lei obriga a conservar certos dados (por exemplo o
percurso escolar durante 15 anos), não os podemos eliminar antes do fim do prazo; nesse caso
**limitamos o acesso** (desativação) e explicamos-lhe a razão. **[JURISTA]**

Como exercer: contacte primeiro a **escola**; ou **[EQUIPA: e-mail]**. Responderemos em **[JURISTA:
prazo]**. Tem também o direito de apresentar queixa à autoridade competente: **[JURISTA: nome e
contacto da autoridade angolana de proteção de dados]**.

## B.9 Como protegemos os dados

- Separação rigorosa entre escolas (uma escola nunca vê os dados de outra), garantida na aplicação
  e na própria base de dados.
- Palavras-passe guardadas com *hash* (bcrypt); sessões de curta duração que expiram e podem ser
  revogadas (ex.: quando uma conta ou escola é desativada).
- Limites de tentativas de início de sessão e de registo, e proteção anti-robôs.
- Controlo de acessos por perfil (Gestor, Secretaria, Professor, Aluno, Responsável).
- Cópias de segurança diárias fora do servidor da base de dados, com restauro testado.
- Ligação cifrada (HTTPS) **[EQUIPA: confirmar em produção]**.

Nenhum sistema é infalível. **Em caso de violação de dados** com risco para os titulares,
notificaremos a escola e, quando exigido, a autoridade e os titulares **[JURISTA: prazos e
conteúdo]**.

## B.10 Cookies e armazenamento no navegador

A aplicação guarda no navegador apenas o necessário para manter a sessão iniciada (dados de sessão
e o perfil do utilizador). Não usamos *cookies* de publicidade nem de seguimento. O serviço
reCAPTCHA da Google pode definir os seus próprios elementos técnicos nas páginas com formulários
públicos. **[JURISTA: necessidade de aviso/consentimento.]**

## B.11 Alterações e contacto

Podemos atualizar esta política; a data da versão em vigor consta no topo e avisaremos as escolas
de alterações relevantes. Contacto: **[EQUIPA]**.

*Versão: rascunho — Data: **[EQUIPA]***

---

# PARTE C — Anexo técnico (a partir do código; para o jurista e para a equipa)

## C.1 Inventário de dados pessoais por tabela

| Tabela | Titular | Campos pessoais |
|---|---|---|
| `aluno` | Aluno | nome_completo, data_nascimento, numero_documento, matricula_interna, usuario_id, `ativo` |
| `foto_perfil_aluno` | Aluno | fotografia (ficheiro, histórico anual) |
| `aluno_documento` | Aluno | anexos livres da escola (BI, certificados, históricos escolares gerados) |
| `matricula`, `matricula_documento`, `pedido_rematricula` | Aluno | turma/ano, estado, documentos da matrícula |
| tabelas do Diário/LMS/Tarefas | Aluno | notas, presenças, respostas a exames e trabalhos, comportamento |
| `responsavel_financeiro_legal`, `aluno_responsavel` | Responsável | nome, telefone, e-mail, numero_documento, parentesco |
| contratos/faturas/pagamentos | Responsável | valores, datas, referência de transferência reportada (texto livre), recibos |
| `professor`, `usuario` | Prof./staff/todos | nome, e-mail, perfil, hash da palavra-passe, estado, e-mail verificado |
| `login_historico` | Todos | **IP**, user-agent, data de cada login |
| `usuario_auditoria` | Todos | ações administrativas sobre contas (quem/quando/o quê) |
| `refresh_token`, `password_reset_token`, `conta_ativacao_token` | Todos | tokens (guardados com hash) e expirações |
| `notificacao` | Todos | mensagens dirigidas ao utilizador |
| `lead_candidato`, `lead_documento`, `mensagem_lead` | Candidato/família | contactos, data de nascimento do candidato, mensagem, documentos, `aceitou_regulamento` |
| comunicados e respostas | Alunos/responsáveis | texto livre e anexos |
| `tenant` | Escola | nome, NIF, IBAN, contactos, morada, logótipo |

## C.2 Lacunas técnicas que a equipa deve decidir (independentes do parecer jurídico)

1. **Não existe página nem link de política de privacidade** na aplicação, nem no registo de escola,
   nem nos formulários públicos. Falta também o **registo/aceitação dos termos** no registo da
   escola e no formulário de candidatura (só existe `aceitou_regulamento`, do regulamento da escola).
2. **Sem rotina de expiração** para `login_historico` (IP/navegador), tokens expirados,
   notificações lidas e leads não convertidos — crescem indefinidamente.
3. **Sem exportação de dados** por titular (acesso/portabilidade): hoje só por pedido manual à equipa.
4. **Sem processo formal de pedido de retificação/oposição** dentro da aplicação.
5. **Texto livre** (comportamento, comunicados, referência de transferência, chat do Prof. Virtual)
   pode conter dados pessoais adicionais — o chat do Prof. Virtual **não é guardado**, mas é enviado
   ao fornecedor de IA enquanto decorre.
6. **Cópias de segurança** contêm todos os dados de todas as escolas durante 14 dias
   (`BACKUP_RETENCAO_DIAS`) — relevante para "apagamento" e para o contrato com o fornecedor de storage.
7. **Sem 2FA** no Super Admin (acesso cross-escola) — relevante para a secção de segurança.
8. Local geográfico de alojamento, storage e backups ainda por decidir/documentar.
9. Nomeação/contacto de um responsável interno para pedidos de titulares.

## C.3 O que já protege os dados (verificável no código)

Isolamento por escola com RLS no Postgres (testado); bcrypt; JWT de 20 min + refresh rotativo com
revogação; rate limiting (login, registo, leads, chat de suporte); reCAPTCHA v3 nos formulários
públicos; RBAC por perfil (no servidor **e** nas rotas do frontend); backups diários fora do
servidor com restauro ensaiado; desativação em vez de eliminação; Sentry com `send_default_pii=False`.
