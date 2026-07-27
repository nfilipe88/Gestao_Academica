import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';

export const jwtInterceptor: HttpInterceptorFn = (req: HttpRequest<unknown>, next: HttpHandlerFn) => {
  const store = inject(Store);
  const platformId = inject(PLATFORM_ID); // Injetar a plataforma para proteção SSR

  let token: string | null = null;
  // Ler síncronamente do NgRx
  store.select(selectToken).subscribe(t => token = t).unsubscribe();

  // Proteção: Só tenta ler do localStorage se estivermos a correr no Browser
  if (!token && isPlatformBrowser(platformId)) {
    token = localStorage.getItem('saas_access_token');
  }

  if (token) {
    const clonedReq = req.clone({
      setHeaders: {
        Authorization: `Bearer ${token}`
      }
    });
    return next(clonedReq);
  }

  return next(req);
};
