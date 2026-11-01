// Módulo cujo ecrã precisa de ler outro que este perfil não pode ver: o ecrã
// ficava vazio sem explicação (ex.: Financeiro sem ler Alunos).
export interface CelulaLeitura {
  modulo: string;
  informativo: boolean;
  leituras_necessarias?: string[];
  ler: boolean;
  // Criar, atualizar ou apagar.
  escreve: boolean;
}

export interface AvisoLeitura {
  modulo: string;
  precisa: string;
}

export function avisosDeLeitura(celulas: CelulaLeitura[]): AvisoLeitura[] {
  const ativas = celulas.filter(c => !c.informativo && (c.ler || c.escreve));
  const lidas = new Set(celulas.filter(c => c.ler).map(c => c.modulo));
  // Um módulo só de leitura que outro precisa é só uma referência: a Tesouraria
  // lê Alunos para escolher o aluno no Financeiro. Avisar também do que o ecrã
  // de Alunos precisa empurrava o Gestor, aviso a aviso, a abrir quase tudo.
  const referenciadas = new Set(ativas.flatMap(c => c.leituras_necessarias ?? []));
  return ativas
    .filter(c => c.escreve || !referenciadas.has(c.modulo))
    .flatMap(c => (c.leituras_necessarias ?? [])
      .filter(precisa => !lidas.has(precisa))
      .map(precisa => ({ modulo: c.modulo, precisa })));
}
