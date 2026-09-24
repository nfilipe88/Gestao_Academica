import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { TestBed, ComponentFixture } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideStore, Store } from '@ngrx/store';
import { LoginComponent } from './login.component';
import { authReducer } from '../../../../store/auth/auth.reducer';
import { loginFalhou, iniciarLogin } from '../../../../store/auth/auth.actions';
import { instalarLocalStorageFalso } from '../../../../testing/ajudas';

describe('LoginComponent', () => {
  let fixture: ComponentFixture<LoginComponent>;
  const raiz = () => fixture.nativeElement as HTMLElement;

  beforeEach(() => {
    instalarLocalStorageFalso();
    TestBed.configureTestingModule({ providers: [provideRouter([]), provideStore({ auth: authReducer })] });
    fixture = TestBed.createComponent(LoginComponent);
    fixture.detectChanges();
  });
  afterEach(() => vi.unstubAllGlobals());

  it('o botão Entrar só fica ativo com e-mail válido e palavra-passe preenchida', () => {
    const entrar = raiz().querySelector('button[type="submit"]') as HTMLButtonElement;
    expect(entrar.disabled).toBe(true);
    fixture.componentInstance.loginForm.setValue({ email: 'gestor@escola.pt', palavraPasse: 'SenhaTeste123!' });
    fixture.detectChanges();
    expect(entrar.disabled).toBe(false);
  });

  it('submeter despacha iniciarLogin com as credenciais', () => {
    const despachar = vi.spyOn(TestBed.inject(Store), 'dispatch');
    fixture.componentInstance.loginForm.setValue({ email: 'gestor@escola.pt', palavraPasse: 'SenhaTeste123!' });
    fixture.componentInstance.onSubmit();
    expect(despachar).toHaveBeenCalledWith(iniciarLogin({ email: 'gestor@escola.pt', palavraPasse: 'SenhaTeste123!' }));
  });

  it('mostra o erro de autenticação num alerta acessível', () => {
    TestBed.inject(Store).dispatch(loginFalhou({ erro: 'Credenciais inválidas.' }));
    fixture.detectChanges();
    expect(raiz().querySelector('[role="alert"]')?.textContent).toContain('Credenciais inválidas.');
  });

  it('cada campo tem etiqueta associada e os tipos certos para gestores de palavras-passe', () => {
    for (const rotulo of Array.from(raiz().querySelectorAll('label[for]'))) {
      expect(raiz().querySelector('#' + rotulo.getAttribute('for'))).toBeTruthy();
    }
    expect(raiz().querySelectorAll('label[for]').length).toBe(2);
    expect((raiz().querySelector('input[type="password"]') as HTMLInputElement).autocomplete).toBe('current-password');
    expect((raiz().querySelector('input[type="email"]') as HTMLInputElement).autocomplete).toBe('username');
  });
});
