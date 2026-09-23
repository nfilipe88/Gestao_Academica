// Alinhado com app/api/v1/lms.py — materiais de aula + banco de questões + exames.

export interface MaterialAula {
  id: string;
  turma_id: string;
  disciplina_id: string;
  titulo: string;
  corpo: string;
  objetivo_aprendizagem_id: string | null;
  publicado: boolean;
  data_criacao: string;
}

// ==========================================
// BANCO DE QUESTÕES
// ==========================================
export type TipoQuestaoLms = 'ESCOLHA_MULTIPLA' | 'VERDADEIRO_FALSO' | 'ABERTA';

export interface LmsQuestao {
  id: string;
  disciplina_id: string;
  enunciado: string;
  tipo: TipoQuestaoLms;
  opcoes: string[];
  resposta_correta: string;
  valor: number;
}

// ==========================================
// EXAMES (motor online) — um GRUPO de 1+ VARIANTES (Variante A/B/C,
// perguntas genuinamente diferentes, não só ordem baralhada), ligado
// desde a criação a uma Avaliacao do Diário. Só Gestor/Secretaria
// consegue INICIAR um grupo — é esse clique que abre aos alunos e
// distribui cada um por round-robin entre as variantes.
// ==========================================
export type Modalidade = 'PRESENCIAL' | 'REMOTO';

// Uma variante individual, tal como devolvida por GET /alocacoes/{id}/grupos-exame.
export interface LmsExameVariante {
  exame_id: string;
  letra_variante: string;
}

export interface LmsGrupoExame {
  grupo_id: string;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  duracao_minutos: number;
  modalidade: Modalidade;
  publicado: boolean;
  iniciado: boolean;
  iniciado_em: string | null;
  avaliacao_id: string | null;
  variantes: LmsExameVariante[];
}

// Detalhe com gabarito de UMA variante — só para o professor/staff (ver obter_exame_com_gabarito).
export interface LmsExameDetalhe {
  id: string;
  titulo: string;
  data_inicio: string;
  data_fim: string;
  duracao_minutos: number;
  baralhar_perguntas: boolean;
  publicado: boolean;
  grupo_id: string;
  letra_variante: string;
  modalidade: Modalidade;
  iniciado: boolean;
  perguntas: LmsQuestao[];
}

// Correção manual guardada por questão ABERTA (ver LMSTentativaExame.correcoes_manuais).
export interface LmsCorrecaoManual {
  pontos: string;
  comentario: string | null;
}

export interface LmsResultadoAlunoExame {
  matricula_id: string;
  nome_aluno: string;
  exame_id: string;
  // AGUARDA_CORRECAO: submetida mas com ≥1 questão ABERTA ainda por pontuar.
  status: 'EM_CURSO' | 'SUBMETIDA' | 'AGUARDA_CORRECAO';
  nota_obtida: number | null;
  nota_maxima: number | null;
  eventos_suspeitos: number;
  data_inicio: string;
  data_submissao: string | null;
  corrigida_finalizada: boolean;
  correcoes_manuais: Record<string, LmsCorrecaoManual>;
  corrigido_por_usuario_id: string | null;
  corrigido_em: string | null;
  // Respostas em bruto do aluno — usadas para corrigir questões ABERTA (ver "Corrigir" no Diário).
  respostas: Record<string, string>;
  // Só presente quando vem de GET /grupos-exame/{id}/resultados (agregado) — ver carregarResultadosGrupo.
  letra_variante?: string;
}

// Payload de POST /exames/{exame_id}/tentativas/{matricula_id}/corrigir —
// cobre corrigir questões ABERTA pendentes e/ou sobrescrever o total
// (caso "prova presencial, o professor corrige sempre").
export interface LmsCorrecaoQuestaoInput {
  questao_id: string;
  pontos: number;
  comentario: string | null;
}

export interface LmsCorrigirTentativaInput {
  correcoes: LmsCorrecaoQuestaoInput[];
  nota_obtida_override: number | null;
}

// Quem está atribuído a cada variante (ver GET /grupos-exame/{id}/atribuicoes) —
// alimenta a tabela de reatribuição manual do Gestor. Vazio antes do INICIAR.
export interface LmsAtribuicaoVariante {
  matricula_id: string;
  nome_aluno: string;
  exame_id: string;
  letra_variante: string;
  atribuido_manualmente: boolean;
}
