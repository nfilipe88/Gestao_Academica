#!/usr/bin/env bash
# Obtém o PRIMEIRO certificado HTTPS (as renovações são automáticas,
# serviço "certbot" do docker-compose.yml). Correr uma vez, no servidor,
# depois de o DNS do domínio já apontar para ele:
#
#   ./primeiro-certificado.sh              # certificado real (Let's Encrypt)
#   ./primeiro-certificado.sh --staging    # ensaio contra o Let's Encrypt de testes
#                                          # (sem limite de pedidos; o browser não confia nele)
#   ./primeiro-certificado.sh --teste-local  # certificado autoassinado, sem Internet
#                                          # (ensaio local em https://localhost)
#
# O problema que isto resolve: o nginx não arranca em 443 sem certificado,
# e o Let's Encrypt precisa do nginx a responder em 80 para validar o
# domínio. Por isso: certificado provisório → nginx arranca → apaga o
# provisório → pede o verdadeiro → recarrega o nginx.
set -euo pipefail
cd "$(dirname "$0")"

ler_env() { grep -E "^$1=" .env | tail -1 | cut -d= -f2- | tr -d '\r'; }
DOMINIO="$(ler_env DOMINIO)"
EMAIL="$(ler_env EMAIL_CERTIFICADO)"
MODO="${1:-}"
[ -n "$DOMINIO" ] || { echo "DOMINIO em falta no .env"; exit 1; }

PASTA="/etc/letsencrypt/live/$DOMINIO"

certificado_provisorio() {
    docker compose run --rm --entrypoint sh certbot -c "
        mkdir -p '$PASTA' &&
        openssl req -x509 -nodes -newkey rsa:2048 -days $1 \
            -keyout '$PASTA/privkey.pem' -out '$PASTA/fullchain.pem' -subj '/CN=$DOMINIO'"
}

if [ "$MODO" = "--teste-local" ]; then
    echo "A criar certificado autoassinado para $DOMINIO (só para ensaio local)..."
    certificado_provisorio 30
    echo "Feito. Arranque com: docker compose up -d"
    exit 0
fi

[ -n "$EMAIL" ] || { echo "EMAIL_CERTIFICADO em falta no .env"; exit 1; }

echo "1/4 Certificado provisório para o nginx conseguir arrancar..."
certificado_provisorio 1

echo "2/4 A arrancar o nginx..."
docker compose up -d nginx

echo "3/4 A pedir o certificado ao Let's Encrypt para $DOMINIO..."
docker compose run --rm --entrypoint sh certbot -c "
    rm -rf '/etc/letsencrypt/live/$DOMINIO' '/etc/letsencrypt/archive/$DOMINIO' '/etc/letsencrypt/renewal/$DOMINIO.conf'"
EXTRA=""
[ "$MODO" = "--staging" ] && EXTRA="--staging"
docker compose run --rm --entrypoint certbot certbot certonly --webroot -w /var/www/certbot \
    -d "$DOMINIO" --email "$EMAIL" --agree-tos --no-eff-email --rsa-key-size 4096 $EXTRA

echo "4/4 A recarregar o nginx com o certificado verdadeiro..."
docker compose exec nginx nginx -s reload
echo "Feito: https://$DOMINIO"
