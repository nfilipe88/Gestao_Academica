import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { firstValueFrom } from 'rxjs';
import { erroGlobalInterceptor } from './erro-global.interceptor';
import { ToastService } from '../services/toast.service';
import { SentryService } from '../services/sentry.service';

describe('erroGlobalInterceptor', () => {
  let http: HttpClient;
  let backend: HttpTestingController;
  let toast: ToastService;
  let capturarErro: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([erroGlobalInterceptor])),
        provideHttpClientTesting(),
      ],
    });
    http = TestBed.inject(HttpClient);
    backend = TestBed.inject(HttpTestingController);
    toast = TestBed.inject(ToastService);
    capturarErro = vi.spyOn(TestBed.inject(SentryService), 'capturarErro').mockImplementation(() => {});
  });
  afterEach(() => backend.verify());

  async function pedirEFalhar(url: string, status: number, statusText = 'Error') {
    const resposta = firstValueFrom(http.get(url)).catch(e => e);
    backend.expectOne(url).flush({}, { status, statusText });
    return resposta;
  }

  it('um 500 mostra um toast genérico e continua a propagar o erro', async () => {
    const erro = await pedirEFalhar('/api/v1/alunos', 500);
    expect(erro.status).toBe(500);
    expect(toast.toasts().length).toBe(1);
    expect(toast.toasts()[0].mensagem).toContain('erro inesperado');
  });

  it('uma falha de rede (status 0) mostra um toast sobre a ligação', async () => {
    await pedirEFalhar('/api/v1/alunos', 0);
    expect(toast.toasts()[0].mensagem).toContain('Sem ligação');
  });

  it('um 500 é enviado ao Sentry; uma falha de rede (status 0) não', async () => {
    await pedirEFalhar('/api/v1/a', 500);
    await pedirEFalhar('/api/v1/b', 0);
    expect(capturarErro).toHaveBeenCalledTimes(1);
  });

  it.each([400, 401, 403, 404, 422, 429])('um %i não mostra toast — já tem mensagem específica no módulo', async (status) => {
    await pedirEFalhar('/api/v1/x', status);
    expect(toast.toasts().length).toBe(0);
  });

  it('não mostra toast para a renovação de sessão em fundo (evita alarmar por um 500 silencioso)', async () => {
    await pedirEFalhar('/api/v1/auth/refresh', 500);
    expect(toast.toasts().length).toBe(0);
  });

  it('não mostra toast para a sondagem de notificações — tem o seu próprio recuo silencioso', async () => {
    await pedirEFalhar('/api/v1/notificacoes/contagem', 500);
    expect(toast.toasts().length).toBe(0);
  });
});
