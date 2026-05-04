# 🚀 Guia Rápido - NFCom Ambientes

## ⚡ Início Rápido

### Desenvolvimento Local
```powershell
# Backend
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (novo terminal)
cd frontend
npm start
```

**Acesse**: http://localhost:3000

---

### Produção (Docker)
```bash
# Copiar configuração de produção
cp backend/.env.production backend/.env

# Subir containers
docker-compose up -d

# Ver logs
docker-compose logs -f
```

**Acesse**: https://nfcom.holeshot.com.br

---

## 📊 Tabela de Portas

| Serviço | Desenvolvimento | Produção (Docker) | Público |
|---------|----------------|-------------------|---------|
| Backend | :8000 | :8013 | /api |
| Frontend | :3000 | :3013 | / |
| MySQL | :3306 | :3313 | - |

---

## 📁 Arquivos Importantes

### Desenvolvimento
- `backend/.env` → Configuração local
- `frontend/.env` → API em localhost:8000

### Produção
- `backend/.env` → Copiar de `.env.production`
- `.env` (raiz) → Configurações Docker
- Apache → Proxy reverso /api → :8013

---

## 🔧 Configurações Principais

### Backend (`backend/.env`)

**Dev:**
```env
DATABASE_URL=mysql+pymysql://occ:Altavista740@localhost:3306/nfcom
CERTIFICATES_DIR=C:\etc\ssl\nfcom
CORS_ORIGINS=http://localhost:3000
```

**Prod:**
```env
DATABASE_URL=mysql+pymysql://occ:Altavista740@db:3306/nfcom
CERTIFICATES_DIR=/etc/ssl/nfcom
CORS_ORIGINS=https://nfcom.holeshot.com.br
```

### Frontend (`frontend/.env`)

**Dev:**
```env
REACT_APP_API_BASE_URL=http://localhost:8000
```

**Prod (docker-compose.yml):**
```yaml
environment:
  - REACT_APP_API_BASE_URL=/api
```

---

## ⚠️ Checklist de Deploy

- [ ] Copiar `backend/.env.production` para `backend/.env`
- [ ] Alterar `SECRET_KEY` para chave forte
- [ ] Configurar `CORS_ORIGINS` com domínio de produção
- [ ] Verificar `CERTIFICATES_DIR` está correto
- [ ] Apache configurado para proxy reverso
- [ ] Certificado SSL válido instalado
- [ ] Backup do banco de dados

---

## 🆘 Troubleshooting Rápido

**Frontend não conecta no backend:**
- Dev: Verificar `frontend/.env` tem `http://localhost:8000`
- Prod: Verificar Apache proxy `/api` → `localhost:8013`

**Erro de CORS:**
- Adicionar origem em `CORS_ORIGINS` no `backend/.env`

**Banco não conecta:**
- Dev: MySQL rodando em `localhost:3306`?
- Prod: `docker-compose ps` mostra `db` UP?

---

📖 **Documentação completa**: `CONFIGURACAO_AMBIENTES.md`
