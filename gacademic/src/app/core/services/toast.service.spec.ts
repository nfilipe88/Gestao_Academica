import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ToastService } from './toast.service';

describe('ToastService', () => {
  let servico: ToastService;

  beforeEach(() => {
    vi.useFakeTimers();
    servico = new ToastService();
  });
  afterEach(() => vi.useRealTimers());

  it('mostra um erro novo', () => {
    servico.mostrarErro('Ocorreu um erro inesperado.');
    expect(servico.toasts().map(t => t.mensagem)).toEqual(['Ocorreu um erro inesperado.']);
  });

  it('não duplica a mesma mensagem em simultâneo (vários pedidos a falhar ao mesmo tempo)', () => {
    servico.mostrarErro('Sem ligação ao servidor.');
    servico.mostrarErro('Sem ligação ao servidor.');
    servico.mostrarErro('Sem ligação ao servidor.');
    expect(servico.toasts().length).toBe(1);
  });

  it('mensagens diferentes aparecem lado a lado', () => {
    servico.mostrarErro('Erro A');
    servico.mostrarErro('Erro B');
    expect(servico.toasts().map(t => t.mensagem)).toEqual(['Erro A', 'Erro B']);
  });

  it('desaparece sozinho ao fim de 8 segundos', () => {
    servico.mostrarErro('Vai desaparecer');
    expect(servico.toasts().length).toBe(1);
    vi.advanceTimersByTime(7999);
    expect(servico.toasts().length).toBe(1);
    vi.advanceTimersByTime(1);
    expect(servico.toasts().length).toBe(0);
  });

  it('remover() tira o toast antes do tempo', () => {
    servico.mostrarErro('Fecho manual');
    const id = servico.toasts()[0].id;
    servico.remover(id);
    expect(servico.toasts().length).toBe(0);
  });

  it('a mesma mensagem pode voltar a aparecer depois de desaparecer', () => {
    servico.mostrarErro('Repete-se');
    vi.advanceTimersByTime(8000);
    expect(servico.toasts().length).toBe(0);
    servico.mostrarErro('Repete-se');
    expect(servico.toasts().length).toBe(1);
  });
});
