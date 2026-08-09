// Tipos alinhados com os schemas devolvidos pelo back-end
// (app/database/models_pessoas.py / app/api/v1/alunos.py).

export interface Aluno {
  id: string;
  tenant_id: string;
  usuario_id: string | null;
  matricula_interna: string;
  nome_completo: string;
  data_nascimento: string; // ISO (YYYY-MM-DD)
  numero_documento: string | null;
  data_criacao: string;
}

export interface Responsavel {
  id: string;
  tenant_id: string;
  usuario_id: string | null;
  nome_completo: string;
  numero_documento: string | null;
  telefone_contato: string;
  data_criacao: string;
}

export interface AlunoResponsavelVinculo {
  id: string;
  tenant_id: string;
  aluno_id: string;
  responsavel_id: string;
  tipo_parentesco: string;
  responsavel_financeiro: boolean;
}
