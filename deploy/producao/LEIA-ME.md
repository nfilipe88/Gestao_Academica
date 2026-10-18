# Pôr a plataforma em produção

Receita para **um servidor Linux** (VPS) com Docker. Monta, com um só comando:

| Serviço | O que é | Acessível da Internet? |
|---|---|---|
| `nginx` | Entrada única, HTTPS (Let's Encrypt), cabeçalhos de segurança, HSTS | **Sim** — só as portas 80 e 443 |
| `certbot` | Renova o certificado HTTPS sozinho (2× por dia verifica) | Não |
| `frontend` | Angular (SSR) | Não |
| `backend` | FastAPI (corre as migrações ao arrancar) + jobs diários (backup 03:00, …) | Não |
| `postgres` | Base de dados, com as roles do RLS (isolamento entre escolas) | Não |
| `redis` | Sessões revogadas, limites de tentativas, fila de e-mails — com password | Não |

Ficheiros (logótipos, anexos, documentos) e backups vão para **storage S3 externo** ao
servidor: se o servidor se perder, os ficheiros e as cópias de segurança não se perdem com ele.

## 1. Antes de começar

- **Servidor**: Ubuntu 24.04 LTS (ou outra distribuição com Docker), 2–4 vCPU, 4–8 GB de RAM,
  40 GB de disco. Acesso SSH só por chave.
- **Firewall do fornecedor**: abrir só 22 (SSH), 80 e 443.
- **Domínio**: um registo DNS `A` (ex.: `plataforma.escola.ao`) a apontar para o IP do servidor.
- **S3** (AWS S3, Wasabi, Backblaze B2, Cloudflare R2, …), com **dois buckets**:
  1. ficheiros da aplicação — credenciais de leitura e escrita;
  2. backups — credenciais **só de escrita** (PutObject) e uma **regra de ciclo de vida** que apaga
     objetos com mais de 14 dias. Se o fornecedor permitir, ligar versionamento / Object Lock.
- **SMTP** (obrigatório: ativação de contas, recuperação de palavra-passe, códigos da verificação
  em dois passos).

## 2. Instalação

```bash
# No servidor
curl -fsSL https://get.docker.com | sh
git clone https://github.com/nfilipe88/Gestao_Academica.git
cd Gestao_Academica/deploy/producao
cp .env.exemplo .env && chmod 600 .env
nano .env        # preencher tudo — os comentários explicam cada valor
```

**Chaves dos backups** — gerar no **seu computador**, nunca no servidor:

```bash
cd back_end
python scripts/gerar_chaves_backup.py --pasta <pasta fora do servidor>
```

Copiar **só** `backup_publica.pem` para o servidor, em `deploy/producao/segredos/backup_publica.pem`.
A privada e a frase-passe ficam consigo, em pelo menos dois sítios: sem elas nenhum backup se
restaura.

**Certificado HTTPS e arranque** (o DNS já tem de apontar para o servidor):

```bash
./primeiro-certificado.sh --staging   # opcional: ensaio sem gastar pedidos do Let's Encrypt
./primeiro-certificado.sh             # certificado real
docker compose up -d --build
```

## 3. Verificar antes de abrir às escolas

```bash
docker compose ps                                        # tudo "healthy"/"running"
docker compose exec backend python scripts/verificar_env_producao.py --ambiente   # sem bloqueadores
docker compose exec backend python scripts/backup_manual.py   # tem de sair um .dump.enc
docker compose exec backend python seed_super_admin.py   # conta Super Admin (pede os dados)
```

- Abrir `https://<domínio>`: cadeado válido; `http://` redireciona para `https://`.
- Ensaio de restauro no **seu computador** (com a chave privada e credenciais de leitura do
  bucket de backups) — ver `README.md`, secção "Backup e Restauro".
- Checklist completa: `CHECKLIST_ENV_PRODUCAO.md` e `RUNBOOK.md` na raiz do repositório.

## 4. Atualizar para uma versão nova

```bash
cd Gestao_Academica && git pull
cd deploy/producao && docker compose up -d --build
```

As migrações da base de dados correm sozinhas ao arrancar o `backend`. Antes de uma atualização
com migrações grandes, tirar um backup extra (`scripts/backup_manual.py`, acima).

## 5. Operação do dia a dia

```bash
docker compose logs -f backend          # registos (rodados automaticamente: 5 × 20 MB por serviço)
docker compose restart backend
docker compose exec postgres psql -U postgres academic_db
```

## Ensaio local (antes do servidor real)

Para experimentar a receita inteira num computador com Docker, sem domínio nem S3: o ficheiro
`docker-compose.ensaio-local.yml` acrescenta um SeaweedFS a fazer de S3 (com um utilizador só de
escrita para os backups, `ensaio-local/s3.json`).

```bash
cd deploy/producao
cp .env.exemplo .env      # DOMINIO=localhost; S3 em http://s3:8333 com as credenciais de ensaio-local/s3.json
./primeiro-certificado.sh --teste-local
docker compose -f docker-compose.yml -f docker-compose.ensaio-local.yml up -d --build
# https://localhost (certificado autoassinado — o browser avisa, é normal no ensaio)
```

## O que esta receita NÃO cobre

- **Alta disponibilidade**: um só servidor; se cair, a plataforma fica em baixo até voltar.
  Recuperação: servidor novo + esta receita + restauro do último backup (perde-se até ~24 h).
- **Réplica da base de dados** e balanceamento entre vários servidores.
- **Monitorização da máquina** (disco cheio, CPU): os erros da aplicação vão para o Sentry, mas
  o servidor em si precisa da monitorização do fornecedor.
