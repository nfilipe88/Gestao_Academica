import { describe, expect, it } from 'vitest';
import { avisosDeLeitura, CelulaLeitura } from './avisos-leitura';

const celula = (modulo: string, ler: boolean, escreve: boolean, leituras_necessarias: string[] = []): CelulaLeitura =>
  ({ modulo, informativo: false, ler, escreve, leituras_necessarias });

describe('avisosDeLeitura', () => {
  it('avisa quando o ecrã precisa de ler um módulo que o perfil não vê', () => {
    expect(avisosDeLeitura([
      celula('Financeiro', true, true, ['Alunos']),
      celula('Alunos', false, false, ['Turmas']),
    ])).toEqual([{ modulo: 'Financeiro', precisa: 'Alunos' }]);
  });

  it('não avisa em cascata: uma leitura de referência não gera avisos próprios', () => {
    expect(avisosDeLeitura([
      celula('Financeiro', true, true, ['Alunos']),
      celula('Alunos', true, false, ['Turmas']),
      celula('Turmas', false, false, ['Cursos']),
    ])).toEqual([]);
  });

  it('avisa se o módulo referenciado também é para escrever: o ecrã dele é usado a sério', () => {
    expect(avisosDeLeitura([
      celula('Financeiro', true, true, ['Alunos']),
      celula('Alunos', true, true, ['Turmas']),
      celula('Turmas', false, false),
    ])).toEqual([{ modulo: 'Alunos', precisa: 'Turmas' }]);
  });

  it('um módulo só de leitura que ninguém referencia continua a avisar', () => {
    expect(avisosDeLeitura([
      celula('Estatísticas', true, false, ['Financeiro']),
      celula('Financeiro', false, false),
    ])).toEqual([{ modulo: 'Estatísticas', precisa: 'Financeiro' }]);
  });

  it('ignora módulos fora de uso e linhas informativas', () => {
    expect(avisosDeLeitura([
      celula('Financeiro', false, false, ['Alunos']),
      { ...celula('Visão Geral', true, false, ['Alunos']), informativo: true },
      celula('Alunos', false, false),
    ])).toEqual([]);
  });
});
