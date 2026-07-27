import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import { iniciarLogin } from '../../../../store/auth/auth.actions';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-login.component',
  imports: [ReactiveFormsModule, CommonModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css',
})
export class LoginComponent {
private fb = inject(FormBuilder);
  private store = inject(Store);

  loginForm = this.fb.group({
    email: ['', [Validators.required, Validators.email]],
    palavraPasse: ['', [Validators.required, Validators.minLength(6)]]
  });

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
