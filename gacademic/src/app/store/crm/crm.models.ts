// Alinhado com app/api/v1/crm.py.

export interface FunilEtapa {
  id: string;
  ordem: number;
  nome_etapa: string;
  eh_etapa_ganho: boolean;
}

export interface LeadCandidato {
  id: string;
  nome_responsavel: string;
  email_contato: string | null;
  telefone: string | null;
  nome_aluno_candidato: string;
  data_nascimento_candidato: string | null;
  curso_interesse_id: string | null;
  origem_lead: string;
  data_entrada: string;
}

export interface OportunidadeCRM {
  id: string;
  etapa_id: string;
  valor_estimado_anual: number | null;
  data_fecho_prevista: string | null;
  aluno_gerado_id: string | null;
  data_criacao: string;
  lead: {
    id: string;
    nome_responsavel: string;
    email_contato: string | null;
    telefone: string | null;
    nome_aluno_candidato: string;
    data_nascimento_candidato: string | null;
    origem_lead: string;
    curso_interesse_id: string | null;
    data_entrada: string;
  };
}
