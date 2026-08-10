// Alinhado com app/api/v1/professores.py.
export interface Professor {
  id: string;
  usuario_id: string;
  nome_completo: string;
  email: string;
  formacao_academica: string | null;
  data_criacao: string;
}
