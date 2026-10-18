"""
Cifra dos backups da base de dados (ver app/core/backup.py) com um par
de chaves: o servidor só tem a chave PÚBLICA (cifra, nunca decifra); a
chave PRIVADA fica fora do servidor, guardada por quem administra a
plataforma (gerada por scripts/gerar_chaves_backup.py, protegida por
frase-passe). Quem comprometer o servidor ou o bucket leva só ficheiros
ilegíveis — um dump da base inclui dados pessoais de menores.

Esquema híbrido (o RSA só cifra poucos bytes): cada backup tem uma
chave AES-256 nova, aleatória, cifrada com RSA-OAEP (SHA-256); o dump
em si vai em AES-256-GCM, por blocos de 16 MB — o GCM autentica cada
bloco, o número do bloco e a marca de "último bloco" entram nos dados
associados, por isso um ficheiro truncado, reordenado ou alterado é
recusado ao decifrar (nunca restaura dados corrompidos em silêncio).

Formato do ficheiro:
    MAGIC | len(chave cifrada) (2 bytes) | chave cifrada | prefixo do nonce (8 bytes)
    | repetido por bloco: len(bloco cifrado) (4 bytes) | bloco cifrado (com tag GCM)
"""
import os
import struct

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"GABACKUP1\n"
_TAMANHO_BLOCO = 16 * 1024 * 1024
_OAEP = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()), algorithm=hashes.SHA256(), label=None)


class BackupInvalido(Exception):
    """Ficheiro que não é um backup cifrado válido, foi alterado/truncado,
    ou a chave privada não é a que corresponde à pública usada."""


def carregar_chave_publica(valor: str) -> rsa.RSAPublicKey:
    """`valor` é o PEM em si (com "\\n" literais, como fica numa linha de
    .env) ou o caminho para um ficheiro .pem."""
    if "-----BEGIN" in valor:
        pem = valor.replace("\\n", "\n").encode()
    else:
        with open(valor, "rb") as ficheiro:
            pem = ficheiro.read()
    chave = serialization.load_pem_public_key(pem)
    if not isinstance(chave, rsa.RSAPublicKey) or chave.key_size < 3072:
        raise ValueError("A chave pública de backup tem de ser RSA com pelo menos 3072 bits.")
    return chave


def carregar_chave_privada(caminho: str, frase_passe: str | None) -> rsa.RSAPrivateKey:
    with open(caminho, "rb") as ficheiro:
        pem = ficheiro.read()
    return serialization.load_pem_private_key(pem, password=frase_passe.encode() if frase_passe else None)


def _nonce(prefixo: bytes, indice: int) -> bytes:
    return prefixo + struct.pack(">I", indice)


def _aad(indice: int, ultimo: bool) -> bytes:
    return MAGIC + struct.pack(">I?", indice, ultimo)


def cifrar(conteudo: bytes, chave_publica: rsa.RSAPublicKey) -> bytes:
    chave_aes = AESGCM.generate_key(bit_length=256)
    chave_cifrada = chave_publica.encrypt(chave_aes, _OAEP)
    prefixo_nonce = os.urandom(8)
    aes = AESGCM(chave_aes)

    partes = [MAGIC, struct.pack(">H", len(chave_cifrada)), chave_cifrada, prefixo_nonce]
    blocos = [conteudo[i:i + _TAMANHO_BLOCO] for i in range(0, len(conteudo), _TAMANHO_BLOCO)] or [b""]
    for indice, bloco in enumerate(blocos):
        cifrado = aes.encrypt(_nonce(prefixo_nonce, indice), bloco, _aad(indice, indice == len(blocos) - 1))
        partes += [struct.pack(">I", len(cifrado)), cifrado]
    return b"".join(partes)


def decifrar(dados: bytes, chave_privada: rsa.RSAPrivateKey) -> bytes:
    if not dados.startswith(MAGIC):
        raise BackupInvalido("Não é um backup cifrado desta plataforma.")
    try:
        pos = len(MAGIC)
        (tamanho_chave,) = struct.unpack_from(">H", dados, pos)
        pos += 2
        chave_aes = chave_privada.decrypt(dados[pos:pos + tamanho_chave], _OAEP)
        pos += tamanho_chave
        prefixo_nonce = dados[pos:pos + 8]
        pos += 8
        aes = AESGCM(chave_aes)

        resultado, indice = [], 0
        while pos < len(dados):
            (tamanho,) = struct.unpack_from(">I", dados, pos)
            pos += 4
            cifrado = dados[pos:pos + tamanho]
            pos += tamanho
            ultimo = pos >= len(dados)
            resultado.append(aes.decrypt(_nonce(prefixo_nonce, indice), cifrado, _aad(indice, ultimo)))
            indice += 1
        if indice == 0:
            raise BackupInvalido("Backup sem conteúdo.")
        return b"".join(resultado)
    except BackupInvalido:
        raise
    except Exception as erro:
        raise BackupInvalido(
            "Não foi possível decifrar: o ficheiro foi alterado/truncado ou a chave privada não corresponde."
        ) from erro


def gerar_par_de_chaves(frase_passe: str | None) -> tuple[bytes, bytes]:
    """(PEM privado, PEM público). O privado sai cifrado com a frase-passe."""
    privada = rsa.generate_private_key(public_exponent=65537, key_size=4096)
    cifra_pem = (
        serialization.BestAvailableEncryption(frase_passe.encode()) if frase_passe else serialization.NoEncryption()
    )
    pem_privado = privada.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, cifra_pem)
    pem_publico = privada.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem_privado, pem_publico
