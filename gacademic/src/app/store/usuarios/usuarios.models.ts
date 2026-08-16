// Alinhado com app/schemas/usuarios.py e app/cruds/usuarios.py.

export type PerfilStaff = 'GESTOR' | 'SECRETARIA' | 'PROFESSOR';

export interface UsuarioStaff {
  id: string;
  nome_completo: string;
  email: string;
  perfil_acesso: PerfilStaff;
  ativo: boolean;
  data_criacao: string;
}

// Só GESTOR e SECRETARIA — Professor tem alocações/Diário associados e
// não pode ser reatribuído por aqui (ver cruds/usuarios.py::PERFIS_SEM_SUBTABELA).
export const PERFIS_ATRIBUIVEIS: ReadonlyArray<'GESTOR' | 'SECRETARIA'> = ['GESTOR', 'SECRETARIA'];

export interface UsuarioAuditoriaRegisto {
  id: string;
  usuario_alvo_id: string;
  nome_alvo: string;
  nome_autor: string | null;
  acao: 'CRIACAO_SECRETARIA' | 'MUDANCA_PERFIL' | 'SUSPENSAO' | 'REATIVACAO';
  perfil_anterior: string | null;
  perfil_novo: string | null;
  detalhe: string | null;
  data_acao: string;
}
