import { CommonModule } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RecaptchaService } from '../../../../core/services/recaptcha.service';

@Component({
  selector: 'app-registo.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './registo.component.html',
  styleUrl: './registo.component.css',
})
export class RegistoComponent {
  private fb = inject(FormBuilder);
  private http = inject(HttpClient);
  private recaptcha = inject(RecaptchaService);

  // Nenhum diálogo nativo (alert/confirm) — não é intercetável em
  // automação/testes e destoa do resto da UI, que nunca usa diálogos
  // nativos (mesmo padrão já seguido no resto da app, ex.:
  // features/admin/admin.component). Erro mostrado inline.
  //
  // Sucesso já NÃO redireciona para /login: o registo deixou de criar
  // uma conta pronta a usar — passa a exigir clicar num link de
  // ativação enviado por e-mail primeiro (ver
  // back_end/app/cruds/auth.py::registar_escola/ativar_conta), por
  // isso mostra-se aqui mesmo um estado "verifique o seu e-mail",
  // mesmo padrão de signal de redefinir-senha.component.
  erro: string | null = null;
  concluido = signal(false);
  emailRegistado = '';

  registoForm = this.fb.group({
    nome_fantasia: ['', Validators.required],
    nif: ['', Validators.required],
    nome_gestor: ['', Validators.required],
    email_gestor: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(8)]],
    aceitou_termos: [false, Validators.requiredTrue]
  });

  async onRegister() {
    if (this.registoForm.valid) {
      this.erro = null;
      const recaptcha_token = await this.recaptcha.obterToken('registo_escola');
      this.http.post('/api/v1/auth/registo', { ...this.registoForm.value, recaptcha_token })
        .subscribe({
          next: () => {
            this.emailRegistado = this.registoForm.value.email_gestor ?? '';
            this.concluido.set(true);
          },
          error: (err) => {
            const detail = err.error?.detail;
            this.erro = typeof detail === 'string' ? detail : 'Não foi possível concluir o registo.';
          }
        });
    }
  }
}
