-- =============================================================================
-- MIGRATION: NOVO MODELO DE ATIVOS/EQUIPAMENTOS MÚLTIPLOS POR CONTRATO
-- =============================================================================

-- 1. Criar a nova tabela de ativos (suporta múltiplos aparelhos por cliente)
CREATE TABLE IF NOT EXISTS ativos_contrato (
    id INT AUTO_INCREMENT PRIMARY KEY,
    contrato_id INT NOT NULL,
    tipo_equipamento VARCHAR(50) NOT NULL COMMENT 'ROTEADOR, ONT, BRIDGE, RADIO, etc',
    modelo VARCHAR(100),
    patrimonio VARCHAR(50),
    serial_number VARCHAR(100),
    login_acesso VARCHAR(100) COMMENT 'Login para acesso técnico/manutenção',
    senha_acesso VARCHAR(100) COMMENT 'Senha para acesso técnico/manutenção',
    is_comodato BOOLEAN DEFAULT TRUE,
    observacoes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_contrato_ativo FOREIGN KEY (contrato_id) 
        REFERENCES servicos_contratados(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 2. Limpeza do esquema antigo na tabela servicos_contratados
-- (Removendo colunas fixas para evitar redundância e confusão)
-- Obs: Se o seu MySQL for versão < 8.0.19, o 'IF EXISTS' no DROP COLUMN pode não funcionar.
-- Se der erro, rode apenas as linhas sem o 'IF EXISTS'.

ALTER TABLE servicos_contratados DROP COLUMN IF EXISTS tipo_equipamento;
ALTER TABLE servicos_contratados DROP COLUMN IF EXISTS modelo_equipamento;
ALTER TABLE servicos_contratados DROP COLUMN IF EXISTS patrimonio_equipamento;
ALTER TABLE servicos_contratados DROP COLUMN IF EXISTS is_comodato;
ALTER TABLE servicos_contratados DROP COLUMN IF EXISTS observacoes_instalacao;

-- 3. Garantir que o campo assigned_ip suporte IPv6
ALTER TABLE servicos_contratados MODIFY COLUMN assigned_ip VARCHAR(45);
