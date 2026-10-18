import { VoltarInicioComponent } from '../../../../shared/components/voltar-inicio/voltar-inicio.component';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Store } from '@ngrx/store';
import {
  cancelarDoisFatores, confirmarCodigoDoisFatores, iniciarLogin, reenviarCodigoDoisFatores
} from '../../../../store/auth/auth.actions';
import { selectAuthError, selectDoisFatores } from '../../../../store/auth/auth.selectors';
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
  // Segundo passo (verificação em dois passos por e-mail) — ver auth.effects.ts.
  doisFatores$ = this.store.select(selectDoisFatores);

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

  codigoForm = this.fb.group({
    codigo: ['', [Validators.required, Validators.pattern(/^\s*\d{6}\s*$/)]]
  });

  ngOnInit() {
    const email = this.route.snapshot.queryParamMap.get('email');
    if (email) {
      this.loginForm.patchValue({ email });
    }
  }

  onConfirmarCodigo() {
    if (this.codigoForm.invalid) return;
    this.store.dispatch(confirmarCodigoDoisFatores({ codigo: this.codigoForm.value.codigo!.trim() }));
    this.codigoForm.reset();
  }

  onReenviarCodigo() {
    this.store.dispatch(reenviarCodigoDoisFatores());
  }

  onCancelarDoisFatores() {
    this.codigoForm.reset();
    this.loginForm.patchValue({ palavraPasse: '' });
    this.store.dispatch(cancelarDoisFatores());
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
