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
  num_responsaveis: number; // calculado no back-end — não confundir com vinculos.length (só carregado depois de expandir "Ver")
}

// Ver app/database/models_pessoas.py::AlunoDocumento — sobretudo o
// Histórico Escolar anexado automaticamente numa Transferência/
// Reingresso cross-escola (app/cruds/transferencias.py::aprovar_e_migrar).
export interface AlunoDocumento {
  id: string;
  descricao: string | null;
  nome_original: string;
}

// Ver app/database/models_pessoas.py::FotoPerfilAluno — a foto que
// vale para o cartão de acesso. Deve ser renovada todos os anos; a
// mais recente é sempre a "ativa" (a antiga fica arquivada, nunca é
// apagada — histórico da evolução do aluno).
export interface FotoPerfilAluno {
  id: string;
  ano_letivo: number;
  ativa: boolean;
  nome_original: string;
  data_envio: string;
}

export interface Responsavel {
  id: string;
  tenant_id: string;
  usuario_id: string | null;
  nome_completo: string;
  numero_documento: string | null;
  telefone_contato: string;
  email: string | null; // Usado para notificar quando é vinculado a um aluno
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
