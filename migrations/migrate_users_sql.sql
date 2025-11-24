-- Migration script: copy users from nf21 -> nfcom preserving IDs when possible
-- Usage: mysql -u occ -pAltavista740 < migrate_users_sql.sql
-- BEFORE RUNNING: review and backup both databases

SET autocommit=0;
START TRANSACTION;

-- Safety checks: show counts before
SELECT 'Source count' AS label, COUNT(*) FROM nf21.users;
SELECT 'Destination count' AS label, COUNT(*) FROM nfcom.users;

-- Detect id collisions (ids present in both DBs)
SELECT u.id, u.cpf AS src_cpf, d.cpf AS dst_cpf, u.email AS src_email, d.email AS dst_email
FROM nf21.users u
LEFT JOIN nfcom.users d ON u.id = d.id
WHERE d.id IS NOT NULL;

-- Option A (recommend): Insert only rows whose id does NOT already exist in destination
-- This preserves IDs for non-conflicting records and avoids overwriting existing rows.

SET FOREIGN_KEY_CHECKS = 0;

INSERT INTO nfcom.users (
  id, cpf, password, email, nome, data_nascimento, celular, image_file,
  data_ultimo_login, data_cadastro, verify_account, id_ultima_novidade
)
SELECT
  id, cpf, password, email, nome, data_nascimento, celular, image_file,
  data_ultimo_login, data_cadastro, verify_account, id_ultima_novidade
FROM nf21.users s
WHERE NOT EXISTS (SELECT 1 FROM nfcom.users d WHERE d.id = s.id);

-- For records that collided on id you must decide whether to:
--  1) Skip (safe default)
--  2) Update destination row with source values (may overwrite data)
--  3) Insert source row using a new id (requires mapping and updating foreign keys)
-- The script chooses option (1). You can inspect collisions above and act manually.

-- Reset auto_increment of destination to avoid duplicate keys on future inserts
SET @maxid = (SELECT COALESCE(MAX(id), 0) FROM nfcom.users);
SET @next = @maxid + 1;
SET @s = CONCAT('ALTER TABLE nfcom.users AUTO_INCREMENT = ', @next);
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET FOREIGN_KEY_CHECKS = 1;

COMMIT;

-- Post-checks
SELECT 'Source count' AS label, COUNT(*) FROM nf21.users;
SELECT 'Destination count' AS label, COUNT(*) FROM nfcom.users;

-- If you want to update destination rows based on cpf match (instead of id), use a targeted UPDATE.
-- Example (do NOT run blindly):
-- UPDATE nfcom.users d
-- JOIN nf21.users s ON s.cpf = d.cpf
-- SET d.email = s.email, d.nome = s.nome, d.celular = s.celular, d.image_file = s.image_file;

-- End of script
