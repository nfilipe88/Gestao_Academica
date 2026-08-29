import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

interface Modulo {
  titulo: string;
  descricao: string;
  pontos: string[];
  icone: string;
}

const MODULOS: Modulo[] = [
  {
    titulo: 'Estrutura Académica',
    descricao: 'A base de tudo: cursos, séries/anos, turmas, disciplinas e grade curricular, ligados às matrículas de cada aluno.',
    pontos: ['Cursos e séries/anos configuráveis', 'Turmas com vagas e ano letivo', 'Grade curricular por disciplina', 'Matrículas com histórico'],
    icone: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25',
  },
  {
    titulo: 'Diário de Classe',
    descricao: 'Lançamento de notas e frequência por professor, com períodos de avaliação e trilha de alterações.',
    pontos: ['Notas por período de avaliação', 'Registo de frequência por aula', 'Trilha de alterações a notas já lançadas', 'Alocação de professor por turma/disciplina'],
    icone: 'M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25',
  },
  {
    titulo: 'Avaliações e Exames',
    descricao: 'Bancos de questões, exames com correção automática e materiais de aula organizados por turma.',
    pontos: ['Banco de questões reutilizável', 'Exames com tentativas registadas', 'Materiais de aula publicáveis', 'Acesso direto pelo Portal do Aluno'],
    icone: 'M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08M8.25 4.5a2.25 2.25 0 012.25-2.25h1.5a2.25 2.25 0 012.25 2.25v.008h-6V4.5z',
  },
  {
    titulo: 'Financeiro e Propinas',
    descricao: 'Contratos financeiros por aluno, faturação mensal automática, recibos e pagamento online.',
    pontos: ['Tabela de propinas por série/ano', 'Faturação mensal automática', 'Recibos numerados sequencialmente', 'Pagamento online (PayPal)'],
    icone: 'M12 6v12m-3-2.818l.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  },
  {
    titulo: 'Comunicação e Notificações',
    descricao: 'Comunicados com anexos para famílias e staff, com envio por e-mail e SMS.',
    pontos: ['Comunicados com ficheiros anexos', 'Fila de notificações com repetição automática em falha', 'Envio por e-mail e SMS', 'Alertas de acesso a partir de um local novo'],
    icone: 'M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z',
  },
  {
    titulo: 'Captação de Alunos (CRM)',
    descricao: 'Funil de admissões para acompanhar candidatos desde o primeiro contacto até à matrícula.',
    pontos: ['Formulário público incorporável no site da escola', 'Funil Kanban por etapa', 'Histórico de contacto por candidato'],
    icone: 'M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z',
  },
  {
    titulo: 'Documentos',
    descricao: 'Emissão de certificados, declarações, boletins e históricos escolares em PDF.',
    pontos: ['Modelos personalizáveis por escola', 'Pré-visualização antes de gravar', 'Pedido e entrega com histórico', 'Preços configuráveis por tipo de documento'],
    icone: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z',
  },
  {
    titulo: 'Trabalhos, Horários e Transferências',
    descricao: 'Trabalhos de casa com submissão e avaliação, horário semanal por turma, e pedidos de transferência entre escolas.',
    pontos: ['Trabalhos/tarefas com prazo e avaliação', 'Grelha de horários por turma', 'Transferência de aluno entre instituições'],
    icone: 'M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25',
  },
  {
    titulo: 'Portal do Aluno e Encarregado',
    descricao: 'Um acesso próprio para alunos e famílias consultarem notas, frequência, materiais e faturas — sem depender do staff.',
    pontos: ['Notas e frequência em tempo real', 'Materiais de aula e exames', 'Faturas e histórico de pagamento', 'Pedidos de documentos'],
    icone: 'M17.982 18.725A7.488 7.488 0 0012 15.75a7.488 7.488 0 00-5.982 2.975m11.963 0a9 9 0 10-11.963 0m11.963 0A8.966 8.966 0 0112 21a8.966 8.966 0 01-5.982-2.275M15 9.75a3 3 0 11-6 0 3 3 0 016 0z',
  },
  {
    titulo: 'Gestão de Acessos e Auditoria',
    descricao: 'Controlo por perfil (Gestor, Secretaria, Professor, Aluno, Encarregado) e um registo automático de toda a atividade.',
    pontos: ['Perfis com permissões distintas', 'Suspensão/reativação individual de contas', 'Trilha de auditoria automática (quem, quando, o quê)', 'Mapa de permissões por módulo'],
    icone: 'M16.5 10.5V6.75a4.5 4.5 0 10-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 002.25-2.25v-6.75a2.25 2.25 0 00-2.25-2.25H6.75a2.25 2.25 0 00-2.25 2.25v6.75a2.25 2.25 0 002.25 2.25z',
  },
  {
    titulo: 'Segurança e Isolamento entre Escolas',
    descricao: 'Cada instituição é um "tenant" isolado ao nível da própria base de dados — não só na aplicação.',
    pontos: ['Isolamento reforçado por Row-Level Security', 'Sessões com token de curta duração e renovação automática', 'Histórico de início de sessão com alerta de local novo', 'Política de força mínima de palavra-passe'],
    icone: 'M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z',
  },
  {
    titulo: 'Indicadores e Escala',
    descricao: 'Painéis de indicadores para acompanhar a escola, numa infraestrutura testada para crescer com o número de escolas.',
    pontos: ['Indicadores académicos e financeiros', 'Trilha de recuperação de alunos em risco', 'Base de dados indexada e dimensionada para múltiplas escolas em simultâneo'],
    icone: 'M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z',
  },
];

@Component({
  selector: 'app-funcionalidades.component',
  imports: [RouterLink],
  templateUrl: './funcionalidades.component.html',
  styleUrl: './funcionalidades.component.css',
})
export class FuncionalidadesComponent {
  modulos = MODULOS;
}
