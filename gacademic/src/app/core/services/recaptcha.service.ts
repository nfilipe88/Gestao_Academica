import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';

declare const grecaptcha: {
  ready(callback: () => void): void;
  execute(siteKey: string, opcoes: { action: string }): Promise<string>;
};

/**
 * Google reCAPTCHA v3 (ver back_end/app/core/recaptcha.py) — invisível
 * para quem preenche o formulário, só produz um token que o backend
 * valida com um score anti-bot. Usado nos formulários sem sessão mais
 * expostos a automação: registo de escola e captação de leads (CRM).
 *
 * A chave pública vem de GET /api/v1/public/config em vez de um
 * ficheiro de environment (esta app ainda não tem esse mecanismo) —
 * assim a mesma build serve para qualquer ambiente, e sem a chave
 * configurada no backend (dev/testes) o método simplesmente devolve
 * null, sem carregar nada da Google.
 */
@Injectable({ providedIn: 'root' })
export class RecaptchaService {
  private http = inject(HttpClient);
  private siteKeyPromise: Promise<string | null> | null = null;
  private scriptPromise: Promise<void> | null = null;

  private obterSiteKey(): Promise<string | null> {
    if (!this.siteKeyPromise) {
      this.siteKeyPromise = firstValueFrom(
        this.http.get<{ recaptcha_site_key: string | null }>('/api/v1/public/config')
      ).then((resposta) => resposta.recaptcha_site_key).catch(() => null);
    }
    return this.siteKeyPromise;
  }

  private carregarScript(siteKey: string): Promise<void> {
    if (!this.scriptPromise) {
      this.scriptPromise = new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = `https://www.google.com/recaptcha/api.js?render=${siteKey}`;
        script.onload = () => resolve();
        script.onerror = () => reject(new Error('Não foi possível carregar o reCAPTCHA.'));
        document.head.appendChild(script);
      });
    }
    return this.scriptPromise;
  }

  /**
   * Devolve o token para a `acao` indicada, ou `null` se o reCAPTCHA
   * não estiver configurado no backend ou se algo falhar a carregar —
   * nunca lança: perder esta camada extra de proteção não pode
   * impedir o envio do formulário em si (o rate limiting continua
   * ativo do lado do servidor de qualquer forma).
   */
  async obterToken(acao: string): Promise<string | null> {
    try {
      const siteKey = await this.obterSiteKey();
      if (!siteKey) return null;
      await this.carregarScript(siteKey);
      return await new Promise<string>((resolve, reject) => {
        grecaptcha.ready(() => {
          grecaptcha.execute(siteKey, { action: acao }).then(resolve, reject);
        });
      });
    } catch {
      return null;
    }
  }
}
