import { ErrorHandler, Injectable, inject } from '@angular/core';
import { SentryService } from './services/sentry.service';

/**
 * Substitui o ErrorHandler por omissão do Angular (que só faz console.error)
 * — mantém esse comportamento (a consola continua útil em desenvolvimento) e
 * acrescenta o envio ao Sentry quando está configurado (ver
 * core/services/sentry.service.ts; sem DSN, capturarErro() não faz nada).
 *
 * Cobre exceções não apanhadas em qualquer parte da app (bugs de template,
 * de lógica de componente, etc.) — diferente do
 * core/interceptors/erro-global.interceptor.ts, que cobre especificamente
 * respostas HTTP inesperadas (500, falhas de rede).
 */
@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  private sentry = inject(SentryService);

  handleError(erro: unknown): void {
    console.error(erro);
    this.sentry.capturarErro(erro);
  }
}
