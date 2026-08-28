"""
Validações partilhadas entre vários schemas Pydantic — hoje só a força
da palavra-passe, usada em todos os pontos da app onde uma é definida
(registo de escola, secretaria, professor, aluno/responsável, tenant
pelo Super Admin, redefinição de palavra-passe).

Política deliberadamente moderada (Fase 5 — segurança de sessão): exige
maiúscula + minúscula + dígito, mas não caráter especial nem
comprimento superior a 8 — o público desta plataforma inclui pessoal
administrativo de escolas sem hábito de gestores de palavras-passe, e
uma política demasiado rígida só produz mais pedidos de suporte e
palavras-passe anotadas em papel, não mais segurança real.
"""
import re


def validar_forca_senha(valor: str) -> str:
    if not re.search(r"[A-Z]", valor):
        raise ValueError("A palavra-passe tem de ter pelo menos uma letra maiúscula.")
    if not re.search(r"[a-z]", valor):
        raise ValueError("A palavra-passe tem de ter pelo menos uma letra minúscula.")
    if not re.search(r"\d", valor):
        raise ValueError("A palavra-passe tem de ter pelo menos um número.")
    return valor
