// Alinhado com app/schemas/perfil.py.

export interface Perfil {
  id: string;
  nome_completo: string;
  email: string;
  perfil_acesso: string;
  tenant_id: string;
  nome_instituicao: string;
  data_criacao: string;
  // Só diz SE há assinatura pessoal ativa — a imagem sai por GET
  // /perfil/assinatura (ver perfil.component.ts), usada em documentos
  // PDF emitidos pelo próprio quando é staff (ver app/core/assinaturas.py).
  tem_assinatura_pessoal: boolean;
}
