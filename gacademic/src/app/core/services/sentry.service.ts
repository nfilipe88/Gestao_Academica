import { Injectable, PLATFORM_ID, inject } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';

interface ConfigPublica {
  sentry_dsn_frontend: string | null;
  sentry_ambiente: string;
}

/**
 * Telemetria de erros do frontend (Sentry) — opcional, espelha o padrão já
 * usado por core/services/recaptcha.service.ts: a chave pública vem de
 * GET /api/v1/public/config (nunca de um ficheiro de environment fixado no
 * build, para poder mudar sem recompilar), e sem DSN configurado no
 * servidor isto fica completamente inerte — nem o pacote @sentry/angular
 * chega a ser importado (import dinâmico), zero custo no bundle inicial.
 *
 * Só captura exceções (init próprio, ver iniciar()) — nunca via
 * Sentry.createErrorHandler(), que a app não usa de propósito: a captura é
 * sempre manual (ver core/error-handler.ts e
 * core/interceptors/erro-global.interceptor.ts), sem assumir nada sobre
 * Zone.js (esta app corre zoneless).
 */
@Injectable({ providedIn: 'root' })
export class SentryService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);
  private sentry: typeof import('@sentry/angular') | null = null;

  async iniciar(): Promise<void> {
    if (!isPlatformBrowser(this.platformId)) return;
    try {
      const config = await firstValueFrom(this.http.get<ConfigPublica>('/api/v1/public/config'));
      if (!config.sentry_dsn_frontend) return;

      const sentry = await import('@sentry/angular');
      sentry.init({
        dsn: config.sentry_dsn_frontend,
        environment: config.sentry_ambiente,
        // Só captura de erros de propósito — sem tracing/session replay
        // (custo e privacidade mínimos; ver core/monitorizacao.py no backend
        // para o mesmo raciocínio do lado do servidor).
        tracesSampleRate: 0,
      });
      this.sentry = sentry;
    } catch {
      // Nunca deixar a app de arrancar por causa disto — é só telemetria.
    }
  }

  capturarErro(erro: unknown): void {
    this.sentry?.captureException(erro);
  }
}
