# Avaliação de prontidão para produção — Gestão Académica

Data: 2026-09-24 · Commit avaliado: `f27db61` (`main`)

**Como esta avaliação foi feita (e os seus limites).** Combina o que foi *executado* (suites de testes,
ensaio geral, teste de fumo, backup/restauro reais, verificações no browser durante o desenvolvimento) com
uma *leitura do código e pesquisas por termos*. Onde escrevo "não encontrei", significa que a pesquisa
não achou — não que se provou a ausência. Não fiz uma auditoria ecrã-a-ecrã de todas as 23 áreas do
front-end, nem testes de utilizadores reais, nem revisão jurídica ou fiscal (não sou jurista nem contabilista).

**Tamanho:** ~23,7 mil linhas de Python, ~29,8 mil de TypeScript/HTML, 283 endpoints, 70 migrações,
23 áreas funcionais, 5 perfis (Super Admin, Gestor, Secretaria, Professor, Aluno/Responsável).

---

## Parte 1 — Relatório realista

### O que está sólido (com evidência)
| Área | Evidência |
|---|---|
| Isolamento entre escolas | RLS no Postgres + filtro no código; `test_rls_isolamento.py`; 3 roles distintos |
| Testes de backend | 344 passam, 1 ignorado (última corrida completa, 14 min) |
| Fluxo ponta a ponta | Ensaio geral 27/27: registo → ativação → configuração → curso/turma → aluno → matrícula → contrato/faturas → pagamento → notas → documentos → portal |
| Desempenho | ~2340 alunos: tudo < 300 ms exceto o PDF de Indicadores (1,25 s) |
| Dados e retenção | Alunos/escolas **desativam-se, nunca se eliminam** (retenção de 15 anos); limpeza automática só de dados operacionais e candidaturas não convertidas (15 dias) |
| Backup | Backup real para S3/MinIO + restauro para base nova, 76 tabelas / 3664 linhas iguais |
| Segurança de acesso | RBAC por perfil no backend **e** guards de rota no front-end; rate limiting; reCAPTCHA v3; revogação de sessões |
| Modelo de negócio SaaS | Planos, limite de alunos aplicado, isenção pelo Super Admin, período de teste, licenças |
| Privacidade | Página `/privacidade`, aceitação dos termos (registo e escolas criadas pelo Super Admin), exportação de dados por titular |
| Regras de negócio no código | RN01–RN08 referenciadas (~127 ocorrências); juros/multa derivados sem escrever na BD (RN02); régua de cobrança (RN04) |

### Cobertura funcional
Académico, diário de classe (frequência, notas, avaliações, períodos com trancagem), financeiro
(contratos, faturas, juros/multa, recibos, despesas, propinas), portal do aluno/responsável, CRM com
funil e captação pública, importação em massa, documentos PDF com modelos personalizáveis, horários,
comunicados com respostas, transferências, rematrícula, LMS com exames, indicadores/BI, auditoria,
site público por escola. É um âmbito largo para o tamanho da equipa.

### Fluxos e utilização
- **Onboarding controlado** funciona: Super Admin cria a escola → Gestor aceita os termos → é obrigado a
  configurar o ano letivo antes de qualquer outra coisa.
- **Autoatendimento** (registo → e-mail de ativação) só funciona com SMTP configurado — hoje não está.
- Interface em português, com estados de erro inline, Tailwind responsivo (39 de 59 templates usam
  breakpoints), guards que redirecionam cada perfil para a sua página inicial.

### Riscos aceites já documentados
Instância única sem alta disponibilidade · pagamentos por transferência com conciliação manual · sem 2FA no
Super Admin · dashboards quase em série sob concorrência (9 pedidos paralelos = 1,1 s) · faturação não
certificada (o recibo avisa que não tem valor fiscal).

---

## Parte 2 — Relatório crítico

### A. Bloqueadores antes da primeira escola real (todos externos ao código)
1. **SMTP** não configurado → nenhuma escola nova consegue ativar conta.
2. **`JWT_SECRET_KEY`** de produção: a app arranca com qualquer valor, inclusive o placeholder; só o
   verificador manual o acusa. Um deploy esquecido seria silenciosamente inseguro.
3. **S3 real**: sem bucket fora do servidor, o backup fica no mesmo disco.
4. **Nenhum backup agendado (03:00) foi observado**; só o manual foi provado.
5. **Política de privacidade é rascunho** sem revisão jurídica; prazos de 30/365/180 dias são valores
   técnicos por confirmar; a base legal e o registo/obrigações perante a autoridade de proteção de dados
   angolana ficam por confirmar com um jurista.
6. **RUNBOOK sem contactos** nem responsável de piloto definidos.

### B. Lacunas funcionais e de regras de negócio (as mais importantes)
1. **Resultado final do aluno / transição de classe.** Não encontrei cálculo de aprovado/reprovado por
   aluno no fim do ano — só uma nota mínima única por escola que "marca" Aprovado/Reprovado no Boletim e
   Indicadores. Não encontrei fecho de ano letivo, nem regras de recurso/exame de recurso ligadas ao
   resultado, nem limite de faltas que reprove ou alerte. Numa escola real é o momento crítico do ano.
2. **Aderência ao sistema de avaliação oficial.** Não encontrei a terminologia/estrutura habitual do
   ensino angolano (ex.: MAC/NPP/NPT ou equivalentes) no modelo de notas; há trimestres e tipos de
   avaliação configuráveis, o que ajuda, mas **não confirmei** que o cálculo da nota final corresponde ao
   regulamento. Tem de ser validado por um professor/direção de uma escola real.
3. **Faturação fiscal.** Recibos sem valor fiscal. Se as escolas estiverem obrigadas a emitir documentos de
   faturação certificados, a plataforma **sozinha não cobre isso**. É decisão de conformidade a confirmar
   com um contabilista/advogado — pode ser bloqueador comercial mesmo sem falha técnica.
4. **Pagamentos.** O PayPal não aceita Kwanza; a via real é transferência com conciliação manual. Sem
   referência de pagamento local (ex.: Multicaixa) nem conciliação automática, a Secretaria confere
   extratos à mão — não escala com muitas escolas.
5. **Dados de teste sobrantes** na BD de desenvolvimento (responsável/contrato do Carlos Neto, 51 alunos,
   ~45 escolas de teste): não afeta produção, mas a BD de produção tem de nascer limpa.

### C. Qualidade e engenharia
1. **Front-end sem testes automatizados relevantes**: 1 ficheiro de testes (2 casos) para ~30 mil linhas.
   Qualquer regressão de interface só se apanha à mão.
2. **Suite de backend lenta** (14 min, serial) — atrasa cada ciclo de correção.
3. **Sessão no `localStorage`** (access + refresh token): uma falha XSS roubaria sessões de 7 dias.
   Mitigado por tokens curtos e revogação, mas é o ponto fraco clássico.
4. **Sem 2FA** para o Super Admin, que vê todas as escolas.
5. **Instância única**; limitador de tentativas em memória sem Redis (não partilhado se houver 2 instâncias).
6. **Concorrência**: os dashboards comportam-se quase em série; a validar antes de dezenas de escolas.
7. **Capacidade testada só com 1 tenant grande**, não com muitas escolas em simultâneo.

### D. Utilização (user-friendly) — o que não está provado
- **Acessibilidade fraca**: cerca de 8 atributos `aria`/`role` em 59 templates; o `index.html` declara
  `lang="en"` numa aplicação em português (afeta leitores de ecrã e correção ortográfica).
- **Sem utilizadores reais**: nunca foi testada por um secretário, professor ou encarregado de educação
  sem acompanhamento. O risco de fricção (muitos separadores, terminologia, mensagens de erro técnicas)
  só se descobre assim.
- **Sem ajuda integrada / tour / documentação de utilizador**; o Suporte Virtual depende de chave externa.
- **Telemóvel**: layouts responsivos existem, mas não foi feita verificação sistemática nos fluxos de
  Professor (lançar notas/faltas) e Encarregado, que são os mais usados em telemóvel.
- **Estados vazios** presentes em apenas ~19 templates; várias listas podem aparecer "em branco".
- **Operação dependente de manutenção manual**: backend sem `--reload`/supervisor definido, reinício manual.

---

## Veredicto

**Não está pronto para entrar em produção aberta (auto-registo e várias escolas).**

**Está pronto para um piloto supervisionado com UMA escola**, criada pelo Super Admin, **depois de**
cumprir os 6 bloqueadores da secção A — todos configuração/decisão, nenhum exige reescrever código.

O que separa "piloto" de "produção a sério" não é infraestrutura, é validação real:
1. Um professor e um secretário de uma escola a usar o fluxo completo, incluindo **fim de trimestre e
   fim de ano** (lacuna B1/B2).
2. Parecer jurídico da política de privacidade e da questão fiscal (A5, B3).
3. Testes automáticos de front-end nos fluxos críticos e uma passagem de acessibilidade.
4. Um mês de backups agendados observados e um restauro ensaiado a partir deles.

Sugestão de ordem: A (1 semana, configuração) → piloto com 1 escola durante um trimestre completo →
corrigir B1/B2/C1 com o que o piloto revelar → só então abrir a mais escolas.
