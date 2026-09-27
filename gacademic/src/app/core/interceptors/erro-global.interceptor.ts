import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { ToastService } from '../services/toast.service';
import { SentryService } from '../services/sentry.service';

// Pedidos que já têm o seu próprio tratamento de falha silenciosa por
// desenho — um toast aqui seria ruído, não ajuda:
//  - /auth/refresh: renovação em fundo (ver jwt.interceptor.ts); uma falha
//    aqui já dispara sessaoExpirada, que por si só leva ao ecrã de login.
//  - /notificacoes/contagem: sondagem periódica com o seu próprio recuo
//    (ver store/notificacoes/polling-contagem.ts) — uma falha isolada é
//    normal e não deve interromper quem está a trabalhar noutro ecrã.
const _SEM_TOAST = ['/api/v1/auth/refresh', '/api/v1/notificacoes/contagem'];

/**
 * Rede de segurança para erros INESPERADOS da API (500 e falhas de rede/
 * ligação — status 0) que um effect concreto não soubesse mostrar: sem
 * isto, um pedido destes deixava o ecrã preso num "a carregar..." sem
 * pista nenhuma para quem está a usar a plataforma (ver ToastService).
 *
 * De propósito NÃO cobre 4xx (400/401/403/404/422/429): esses já têm uma
 * mensagem específica e mais útil, mostrada inline por cada módulo (ver os
 * *.effects.ts, todos com o seu próprio catchError) — duplicar isso aqui
 * seria ruído, não ajuda. O 401 em particular já é tratado à parte pelo
 * jwt.interceptor.ts (tenta renovar a sessão antes de desistir).
 *
 * Nunca engole o erro — sempre volta a lançá-lo (throwError), para o
 * catchError de cada effect continuar a correr como já corria (loading:false,
 * mensagem de erro local, etc.). Isto é um extra, não uma substituição.
 */
export const erroGlobalInterceptor: HttpInterceptorFn = (req, next) => {
  const toast = inject(ToastService);
  const sentry = inject(SentryService);

  return next(req).pipe(
    catchError((erro: HttpErrorResponse) => {
      const semLigacao = erro.status === 0;
      const erroDoServidor = erro.status >= 500;

      if ((semLigacao || erroDoServidor) && !_SEM_TOAST.some(caminho => req.url.includes(caminho))) {
        toast.mostrarErro(
          semLigacao
            ? 'Sem ligação ao servidor — verifique a sua internet e tente novamente.'
            : 'Ocorreu um erro inesperado no servidor. Tente novamente dentro de momentos.'
        );
        if (erroDoServidor) sentry.capturarErro(erro);
      }

      return throwError(() => erro);
    })
  );
};
