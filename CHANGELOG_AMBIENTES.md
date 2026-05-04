# 📝 Changelog - Reorganização de Ambientes

**Data**: 05/11/2025
**Autor**: GitHub Copilot

## 🎯 Objetivo

Separar e organizar corretamente as configurações de desenvolvimento local e produção (Docker), eliminando a confusão de portas e URLs hardcoded no código.

---

## ✅ Arquivos Criados

### Configuração
- ✨ **`frontend/.env`** - Variáveis de ambiente do frontend (desenvolvimento)
- ✨ **`frontend/.env.example`** - Template de configuração frontend
- ✨ **`backend/.env.example`** - Template de configuração backend
- ✨ **`backend/.env.production`** - Configurações específicas para produção

### Documentação
- ✨ **`CONFIGURACAO_AMBIENTES.md`** - Guia completo de configuração
- ✨ **`QUICK_START.md`** - Guia rápido de início

---

## 🔧 Arquivos Modificados

### Backend
- **`backend/app/core/config.py`**
  - ✅ Valores padrão ajustados para desenvolvimento local
  - ✅ DATABASE_URL padrão: `localhost:3306`
  - ✅ CORS_ORIGINS padrão: `localhost:3000`
  - ✅ CERTIFICATES_DIR detecta automaticamente Windows/Linux

- **`backend/.env`**
  - ✅ Configurado para desenvolvimento local
  - ✅ Conexão MySQL em `localhost:3306`
  - ✅ Certificados em `C:\etc\ssl\nfcom`
  - ✅ CORS permite `localhost:3000`

### Frontend
- **`frontend/src/services/api.js`**
  - ✅ Fallback padrão mudado de `:8013` para `:8000`
  - ✅ Documentação clara sobre dev vs. produção
  - ✅ Comentários explicativos sobre cada ambiente

- **`frontend/src/pages/NFCom.tsx`**
  - ✅ Removidas URLs hardcoded `REACT_APP_BACKEND_URL`
  - ✅ Removidos construções manuais de URLs com `:8000`
  - ✅ Usa exclusivamente a instância `api` configurada

### Docker
- **`docker-compose.yml`**
  - ✅ Comentários adicionados explicando portas de produção
  - ✅ Variáveis de ambiente injetadas no backend
  - ✅ DATABASE_URL sobrescrito para usar serviço `db`
  - ✅ CERTIFICATES_DIR sobrescrito para `/etc/ssl/nfcom`

- **`.env`** (raiz)
  - ✅ Reorganizado com comentários claros
  - ✅ Documentado uso para Windows e Linux

- **`.env.example`** (raiz)
  - ✅ Atualizado com instruções mais claras
  - ✅ Referência aos arquivos de configuração do backend

---

## 🌍 Configuração de Ambientes

### Desenvolvimento Local (Windows)
```
Backend:  localhost:8000
Frontend: localhost:3000
MySQL:    localhost:3306
Certs:    C:\etc\ssl\nfcom
```

### Produção (Docker + Apache)
```
Backend:  localhost:8013 (container)
Frontend: localhost:3013 (container)
MySQL:    localhost:3313 (container)
Público:  nfcom.holeshot.com.br
  - Frontend: / → :3013
  - Backend:  /api → :8013
Certs:    /etc/ssl/nfcom
```

---

## 🔑 Principais Mudanças

### 1. Separação Clara de Ambientes
- Arquivos `.env` específicos para cada ambiente
- Valores padrão no código refletem desenvolvimento local
- Produção sobrescreve via variáveis de ambiente

### 2. Eliminação de Hardcoded URLs
- ❌ Removido: `localhost:8013` hardcoded no frontend
- ❌ Removido: `REACT_APP_BACKEND_URL` construindo URLs manualmente
- ✅ Adicionado: Uso exclusivo da instância `api` configurada

### 3. Configuração Centralizada
- `frontend/.env` controla URL da API
- `backend/.env` controla banco, CORS e certificados
- `docker-compose.yml` sobrescreve para produção

### 4. Documentação Completa
- Guia detalhado: `CONFIGURACAO_AMBIENTES.md`
- Referência rápida: `QUICK_START.md`
- Templates: `.env.example` em cada diretório

---

## 📋 Próximos Passos Recomendados

### Para Desenvolvimento
1. ✅ Arquivos já estão configurados
2. Verificar se MySQL está rodando em `localhost:3306`
3. Criar diretório `C:\etc\ssl\nfcom` se não existir
4. Executar migrations: `cd backend && alembic upgrade head`

### Para Produção
1. ⚠️ **Copiar** `backend/.env.production` para `backend/.env`
2. ⚠️ **Alterar** `SECRET_KEY` para valor forte e aleatório
3. Verificar configuração do Apache (proxy reverso)
4. Testar conectividade: frontend → /api → backend

---

## 🐛 Problemas Corrigidos

- ✅ Frontend tentava conectar em `:8013` localmente (porta Docker)
- ✅ URLs hardcoded causavam falhas em diferentes ambientes
- ✅ CORS configurado como `*` expunha riscos de segurança
- ✅ Falta de documentação causava confusão na configuração
- ✅ Certificados com caminhos inconsistentes entre ambientes

---

## 🔒 Melhorias de Segurança

- ✅ CORS agora especifica origens permitidas explicitamente
- ✅ SECRET_KEY diferente para dev/prod (lembrete para alterar)
- ✅ Documentação de checklist de segurança
- ✅ `.gitignore` já configurado para não commitar `.env`

---

## 📚 Referências

- `CONFIGURACAO_AMBIENTES.md` - Documentação completa
- `QUICK_START.md` - Guia de início rápido
- `backend/.env.example` - Template backend
- `frontend/.env.example` - Template frontend
- `.env.example` - Template Docker Compose

---

**Status**: ✅ Concluído e testável
