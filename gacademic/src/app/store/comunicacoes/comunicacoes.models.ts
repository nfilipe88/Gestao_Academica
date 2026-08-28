// Alinhado com app/api/v1/comunicacoes.py.
export interface Comunicado {
  id: string;
  autor_nome: string;
  tipo: string; // COMUNICADO | CONVOCATORIA
  titulo: string;
  corpo: string;
  destinatario_tipo: string; // TURMA | ALUNO | ESCOLA
  destinatario_turma_id: string | null;
  destinatario_aluno_id: string | null;
  total_destinatarios: number;
  data_envio: string;
  // Ficheiro anexado (ex.: circular em PDF) — ver
  // PUT/GET /comunicados/{id}/anexo. Não vem no e-mail já disparado na
  // criação, só fica disponível para download na plataforma (staff).
  tem_anexo: boolean;
}

export const TIPOS_COMUNICADO = ['COMUNICADO', 'CONVOCATORIA'] as const;
export const DESTINATARIOS_COMUNICADO = ['TURMA', 'ALUNO', 'ESCOLA'] as const;
