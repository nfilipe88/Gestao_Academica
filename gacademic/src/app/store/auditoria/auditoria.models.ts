// Alinhado com app/schemas/auditoria.py e app/cruds/auditoria.py.
// Diferente de UsuarioAuditoriaRegisto (store/usuarios/usuarios.models.ts,
// só ações de RBAC): isto cobre a criação/alteração/eliminação de
// QUALQUER entidade do sistema, gerada automaticamente no back-end.

export type AcaoAuditoria = 'CRIADO' | 'ALTERADO' | 'APAGADO';

export interface AlteracaoCampo {
  antes: unknown;
  depois: unknown;
}

export interface AuditLogRegisto {
  id: string;
  autor_id: string | null;
  autor_nome: string | null;
  autor_perfil: string | null;
  acao: AcaoAuditoria;
  entidade: string;
  entidade_id: string;
  // Para CRIADO/APAGADO: snapshot simples { campo: valor }.
  // Para ALTERADO: { campo: { antes, depois } } — o componente distingue pelo formato.
  alteracoes: Record<string, unknown> | Record<string, AlteracaoCampo> | null;
  criado_em: string;
}

export interface FiltrosAuditoria {
  entidade?: string;
  entidade_id?: string;
  acao?: AcaoAuditoria;
  autor_id?: string;
  data_inicio?: string;
  data_fim?: string;
}
