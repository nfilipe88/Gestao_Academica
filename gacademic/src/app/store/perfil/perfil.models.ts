// Alinhado com app/schemas/perfil.py.

export interface Perfil {
  id: string;
  nome_completo: string;
  email: string;
  perfil_acesso: string;
  tenant_id: string;
  nome_instituicao: string;
  data_criacao: string;
}
