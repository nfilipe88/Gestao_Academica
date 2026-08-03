src/app/
│
├── core/                   # Serviços vitais, interceptors e guards (carregados 1x)
│   ├── auth/               # Lógica de autenticação (AuthService)
│   ├── interceptors/       # jwt.interceptor.ts, error.interceptor.ts
│   └── guards/             # tenant.guard.ts, auth.guard.ts
│
├── shared/                 # Componentes visuais burros (Tailwind) e utilitários globais
│   ├── components/         # Botoes, Modais, Tabelas, Sidebar
│   └── pipes/              # Formatação de moeda, datas
│
├── features/               # Os módulos de negócio do seu SaaS (Lazy Loaded)
│   ├── admin/              # Ecrãs do Super Admin (gerir tenants)
│   ├── academico/          # Diário de classe, matrículas
│   ├── financeiro/         # Faturas, pagamentos
│   └── public/             # Login, página de registo do CRM
│
├── store/                  # Gestão de Estado Global (Redux / NgRx)
│   ├── auth/               # Estado do utilizador logado e permissões
│   │   ├── auth.actions.ts
│   │   ├── auth.reducer.ts
│   │   └── auth.selectors.ts
│   └── tenant/             # Dados globais da escola atual
│
├── app.component.ts        # Root component
├── app.routes.ts           # Roteamento global (Lazy Loading das features)
└── app.config.ts           # Configuração de providers globais (antigo app.module)

cd D:\Projects_To_Implement\Gestao_Academica

# Se ainda não é um repositório git local:
git init
git branch -M main

# Conectar ao repositório remoto (só precisa fazer uma vez)
git remote add origin https://github.com/nfilipe88/Gestao_Academica.git

# Trazer o que já existe lá (README.md e .gitignore), para não dar conflito
git fetch origin
git merge origin/main --allow-unrelated-histories

git add .
git status

git commit -m "Setup inicial: front-end Angular + backend FastAPI com auth, RLS e migrations"
git push -u origin main


# Gacademic

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 21.1.4.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
