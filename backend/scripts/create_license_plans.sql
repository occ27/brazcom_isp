CREATE TABLE IF NOT EXISTS license_pricing_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    price FLOAT NOT NULL,
    duration_months INT NOT NULL DEFAULT 12,
    is_active BOOLEAN DEFAULT TRUE,
    is_highlighted BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

INSERT INTO license_pricing_plans (name, description, price, duration_months, is_highlighted) 
VALUES ('ANUAL', 'Acesso completo por 12 meses', 300.0, 12, FALSE);

INSERT INTO license_pricing_plans (name, description, price, duration_months, is_highlighted) 
VALUES ('BIANUAL', 'Acesso completo por 24 meses com desconto especial', 500.0, 24, TRUE);
