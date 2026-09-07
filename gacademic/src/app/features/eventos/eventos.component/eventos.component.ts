import { AsyncPipe, CommonModule } from '@angular/common';
import { Component, inject, OnInit } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Store } from '@ngrx/store';
import {
  adicionarFotoEvento, atualizarEvento, carregarEventos, criarEvento, removerEvento, removerFotoEvento
} from '../../../store/eventos/eventos.actions';
import { selectEventos, selectEventosError, selectEventosMensagem } from '../../../store/eventos/eventos.selector';
import { Evento } from '../../../store/eventos/eventos.models';

// Área de gestão de Eventos da escola (festas, feiras, dias abertos) —
// publicados automaticamente na página pública (Site Público), numa
// secção "Últimos Eventos". Mesmo padrão de UI da secção Site Público
// em configuracoes.component.ts (formulário + grelha de fotos), mas
// SEM o limite de 8 fotos pensado para aquela galeria genérica — aqui
// cada evento pode ter tantas fotos quantas fizerem sentido.
@Component({
  selector: 'app-eventos.component',
  imports: [ReactiveFormsModule, CommonModule, AsyncPipe],
  templateUrl: './eventos.component.html',
  styleUrl: './eventos.component.css',
})
export class EventosComponent implements OnInit {
  private fb = inject(FormBuilder);
  private store = inject(Store);

  eventos$ = this.store.select(selectEventos);
  mensagem$ = this.store.select(selectEventosMensagem);
  erro$ = this.store.select(selectEventosError);

  mostrarFormulario = false;
  eventoEmEdicaoId: string | null = null;

  eventoForm = this.fb.group({
    titulo: ['', Validators.required],
    data: ['', Validators.required],
    descricao: [''],
    publicado: [true],
  });

  ngOnInit() {
    this.store.dispatch(carregarEventos());
  }

  alternarFormulario() {
    this.mostrarFormulario = !this.mostrarFormulario;
    this.eventoEmEdicaoId = null;
    this.eventoForm.reset({ titulo: '', data: '', descricao: '', publicado: true });
  }

  onSubmit() {
    if (this.eventoForm.invalid) return;
    const v = this.eventoForm.value;
    if (this.eventoEmEdicaoId) {
      this.store.dispatch(atualizarEvento({
        evento_id: this.eventoEmEdicaoId, titulo: v.titulo!, data: v.data!,
        descricao: v.descricao || null, publicado: !!v.publicado,
      }));
    } else {
      this.store.dispatch(criarEvento({
        titulo: v.titulo!, data: v.data!, descricao: v.descricao || null, publicado: !!v.publicado,
      }));
    }
    this.mostrarFormulario = false;
    this.eventoEmEdicaoId = null;
  }

  onEditar(evento: Evento) {
    this.eventoEmEdicaoId = evento.id;
    this.mostrarFormulario = true;
    this.eventoForm.setValue({
      titulo: evento.titulo, data: evento.data, descricao: evento.descricao ?? '', publicado: evento.publicado,
    });
  }

  onRemover(eventoId: string) {
    this.store.dispatch(removerEvento({ evento_id: eventoId }));
  }

  onSelecionarFoto(eventoId: string, event: Event) {
    const ficheiro = (event.target as HTMLInputElement).files?.[0];
    if (!ficheiro) return;
    this.store.dispatch(adicionarFotoEvento({ evento_id: eventoId, ficheiro }));
    (event.target as HTMLInputElement).value = ''; // permite voltar a escolher o mesmo ficheiro depois
  }

  onRemoverFoto(eventoId: string, fotoId: string) {
    this.store.dispatch(removerFotoEvento({ evento_id: eventoId, foto_id: fotoId }));
  }
}
