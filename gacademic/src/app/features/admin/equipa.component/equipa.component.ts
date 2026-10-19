import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, inject, OnInit, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NomePerfilPipe } from '../../../shared/pipes/nome-perfil.pipe';

interface MembroEquipa {
  id: string;
  nome_completo: string;
  email: string;
  perfil_acesso: 'SUPER_ADMIN' | 'SUPORTE';
  ativo: boolean;
  data_criacao: string;
}

/**
 * Equipa da plataforma (só o Super Admin): as contas de Suporte, que
 * ajudam as escolas — tickets, consulta das escolas, desbloquear pessoas,
 * eventos de segurança — sem os poderes do Super Admin.
 * Ver back_end/app/api/v1/admin.py (rotas /admin/equipa e _EQUIPA).
 */
@Component({
  selector: 'app-equipa-plataforma',
  imports: [DatePipe, ReactiveFormsModule, NomePerfilPipe],
  templateUrl: './equipa.component.html',
})
export class EquipaPlataformaComponent implements OnInit {
  private http = inject(HttpClient);
  private fb = inject(FormBuilder);

  membros = signal<MembroEquipa[]>([]);
  mensagem = signal<string | null>(null);
  erro = signal<string | null>(null);
  aEnviar = signal(false);

  form = this.fb.group({
    nome_completo: ['', Validators.required],
    email: ['', [Validators.required, Validators.email]],
    palavra_passe: ['', [Validators.required, Validators.minLength(12)]],
  });

  ngOnInit() {
    this.carregar();
  }

  carregar() {
    this.http.get<MembroEquipa[]>('/api/v1/admin/equipa').subscribe({
      next: (lista) => this.membros.set(lista),
      error: (err) => this.erro.set(err.error?.detail || 'Não foi possível carregar a equipa.'),
    });
  }

  onCriar() {
    if (this.form.invalid) return;
    this.mensagem.set(null);
    this.erro.set(null);
    this.aEnviar.set(true);
    this.http.post<MembroEquipa>('/api/v1/admin/equipa', this.form.getRawValue()).subscribe({
      next: (membro) => {
        this.aEnviar.set(false);
        this.form.reset();
        this.mensagem.set(`Conta de Suporte criada para ${membro.nome_completo}. Entregue-lhe a palavra-passe inicial por um canal seguro.`);
        this.carregar();
      },
      error: (err) => {
        this.aEnviar.set(false);
        const detalhe = err.error?.detail;
        this.erro.set(typeof detalhe === 'string' ? detalhe
          : 'Verifique os dados: a palavra-passe precisa de 12+ caracteres, com maiúsculas, minúsculas e números.');
      },
    });
  }

  onAlternarAtivo(membro: MembroEquipa) {
    this.mensagem.set(null);
    this.erro.set(null);
    this.http.patch<MembroEquipa>(`/api/v1/admin/equipa/${membro.id}/ativo`, { ativo: !membro.ativo }).subscribe({
      next: (atualizado) => {
        this.mensagem.set(`${atualizado.nome_completo} agora está ${atualizado.ativo ? 'ativo' : 'suspenso'}.`);
        this.carregar();
      },
      error: (err) => this.erro.set(err.error?.detail || 'Não foi possível alterar o estado.'),
    });
  }
}
