import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { GlobalErrorHandler } from './error-handler';
import { SentryService } from './services/sentry.service';

describe('GlobalErrorHandler', () => {
  let handler: GlobalErrorHandler;
  let capturarErro: ReturnType<typeof vi.fn>;
  let consoleErro: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [GlobalErrorHandler] });
    handler = TestBed.inject(GlobalErrorHandler);
    capturarErro = vi.spyOn(TestBed.inject(SentryService), 'capturarErro').mockImplementation(() => {});
    consoleErro = vi.spyOn(console, 'error').mockImplementation(() => {});
  });
  afterEach(() => vi.restoreAllMocks());

  it('regista na consola (mantém o comportamento por omissão do Angular)', () => {
    const erro = new Error('falhou');
    handler.handleError(erro);
    expect(consoleErro).toHaveBeenCalledWith(erro);
  });

  it('envia sempre ao Sentry (que decide sozinho se está ativo — ver SentryService)', () => {
    const erro = new Error('falhou');
    handler.handleError(erro);
    expect(capturarErro).toHaveBeenCalledWith(erro);
  });
});
