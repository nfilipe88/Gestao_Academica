import { Pipe, PipeTransform, inject } from '@angular/core';
import { NomesPerfisService } from '../../core/services/nomes-perfis.service';

/**
 * {{ 'GESTOR' | nomePerfil }} → "Gestor" (ou o nome que o Super Admin
 * tiver definido, ex.: "Diretor Geral"). Impuro de propósito: lê um
 * signal do serviço, por isso atualiza sozinho quando os nomes chegam
 * ou mudam.
 */
@Pipe({ name: 'nomePerfil', pure: false })
export class NomePerfilPipe implements PipeTransform {
  private nomes = inject(NomesPerfisService);

  transform(codigo: string | null | undefined): string {
    return this.nomes.nome(codigo);
  }
}
