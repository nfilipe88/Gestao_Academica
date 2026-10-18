"""Gera o par de chaves que cifra os backups da base de dados (ver
app/core/cifra_backup.py).

- chave PÚBLICA → vai para o servidor (BACKUP_CHAVE_PUBLICA no .env:
  caminho para o ficheiro .pem). Só cifra; não serve para ler backups.
- chave PRIVADA → NUNCA vai para o servidor. Guardar fora dele (cofre de
  passwords, pen USB num cofre físico, ...), em pelo menos dois sítios.
  Sem ela, NENHUM backup cifrado com a pública correspondente pode ser
  restaurado — não há recuperação possível.

A chave privada sai protegida por uma frase-passe (pedida aqui, sem eco
no ecrã), que é pedida de novo ao restaurar.

Uso:
    python scripts/gerar_chaves_backup.py --pasta C:\\caminho\\fora\\do\\servidor
"""
import argparse
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.cifra_backup import gerar_par_de_chaves


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pasta", required=True, help="Pasta onde gravar backup_privada.pem e backup_publica.pem")
    args = parser.parse_args()

    pasta = Path(args.pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminho_privada = pasta / "backup_privada.pem"
    caminho_publica = pasta / "backup_publica.pem"
    if caminho_privada.exists() or caminho_publica.exists():
        raise SystemExit(f"Já existem chaves em {pasta} — não as substituo (os backups antigos dependem delas).")

    frase = getpass.getpass("Frase-passe para proteger a chave privada (mín. 12 caracteres): ")
    if len(frase) < 12:
        raise SystemExit("Frase-passe demasiado curta.")
    if getpass.getpass("Repita a frase-passe: ") != frase:
        raise SystemExit("As frases-passe não coincidem.")

    print("A gerar chaves RSA de 4096 bits...")
    pem_privado, pem_publico = gerar_par_de_chaves(frase)
    caminho_privada.write_bytes(pem_privado)
    caminho_publica.write_bytes(pem_publico)

    print(f"\nChave pública: {caminho_publica}")
    print("  → copiar para o servidor e definir BACKUP_CHAVE_PUBLICA=<caminho desse ficheiro> no .env")
    print(f"Chave privada: {caminho_privada}")
    print("  → guardar FORA do servidor, em pelo menos dois sítios. Sem ela e sem a frase-passe,")
    print("    os backups não podem ser restaurados.")


if __name__ == "__main__":
    main()
