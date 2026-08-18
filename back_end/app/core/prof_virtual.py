"""
Prof. Virtual — assistente de IA da plataforma, com dois papéis distintos:

1. Tutor do aluno (perguntar_prof_virtual, usado em app/api/v1/portal.py):
   ajuda o aluno a raciocinar sobre um material de aula concreto, não
   resolve o problema por ele. O botão de ajuda vive sempre "dentro" de
   um material (nunca solto), para o modelo ter o contexto real do que
   está a ser estudado — sem isso a IA responderia em abstrato, sem
   saber que "Equações do 2º Grau" desta escola específica cobre a
   fórmula resolvente mas não a factorização, por exemplo.

2. Assistente de redação do professor (sugerir_conteudo_aula, usado em
   app/api/v1/lms.py): a partir do título que o professor escreveu,
   sugere um rascunho do campo "Conteúdo" do material — o professor
   revê e edita antes de publicar, a IA nunca publica sozinha.

3. Gerador de trilhas de recuperação (gerar_trilha_recuperacao, usado
   em app/cruds/indicadores.py): a partir do perfil de risco de um
   aluno sinalizado pelo motor de risco de evasão (regras, não IA —
   ver obter_risco_evasao), sugere um plano de ações concretas para a
   Secretaria/Gestor conduzirem com a família. A IA aqui é consultiva,
   não decide nada sozinha: o resultado fica sempre gravado para
   revisão humana antes de ser posto em prática.

Chat do aluno sem persistência em BD nesta primeira versão: o histórico
viaja no próprio pedido (ver ProfVirtualPerguntaCreate) — refrescar a
página perde a conversa. Suficiente para testar o conceito; se ficar,
persistir passa a fazer sentido para retomar conversas e para a
direção poder ver que dúvidas os alunos têm mais.

Nunca regista a ANTHROPIC_API_KEY nos logs.
"""
import logging
import os

from anthropic import AsyncAnthropic, APIStatusError
from dotenv import load_dotenv
from fastapi import HTTPException

from app.schemas.lms import MensagemProfVirtual

load_dotenv()

logger = logging.getLogger("prof_virtual")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODELO = os.getenv("PROF_VIRTUAL_MODELO", "claude-sonnet-5")

_cliente: AsyncAnthropic | None = AsyncAnthropic(api_key=ANTHROPIC_API_KEY) if ANTHROPIC_API_KEY else None


def _construir_prompt_sistema(titulo_material: str, corpo_material: str, nome_objetivo: str | None) -> str:
    contexto_objetivo = f'\nEsta aula está catalogada sob o objetivo de aprendizagem "{nome_objetivo}".' if nome_objetivo else ""
    return f"""És o Prof. Virtual, um assistente de estudo para alunos do ensino básico/secundário.

A tua função é ajudar o aluno a RACIOCINAR sobre a matéria — não é dar-lhe a resposta final feita.
Regras que segues sempre:
- Faz perguntas que guiem o raciocínio antes de confirmar ou explicar um conceito.
- Se o aluno pedir a resposta direta de um exercício, não a dês de imediato: pergunta o que ele já tentou, aponta o próximo passo, e só confirma quando ele chegar lá (ou tiver tentado a sério e continuar preso).
- Podes confirmar se um raciocínio está certo, corrigir um erro conceptual, e dar pequenas explicações — mas mantém sempre o aluno a pensar, não a copiar.
- Responde em português europeu, num tom simples, paciente e encorajador, adequado à idade escolar.
- Mantém-te SEMPRE dentro do âmbito do material de aula abaixo. Se o aluno perguntar algo sem relação nenhuma com esta matéria, traz a conversa de volta ao tema com delicadeza.
- Respostas curtas (2-5 frases) — isto é uma conversa, não um manual.

Material de aula em estudo — "{titulo_material}":
---
{corpo_material}
---
{contexto_objetivo}"""


async def perguntar_prof_virtual(
    titulo_material: str,
    corpo_material: str,
    nome_objetivo: str | None,
    historico: list[MensagemProfVirtual],
    pergunta: str
) -> str:
    if _cliente is None:
        raise HTTPException(
            status_code=503,
            detail="O Prof. Virtual ainda não está configurado nesta instituição — falta a chave da API de IA no servidor."
        )

    mensagens = [
        {"role": "user" if m.papel == "aluno" else "assistant", "content": m.texto}
        for m in historico
    ]
    mensagens.append({"role": "user", "content": pergunta})

    try:
        resposta = await _cliente.messages.create(
            model=MODELO,
            max_tokens=500,
            system=_construir_prompt_sistema(titulo_material, corpo_material, nome_objetivo),
            messages=mensagens
        )
    except APIStatusError as erro:
        logger.error("Prof. Virtual: falha na API da Anthropic (status %s)", erro.status_code)
        raise HTTPException(status_code=502, detail="O Prof. Virtual não conseguiu responder agora — tenta novamente daqui a pouco.")

    return "".join(bloco.text for bloco in resposta.content if bloco.type == "text").strip()


def _construir_prompt_sistema_sugestao(nome_disciplina: str, nome_turma: str, nome_objetivo: str | None, instrucoes: str | None) -> str:
    contexto_objetivo = f'\nEste material está catalogado sob o objetivo de aprendizagem "{nome_objetivo}" — o texto deve servir esse objetivo.' if nome_objetivo else ""
    contexto_instrucoes = f"\nInstruções extra do professor para esta sugestão: {instrucoes}" if instrucoes else ""
    return f"""És um assistente de redação pedagógica para professores de {nome_disciplina}, a preparar um material de aula para a turma "{nome_turma}".

A tua função é escrever um rascunho do CONTEÚDO de um material de aula, a partir do título dado pelo professor. Este texto vai ser lido diretamente pelos alunos e serve também de base ao Prof. Virtual (um tutor de IA) para os ajudar a estudar — por isso tem de ser claro, correto e autossuficiente.
Regras que segues sempre:
- Escreve em português europeu, num registo claro e didático, adequado à disciplina e à turma indicadas.
- Explica o conceito com progressão lógica (do mais simples para o mais complexo), usando exemplos quando ajudam a fixar a ideia.
- Não inventes factos, fórmulas ou datas — se não tiveres a certeza de algo específico, mantém-te no essencial e correto.
- O professor vai rever e editar este rascunho antes de publicar — produz um bom ponto de partida, não precisa de estar perfeito.
- Devolve APENAS o texto do conteúdo, sem título, sem comentários sobre o que fizeste, sem markdown de cabeçalhos.
- Comprimento razoável para um material de aula (tipicamente 3-8 parágrafos, conforme o tema).
{contexto_objetivo}{contexto_instrucoes}"""


async def sugerir_conteudo_aula(
    titulo: str,
    nome_disciplina: str,
    nome_turma: str,
    nome_objetivo: str | None,
    instrucoes: str | None
) -> str:
    if _cliente is None:
        raise HTTPException(
            status_code=503,
            detail="O Prof. Virtual ainda não está configurado nesta instituição — falta a chave da API de IA no servidor."
        )

    try:
        resposta = await _cliente.messages.create(
            model=MODELO,
            max_tokens=1500,
            system=_construir_prompt_sistema_sugestao(nome_disciplina, nome_turma, nome_objetivo, instrucoes),
            messages=[{"role": "user", "content": f'Título do material: "{titulo}"'}]
        )
    except APIStatusError as erro:
        logger.error("Prof. Virtual (sugestão de conteúdo): falha na API da Anthropic (status %s)", erro.status_code)
        raise HTTPException(status_code=502, detail="O Prof. Virtual não conseguiu gerar uma sugestão agora — tenta novamente daqui a pouco.")

    return "".join(bloco.text for bloco in resposta.content if bloco.type == "text").strip()


def _construir_prompt_sistema_trilha() -> str:
    return """És um especialista em sucesso escolar e apoio socioeducativo, a ajudar a Secretaria/Direção de uma escola a montar planos de recuperação para alunos sinalizados por um motor de risco de evasão baseado em regras (não é análise tua — os fatores já vêm calculados e são factuais).

A tua função é traduzir esses fatores num plano de ação concreto e acionável — não é diagnosticar nem repetir os números que já te deram.
Regras que segues sempre:
- Responde em português europeu, em markdown simples (títulos com ##, listas com -), sem introduções nem despedidas.
- Estrutura sempre em 3 secções: "## Ações imediatas" (1-2 semanas), "## Acompanhamento" (resto do período), "## Envolvimento da família" (o que comunicar aos encarregados de educação e como).
- Cada ação tem de ser concreta e atribuível (quem faz o quê), nunca genérica ("melhorar a atenção do aluno" não serve; "Diretor de Turma agenda reunião com o encarregado de educação até [prazo]" serve).
- Baseia as sugestões só nos fatores de risco fornecidos — não inventes causas (problemas familiares, saúde, etc.) que não foram dados.
- Não sugiras nada que exija orçamento ou recursos que uma escola comum tipicamente não tem (ex.: psicólogo a tempo inteiro) — sugere o que é razoável pedir à estrutura já existente (Diretor de Turma, Professores, Secretaria).
- Comprimento: conciso, tipicamente 150-300 palavras no total."""


async def gerar_trilha_recuperacao(
    nome_aluno: str,
    nome_turma: str,
    nivel_risco: str,
    pontuacao_risco: int,
    fatores: list[str],
    taxa_falta: float,
    media_notas: float | None,
) -> str:
    if _cliente is None:
        raise HTTPException(
            status_code=503,
            detail="O Prof. Virtual ainda não está configurado nesta instituição — falta a chave da API de IA no servidor."
        )

    media_texto = f"{media_notas}" if media_notas is not None else "sem notas lançadas ainda"
    pedido = f"""Aluno: {nome_aluno} (turma {nome_turma})
Nível de risco: {nivel_risco} (pontuação {pontuacao_risco}/100)
Taxa de faltas: {taxa_falta}%
Média de notas: {media_texto}
Fatores de risco identificados:
{chr(10).join(f"- {fator}" for fator in fatores)}

Gera o plano de recuperação para este aluno."""

    try:
        resposta = await _cliente.messages.create(
            model=MODELO,
            max_tokens=1000,
            system=_construir_prompt_sistema_trilha(),
            messages=[{"role": "user", "content": pedido}]
        )
    except APIStatusError as erro:
        logger.error("Prof. Virtual (trilha de recuperação): falha na API da Anthropic (status %s)", erro.status_code)
        raise HTTPException(status_code=502, detail="Não foi possível gerar a trilha de recuperação agora — tenta novamente daqui a pouco.")

    return "".join(bloco.text for bloco in resposta.content if bloco.type == "text").strip()
