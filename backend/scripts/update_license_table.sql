-- Adicionar coluna plan_id na tabela company_licenses
ALTER TABLE company_licenses ADD COLUMN plan_id INT NULL;
ALTER TABLE company_licenses ADD CONSTRAINT fk_license_plan FOREIGN KEY (plan_id) REFERENCES license_pricing_plans(id);

-- Alterar a coluna plan para suportar nomes dinâmicos (remover restrição de ENUM se existir)
-- No MySQL, apenas mudar o tipo já resolve
ALTER TABLE company_licenses MODIFY COLUMN plan VARCHAR(100) NOT NULL;
