import { HttpInterceptorFn, HttpRequest, HttpHandlerFn } from '@angular/common/http';
import { inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { Store } from '@ngrx/store';
import { selectToken } from '../../store/auth/auth.selectors';
import { switchMap } from 'rxjs/internal/operators/switchMap';
import { take } from 'rxjs';

export const jwtInterceptor: HttpInterceptorFn = (req, next) => {
  const store = inject(Store);
  const platformId = inject(PLATFORM_ID);

  return store.select(selectToken).pipe(
    take(1),
    switchMap(token => {
      if (!token && isPlatformBrowser(platformId)) {
        token = localStorage.getItem('saas_access_token');
      }
      const finalReq = token
        ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
        : req;
      return next(finalReq);
    })
  );
};
