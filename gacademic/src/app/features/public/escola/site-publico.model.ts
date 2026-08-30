// Tipos partilhados entre o contentor (escola.component) e os 4
// modelos visuais (./templates/*) — ver app/schemas/site_publico.py
// no back-end para a forma exata da resposta.

export interface CursoPublico {
  id: string;
  nome: string;
  descricao: string | null; // conteúdo programático, texto livre
}

export interface SitePublico {
  tenant_id: string;
  nome_fantasia: string;
  template: string;
  logotipo: string | null;
  missao: string | null;
  metodologia: string | null;
  telefone_contacto: string | null;
  email_contacto: string | null;
  morada: string | null;
  cidade: string | null;
  facebook: string | null;
  instagram: string | null;
  whatsapp: string | null;
  cursos: CursoPublico[];
  fotos: string[];
}
