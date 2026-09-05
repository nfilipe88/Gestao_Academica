import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import { iniciarLogin } from '../../../../store/auth/auth.actions';
import { selectAuthError } from '../../../../store/auth/auth.selectors';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent implements OnInit {
private fb = inject(FormBuilder);
  private store = inject(Store);
  private route = inject(ActivatedRoute);

  erro$ = this.store.select(selectAuthError);

  // Vindo do registo (?registado=1&email=...) — confirma que a escola
  // foi criada com sucesso e poupa reescrever o e-mail. Nunca a
  // palavra-passe aqui: não deve viajar num URL (histórico do browser,
  // logs do servidor, cabeçalho Referer).
  mostrarMensagemRegisto = this.route.snapshot.queryParamMap.get('registado') === '1';

  loginForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    palavraPasse: ['', [Validators.required, Validators.minLength(6)]]
  });

  ngOnInit() {
    const email = this.route.snapshot.queryParamMap.get('email');
    if (email) {
      this.loginForm.patchValue({ email });
    }
  }

  onSubmit() {
    if (this.loginForm.valid) {
      const { email, palavraPasse } = this.loginForm.value;
      // Dispara a Action para o Redux / Effect intercetar
      this.store.dispatch(iniciarLogin({
        email: email!,
        palavraPasse: palavraPasse!
      }));
    }
  }
}
