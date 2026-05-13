-- Migração Brazcom ISP
-- Objetivo: Adicionar campos de Equipamentos (Ativos) e Documentação Anatel
-- Data: 2026-05-13

USE brazcom_db;

-- 1. Adicionar novas colunas para controle de instalação e hardware
ALTER TABLE servicos_contratados 
    ADD COLUMN IF NOT EXISTS tipo_equipamento VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS modelo_equipamento VARCHAR(100) NULL,
    ADD COLUMN IF NOT EXISTS patrimonio_equipamento VARCHAR(50) NULL,
    ADD COLUMN IF NOT EXISTS is_comodato BOOLEAN DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS observacoes_instalacao TEXT NULL,
    ADD COLUMN IF NOT EXISTS contrato_anatel_url VARCHAR(500) NULL;

-- 2. Expandir campo de IP para suportar IPv6 (de 15 para 45 caracteres)
ALTER TABLE servicos_contratados 
    MODIFY COLUMN assigned_ip VARCHAR(45) NULL;

-- 3. (Opcional) Verificar se as colunas foram criadas corretamente
DESCRIBE servicos_contratados;
