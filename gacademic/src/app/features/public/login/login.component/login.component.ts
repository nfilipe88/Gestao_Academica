import { VoltarInicioComponent } from '../../../../shared/components/voltar-inicio/voltar-inicio.component';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import { iniciarLogin } from '../../../../store/auth/auth.actions';
import { selectAuthError } from '../../../../store/auth/auth.selectors';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login.component',
  imports: [ReactiveFormsModule, CommonModule, VoltarInicioComponent],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent implements OnInit {
private fb = inject(FormBuilder);
  private store = inject(Store);
  private route = inject(ActivatedRoute);

  erro$ = this.store.select(selectAuthError);

  // Vindo da ativação de conta por e-mail (?ativado=1, ver
  // ativar-conta.component) — confirma que o link de ativação foi
  // validado com sucesso e o login já está disponível. O registo em si
  // já não redireciona para aqui (deixou de haver login imediato após
  // registar — ver registo.component), por isso não existe mensagem
  // equivalente para "?registado=1".
  mostrarMensagemAtivado = this.route.snapshot.queryParamMap.get('ativado') === '1';

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
