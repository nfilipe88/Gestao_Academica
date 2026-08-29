import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface Destaque {
  titulo: string;
  descricao: string;
  icone: string; // path SVG (viewBox 0 0 24 24, mesmo conjunto de ícones do resto da app)
}

interface Razao {
  titulo: string;
  descricao: string;
}

const DESTAQUES: Destaque[] = [
  {
    titulo: 'Académico completo',
    descricao: 'Cursos, turmas, disciplinas, grade curricular, matrículas e diário de classe — notas, frequência e avaliações num só sítio.',
    icone: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25',
  },
  {
    titulo: 'Financeiro e propinas',
    descricao: 'Contratos, faturação mensal, recibos automáticos e pagamento online — com conciliação e histórico por aluno.',
    icone: 'M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    titulo: 'Comunicação com famílias',
    descricao: 'Comunicados com anexos, notificações por e-mail e SMS, e um portal próprio para alunos e encarregados de educação.',
    icone: 'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z',
  },
  {
    titulo: 'Captação e admissões',
    descricao: 'Funil de CRM para leads de novos alunos, com formulário público de captação embutido no site da própria escola.',
    icone: 'M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z',
  },
  {
    titulo: 'Documentos automáticos',
    descricao: 'Certificados, declarações, boletins e históricos escolares gerados em PDF, com modelos personalizáveis por escola.',
    icone: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  },
  {
    titulo: 'Multi-escola e segurança',
    descricao: 'Cada escola isolada por definição (isolamento a nível de base de dados), com trilha de auditoria completa e sessões protegidas.',
    icone: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z',
  },
];

const RAZOES: Razao[] = [
  { titulo: 'Cada escola, isolada de verdade', descricao: 'Os dados de uma instituição nunca ficam visíveis a outra — reforçado a nível de base de dados, não só na aplicação.' },
  { titulo: 'Sabe sempre quem fez o quê', descricao: 'Trilha de auditoria automática: quem criou, alterou ou apagou cada registo, e quando.' },
  { titulo: 'Preço justo, sem surpresas', descricao: 'Paga por aluno matriculado, mais só os módulos que a sua escola realmente usa.' },
  { titulo: 'Pronta para crescer', descricao: 'Testada sob carga, com a infraestrutura dimensionada para dezenas de escolas em simultâneo.' },
];

@Component({
  selector: 'app-landing.component',
  imports: [RouterLink],
  templateUrl: './landing.component.html',
  styleUrl: './landing.component.css',
})
export class LandingComponent {
  destaques = DESTAQUES;
  razoes = RAZOES;
}
