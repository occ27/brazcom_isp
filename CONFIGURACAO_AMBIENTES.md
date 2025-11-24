# NFCom - Guia de Configuração de Ambientes

## 📋 Visão Geral

Este documento explica como configurar e executar o sistema NFCom em dois ambientes distintos:
- **Desenvolvimento Local**: Rodando diretamente no host (Windows)
- **Produção**: Usando Docker Compose (Linux/produção)

---

## 🔧 Ambiente de Desenvolvimento Local

### Portas em Desenvolvimento
- **Backend (FastAPI)**: `http://localhost:8000`
- **Frontend (React)**: `http://localhost:3000`
- **MySQL**: `localhost:3306`

### Configuração do Backend

1. **Arquivo**: `backend/.env`
   ```env
   DATABASE_URL=mysql+pymysql://occ:Altavista740@localhost:3306/nfcom
   CERTIFICATES_DIR=C:\etc\ssl\nfcom
   CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
   SECRET_KEY=dev_secret_key_change_in_production
   ```

2. **Executar Backend**:
   ```powershell
   cd backend
   # Ativar ambiente virtual Python
   .\venv\Scripts\Activate.ps1
   # Instalar dependências (primeira vez)
   pip install -r requirements.txt
   # Rodar servidor
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

### Configuração do Frontend

1. **Arquivo**: `frontend/.env`
   ```env
   REACT_APP_API_BASE_URL=http://localhost:8000
   ```

2. **Executar Frontend**:
   ```powershell
   cd frontend
   # Instalar dependências (primeira vez)
   npm install
   # Rodar servidor de desenvolvimento
   npm start
   ```
   O frontend abrirá automaticamente em `http://localhost:3000`

### Banco de Dados Local

- Instale o MySQL 8.0 localmente
- Crie o banco de dados:
  ```sql
  CREATE DATABASE nfcom CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
  CREATE USER 'occ'@'localhost' IDENTIFIED BY 'Altavista740';
  GRANT ALL PRIVILEGES ON nfcom.* TO 'occ'@'localhost';
  FLUSH PRIVILEGES;
  ```

- Execute as migrations:
  ```powershell
  cd backend
  alembic upgrade head
  ```

---

## 🐳 Ambiente de Produção (Docker)

### Portas em Produção
- **Backend (FastAPI)**: `http://localhost:8013` (container exposto)
- **Frontend (React)**: `http://localhost:3013` (container exposto)
- **MySQL**: `localhost:3313` (container exposto)
- **Domínio Público**: `https://nfcom.holeshot.com.br` (via Apache proxy reverso)

### Configuração do Backend

1. **Arquivo**: `backend/.env` (para produção, use as configurações de `.env.production`)
   ```env
   DATABASE_URL=mysql+pymysql://occ:Altavista740@db:3306/nfcom
   CERTIFICATES_DIR=/etc/ssl/nfcom
   CORS_ORIGINS=https://nfcom.holeshot.com.br,http://localhost:3013
   SECRET_KEY=MUDE_ESTA_CHAVE_SECRETA_EM_PRODUCAO
   ```

2. **Nota**: O arquivo `backend/.env.production` contém as configurações recomendadas para produção. Copie-o para `backend/.env` antes de fazer deploy.

### Configuração do Frontend

A variável de ambiente é definida no `docker-compose.yml`:
```yaml
environment:
  - REACT_APP_API_BASE_URL=/api
```

Isso faz o frontend usar caminhos relativos, e o Apache faz o proxy reverso de `/api` para o backend.

### Variáveis de Ambiente Raiz

**Arquivo**: `.env` (na raiz do projeto)
```env
MYSQL_DATABASE=nfcom
MYSQL_USER=occ
MYSQL_PASSWORD=Altavista740
MYSQL_ROOT_PASSWORD=Altavista740
CERTIFICATES_DIR=/etc/ssl/nfcom
```

### Executar em Produção

```bash
# Subir todos os containers
docker-compose up -d

# Ver logs
docker-compose logs -f

# Parar containers
docker-compose down

# Reconstruir após mudanças no código
docker-compose up -d --build
```

### Configuração do Apache (Proxy Reverso)

Para o domínio `nfcom.holeshot.com.br`, configure o Apache para fazer proxy reverso:

```apache
<VirtualHost *:80>
    ServerName nfcom.holeshot.com.br
    
    # Redirecionar para HTTPS
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
</VirtualHost>

<VirtualHost *:443>
    ServerName nfcom.holeshot.com.br
    
    SSLEngine on
    SSLCertificateFile /caminho/certificado.crt
    SSLCertificateKeyFile /caminho/chave.key
    
    # Frontend (React)
    ProxyPass / http://localhost:3013/
    ProxyPassReverse / http://localhost:3013/
    
    # Backend (API)
    ProxyPass /api http://localhost:8013/
    ProxyPassReverse /api http://localhost:8013/
    
    # WebSocket support (se necessário)
    ProxyPass /ws ws://localhost:8013/ws
    ProxyPassReverse /ws ws://localhost:8013/ws
    
    # Headers
    ProxyPreserveHost On
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
</VirtualHost>
```

---

## 📊 Resumo das Configurações

| Ambiente | Backend | Frontend | MySQL | Certificados |
|----------|---------|----------|-------|--------------|
| **Desenvolvimento** | localhost:8000 | localhost:3000 | localhost:3306 | C:\etc\ssl\nfcom |
| **Produção (Docker)** | localhost:8013 | localhost:3013 | localhost:3313 | /etc/ssl/nfcom |
| **Produção (Público)** | nfcom.holeshot.com.br/api | nfcom.holeshot.com.br | (interno) | (interno) |

---

## 🔐 Checklist de Segurança para Produção

- [ ] Alterar `SECRET_KEY` no `backend/.env` para uma chave forte e aleatória
- [ ] Configurar `CORS_ORIGINS` com apenas os domínios necessários
- [ ] Usar HTTPS no domínio público (certificado SSL válido)
- [ ] Proteger acesso ao diretório de certificados
- [ ] Fazer backup regular do banco de dados
- [ ] Configurar firewall para expor apenas as portas necessárias ao Apache
- [ ] Revisar logs regularmente

---

## 🆘 Troubleshooting

### Backend não conecta ao banco de dados
- **Dev**: Verifique se o MySQL está rodando em `localhost:3306`
- **Prod**: Verifique se o container `db` está UP: `docker-compose ps`

### Frontend não acessa a API
- **Dev**: Verifique se `frontend/.env` tem `REACT_APP_API_BASE_URL=http://localhost:8000`
- **Prod**: Verifique se o Apache está fazendo proxy corretamente de `/api` para `localhost:8013`

### Erro de CORS
- Verifique se a origem do frontend está listada em `CORS_ORIGINS` no `backend/.env`
- Em desenvolvimento: `http://localhost:3000`
- Em produção: `https://nfcom.holeshot.com.br`

### Certificados não encontrados
- **Dev**: Certifique-se que o diretório `C:\etc\ssl\nfcom` existe
- **Prod**: Verifique o volume montado no `docker-compose.yml`

---

## 📝 Notas Adicionais

- Sempre reinicie o backend após alterar o `.env`
- O frontend precisa ser reconstruído (`npm run build`) após alterar variáveis de ambiente em produção
- Use `docker-compose logs <serviço>` para debugar problemas nos containers
- Mantenha backups regulares do diretório de certificados

---

**Última atualização**: Novembro 2025
