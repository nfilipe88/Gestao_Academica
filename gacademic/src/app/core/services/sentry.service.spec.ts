import { afterEach, describe, expect, it } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { SentryService } from './sentry.service';

describe('SentryService', () => {
  let servico: SentryService;
  let backend: HttpTestingController;

  function preparar() {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    servico = TestBed.inject(SentryService);
    backend = TestBed.inject(HttpTestingController);
  }

  afterEach(() => backend.verify());

  it('sem DSN configurado no servidor, fica inerte — capturarErro não faz nada nem rebenta', async () => {
    preparar();
    const promessa = servico.iniciar();
    backend.expectOne('/api/v1/public/config').flush({ sentry_dsn_frontend: null, sentry_ambiente: 'development' });
    await promessa;
    expect(() => servico.capturarErro(new Error('x'))).not.toThrow();
  });

  it('se o pedido de configuração falhar, não rebenta o arranque da app', async () => {
    preparar();
    const promessa = servico.iniciar();
    backend.expectOne('/api/v1/public/config').flush({}, { status: 500, statusText: 'Error' });
    await expect(promessa).resolves.toBeUndefined();
  });
});
