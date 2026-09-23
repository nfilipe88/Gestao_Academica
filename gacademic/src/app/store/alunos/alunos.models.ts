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
  ativo: boolean; // desativado (nunca eliminado — retenção legal de 15 anos): sem acesso, não conta para o limite do plano
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

// Lista fechada para o <select> de "Vincular responsável" — antes era
// texto livre (input com placeholder "Ex: Mãe"), o que arriscava dados
// inconsistentes ("Pai"/"pai"/"Papá") a aparecerem tal e qual em
// relatórios/Estatísticas (achado real de uma auditoria de UX desta
// sessão). O back-end continua a aceitar qualquer string (coluna
// tipo_parentesco em models_pessoas.py é texto livre, sem enum — usada
// também por cruds/crm.py com o valor "Responsável" e copiada tal e
// qual em Transferências entre escolas), por isso "Outro" continua
// disponível para não perder nenhum caso real.
export const TIPOS_PARENTESCO = ['Pai', 'Mãe', 'Avô', 'Avó', 'Tio', 'Tia', 'Tutor Legal'] as const;
