-- Ativar a extensão para geração de UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Tabela Global: Tenant (A Instituição de Ensino)
CREATE TABLE tenant (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    nome_fantasia VARCHAR(255) NOT NULL,
    razao_social VARCHAR(255),
    cnpj_nif VARCHAR(50) UNIQUE,
    status VARCHAR(50) DEFAULT 'ATIVO',
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Tabela Base: Utilizadores (Gestão de Acesso)
CREATE TABLE usuario (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id UUID NOT NULL REFERENCES tenant(id) ON DELETE CASCADE,
    nome_completo VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    senha_hash VARCHAR(255) NOT NULL,
    perfil_acesso VARCHAR(50) NOT NULL, -- SUPER_ADMIN, GESTOR, PROFESSOR, etc.
    data_criacao TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- ==========================================
-- POLÍTICAS DE SEGURANÇA MULTI-TENANT (RLS)
-- ==========================================

-- 1. Ativar o RLS na tabela de utilizadores
ALTER TABLE usuario ENABLE ROW LEVEL SECURITY;

-- 2. Criar a política de isolamento
-- Esta regra diz: "Um utilizador só pode ler/escrever linhas onde o tenant_id 
-- corresponda ao tenant_id configurado na sessão atual da base de dados."
CREATE POLICY isolamento_tenant_usuario ON usuario
    USING (tenant_id = current_setting('app.current_tenant_id', true)::UUID);