// Tipos partilhados entre o contentor (features/public/escola) e os
// modelos visuais de página pública + as peças reutilizáveis de
// shared/components/site-publico-* que os compõem — ver
// app/schemas/site_publico.py no back-end para a forma exata da
// resposta.

export interface CursoPublico {
  id: string;
  nome: string;
  descricao: string | null; // conteúdo programático, texto livre
}

// Evento da escola publicado na página pública — ver
// app/schemas/eventos.py::EventoPublicoOut. Distinto da galeria solta
// (`fotos` abaixo): aqui cada evento tem título/data/descrição e as
// suas próprias fotos, sem limite.
export interface EventoPublico {
  id: string;
  titulo: string;
  data: string;
  descricao: string | null;
  fotos: string[];
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
  eventos: EventoPublico[];
  moeda: string;
  // false = a escola encerrou as candidaturas de matrícula.
  matriculas_abertas?: boolean;
  // Valor da taxa de matrícula (encargo único) — null = a escola não
  // cobra. Ver Tenant.valor_taxa_matricula no back-end.
  valor_taxa_matricula: number | null;
}
