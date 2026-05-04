# 🌐 Configuração Apache - Proxy Reverso para NFCom

## 📋 Visão Geral

Este arquivo contém a configuração do Apache para fazer proxy reverso do domínio `nfcom.holeshot.com.br` para os containers Docker rodando localmente.
A configuração assume que o Cloudflare está gerenciando o SSL e redirecionando HTTP para HTTPS.

---

## 🔌 Módulos Necessários

```bash
# Ativar módulos do Apache (Linux)
sudo a2enmod proxy
sudo a2enmod proxy_http
sudo a2enmod proxy_wstunnel  # Para WebSocket (se necessário)
sudo a2enmod ssl
sudo a2enmod rewrite
sudo a2enmod headers

# Reiniciar Apache
sudo systemctl restart apache2
```

---

## ⚙️ Configuração do VirtualHost

### Arquivo: `/etc/apache2/sites-available/nfcom.conf`

```apache
# ========================================================================
# ========================================================================
# NFCom - HTTP (Redireciona para HTTPS)
# ========================================================================
<VirtualHost *:80>
    ServerName nfcom.holeshot.com.br
    ServerAdmin admin@holeshot.com.br
    
    # Redirecionar todo tráfego HTTP para HTTPS
    # Esta regra é desnecessária se o Cloudflare já faz o redirecionamento HTTP->HTTPS.
    # Mantenha-a comentada ou remova se o Cloudflare estiver configurado para "Full" ou "Full (strict)" SSL.
    # Se o Cloudflare estiver em "Flexible" SSL, o Apache receberá HTTP e esta regra seria útil,
    # mas o ideal é configurar o Cloudflare para "Full" ou "Full (strict)" para segurança ponta a ponta.
    # No seu caso, como o Cloudflare já faz o redirecionamento, esta seção pode ser removida ou comentada.
    # No entanto, se o Apache estiver recebendo HTTP do Cloudflare (modo Flexible),
    # esta configuração de VirtualHost *:80 é a que será usada.
    # Vamos focar em corrigir o comportamento do proxy dentro deste bloco.
    
    # IMPORTANTE: A ordem importa! /api DEVE vir ANTES de /
    ProxyPreserveHost On
    ProxyTimeout 300 # Adicionado para consistência e controle de timeout

    # Backend API - DEVE VIR PRIMEIRO
    # Usar ProxyPass sem nocanon para permitir redirects internos
    ProxyPass /api http://127.0.0.1:8013
    ProxyPassReverse /api http://127.0.0.1:8013
    ProxyPassReverseCookiePath /api/ /

    # Arquivos estáticos do backend (se houver)
    ProxyPass /files http://127.0.0.1:8013/files
    ProxyPassReverse /files http://127.0.0.1:8013/files

    # Frontend - vem depois (excluindo /api e /files)
    ProxyPass / http://127.0.0.1:3013/
    ProxyPassReverse / http://127.0.0.1:3013/

    # Headers para Cloudflare
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-For "%{REMOTE_ADDR}s"

    # Forçar reescrita de Location headers para HTTPS e adicionar /api prefixo.
    # Isso é crucial porque um backend ciente do proxy pode gerar URLs externas
    # que ProxyPassReverse não reescreveria, e precisamos garantir o prefixo /api.
    # Esta regra corrige o redirecionamento 307, adicionando o /api que falta.
    # Ela captura URLs que começam com http:// ou https:// e garante o prefixo /api e o esquema https.
    Header edit Location "^(http|https)://nfcom\.holeshot\.com\.br/empresas/(.*)$" "https://nfcom.holeshot.com.br/api/empresas/$2"

    # Logs
    ErrorLog ${APACHE_LOG_DIR}/nfcom-error.log
    CustomLog ${APACHE_LOG_DIR}/nfcom-access.log combined

    # ========================================================================
    # NFCom - HTTPS (Produção) - Este bloco é desnecessário se o Cloudflare
    # está terminando o SSL e encaminhando para o Apache via HTTP na porta 80.
    # Se o Cloudflare estiver configurado para "Full" ou "Full (strict)" SSL,
    # então este bloco *seria* o correto para o Apache receber HTTPS.
    # Com base na sua afirmação de que o VirtualHost *:80 funciona para outros
    # sistemas, vamos assumir que o tráfego chega em HTTP ao Apache.
    # Portanto, este bloco pode ser removido ou mantido para um cenário futuro.
    # Por enquanto, focaremos no VirtualHost *:80.
    # ========================================================================
    # <VirtualHost *:443>
    #     ServerName nfcom.holeshot.com.br
    #     ServerAdmin admin@holeshot.com.br
    #     
    #     # SSL/TLS Configuration
    #     SSLEngine on
    #     SSLCertificateFile /caminho/para/certificado.crt
    #     SSLCertificateKeyFile /caminho/para/chave-privada.key
    #     SSLCertificateChainFile /caminho/para/cadeia.crt  # Se aplicável
    #     
    #     # Protocolos e Ciphers Seguros
    #     SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1
    #     SSLCipherSuite HIGH:!aNULL:!MD5:!3DES
    #     SSLHonorCipherOrder on
    #     
    #     ProxyPreserveHost On
    #     ProxyTimeout 300
    #     
    #     # ====================================================================
    #     # Proxy para Backend API (FastAPI) - Porta 8013
    #     # ====================================================================
    #     # Todas as requisições para /api/* são redirecionadas para o backend
    #     # A regra mais específica (/api) deve vir ANTES da regra mais genérica (/).
    #     ProxyPass /api http://localhost:8013
    #     ProxyPassReverse /api http://localhost:8013
    # 
    #     # ====================================================================
    #     # Proxy para Frontend (React) - Porta 3013
    #     # ====================================================================
    #     # A regra genérica (/) deve vir DEPOIS da regra da API.
    #     ProxyPass / http://localhost:3013/
    #     ProxyPassReverse / http://localhost:3013/
    #     
    #     # ====================================================================
    #     # WebSocket Support (se necessário para recursos em tempo real)
    #     # ====================================================================
    #     # Descomente se usar WebSockets
    #     # ProxyPass /ws ws://localhost:8013/ws
    #     # ProxyPassReverse /ws ws://localhost:8013/ws
    #     
    #     # ====================================================================
    #     # Headers de Segurança
    #     # ====================================================================
    #     Header always set X-Frame-Options "SAMEORIGIN"
    #     Header always set X-Content-Type-Options "nosniff"
    #     Header always set X-XSS-Protection "1; mode=block"
    #     Header always set Referrer-Policy "strict-origin-when-cross-origin"
    #     Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    #     
    #     # Informar ao backend sobre o protocolo original
    #     RequestHeader set X-Forwarded-Proto "https"
    #     RequestHeader set X-Forwarded-Port "443"
    #     
    #     # Forçar reescrita de Location headers para HTTPS e adicionar /api prefixo.
    #     # Isso é crucial porque um backend ciente do proxy pode gerar URLs externas
    #     # que ProxyPassReverse não reescreveria, e precisamos garantir o prefixo /api.
    #     # Esta regra corrige o redirecionamento 307, adicionando o /api que falta.
    #     Header edit Location ^http://nfcom\.holeshot\.com\.br/empresas/(.*)$ https://nfcom.holeshot.com.br/api/empresas/$1
    #     
    #     # ====================================================================
    #     # Logs
    #     # ====================================================================
    #     ErrorLog ${APACHE_LOG_DIR}/nfcom-ssl-error.log
    #     CustomLog ${APACHE_LOG_DIR}/nfcom-ssl-access.log combined
    #     
    #     # ====================================================================
    #     # Limites e Timeouts (ajuste conforme necessário)
    #     # ====================================================================
    #     # Para upload de arquivos grandes (certificados, XMLs, etc.)
    #     LimitRequestBody 52428800  # 50MB
    #     
    # </VirtualHost>
    # ```

---

## 🚀 Ativação do Site

```bash
# Copiar arquivo de configuração
sudo nano /etc/apache2/sites-available/nfcom.conf

# Colar a configuração acima (ajustando caminhos dos certificados SSL)

# Ativar o site
sudo a2ensite nfcom.conf

# Testar configuração
sudo apache2ctl configtest

# Se "Syntax OK", recarregar Apache
sudo systemctl reload apache2
```

---

## 🔐 Certificado SSL

### Opção 1: Let's Encrypt (Gratuito e Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-apache

# Obter certificado
sudo certbot --apache -d nfcom.holeshot.com.br

# Certbot configurará automaticamente o Apache
# E criará renovação automática
```

### Opção 2: Certificado Próprio

Se já possui certificado:
1. Copie os arquivos para um local seguro (ex: `/etc/ssl/nfcom/`)
2. Ajuste os caminhos no VirtualHost:
   ```apache
   SSLCertificateFile /etc/ssl/nfcom/certificado.crt
   SSLCertificateKeyFile /etc/ssl/nfcom/chave-privada.key
   SSLCertificateChainFile /etc/ssl/nfcom/cadeia.crt
   ```

---

## 🧪 Testando a Configuração

### 1. Verificar containers Docker estão rodando
```bash
docker-compose ps
# Deve mostrar: backend (8013), frontend (3013), db (3313)
```

### 2. Testar acesso local às portas
```bash
# Backend
curl http://localhost:8013/docs
# Deve retornar a documentação da API

# Frontend
curl http://localhost:3013
# Deve retornar HTML do React
```

### 3. Testar proxy reverso
```bash
# Frontend via domínio
curl https://nfcom.holeshot.com.br

# API via domínio
curl https://nfcom.holeshot.com.br/api/docs
```

### 4. Testar no navegador
- Acesse: `https://nfcom.holeshot.com.br`
- Faça login
- Verifique console do navegador (F12) para erros de conexão

---

## 🔍 Troubleshooting

### 502 Bad Gateway
**Causa**: Apache não consegue conectar aos containers
```bash
# Verificar containers
docker-compose ps

# Verificar logs do Apache
sudo tail -f /var/log/apache2/nfcom-error.log

# Verificar conectividade
curl http://localhost:8013
curl http://localhost:3013
```

### 503 Service Unavailable
**Causa**: Containers não estão respondendo
```bash
# Ver logs dos containers
docker-compose logs backend
docker-compose logs frontend
```

### Erro de SSL/Certificado
```bash
# Se você estiver usando o VirtualHost *:443, verifique:
# sudo openssl x509 -in /caminho/certificado.crt -text -noout
# sudo certbot certificates
```

### Erro CORS
**Causa**: Backend não está permitindo o domínio
- Adicione `https://nfcom.holeshot.com.br` em `CORS_ORIGINS` no `backend/.env`
- Reinicie o container: `docker-compose restart backend`

---

## 📊 Monitoramento

### Ver logs em tempo real
```bash
# Apache
sudo tail -f /var/log/apache2/nfcom-access.log

# Containers Docker
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Verificar status
```bash
# Apache
sudo systemctl status apache2

# Docker
docker-compose ps
```

---

## 🔄 Após Mudanças

### Alteração na configuração Apache
```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}$1 [R=301,L]
    
    # Logs
    ErrorLog ${APACHE_LOG_DIR}/nfcom-error.log
    CustomLog ${APACHE_LOG_DIR}/nfcom-access.log combined
</VirtualHost>

# ========================================================================
# NFCom - HTTPS (Produção)
# ========================================================================
<VirtualHost *:443>
    ServerName nfcom.holeshot.com.br
    ServerAdmin admin@holeshot.com.br
    
    # SSL/TLS Configuration
    SSLEngine on
    SSLCertificateFile /caminho/para/certificado.crt
    SSLCertificateKeyFile /caminho/para/chave-privada.key
    SSLCertificateChainFile /caminho/para/cadeia.crt  # Se aplicável
    
    # Protocolos e Ciphers Seguros
    SSLProtocol all -SSLv2 -SSLv3 -TLSv1 -TLSv1.1
    SSLCipherSuite HIGH:!aNULL:!MD5:!3DES
    SSLHonorCipherOrder on
    
    # ====================================================================
    # Proxy para Frontend (React) - Porta 3013
    # ====================================================================
    ProxyPreserveHost On
    ProxyTimeout 300
    
    # ====================================================================
    # Proxy para Backend API (FastAPI) - Porta 8013
    # ====================================================================
    # Todas as requisições para /api/* são redirecionadas para o backend
    # A regra mais específica (/api) deve vir ANTES da regra mais genérica (/).
    ProxyPass /api http://localhost:8013
    ProxyPassReverse /api http://localhost:8013

    # ====================================================================
    # Proxy para Frontend (React) - Porta 3013
    # ====================================================================
    # A regra genérica (/) deve vir DEPOIS da regra da API.
    ProxyPass / http://localhost:3013/
    ProxyPassReverse / http://localhost:3013/
    
    # ====================================================================
    # WebSocket Support (se necessário para recursos em tempo real)
    # ====================================================================
    # Descomente se usar WebSockets
    # ProxyPass /ws ws://localhost:8013/ws
    # ProxyPassReverse /ws ws://localhost:8013/ws
    
    # ====================================================================
    # Headers de Segurança
    # ====================================================================
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-XSS-Protection "1; mode=block"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
    Header always set Strict-Transport-Security "max-age=31536000; includeSubDomains"
    
    # Informar ao backend sobre o protocolo original
    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Port "443"
    
    # Forçar reescrita de Location headers para HTTPS e adicionar /api prefixo.
    # Isso é crucial porque um backend ciente do proxy pode gerar URLs externas
    # que ProxyPassReverse não reescreveria, e precisamos garantir o prefixo /api.
    # Esta regra corrige o redirecionamento 307, adicionando o /api que falta.
    Header edit Location ^http://nfcom\.holeshot\.com\.br/empresas/(.*)$ https://nfcom.holeshot.com.br/api/empresas/$1
    
    # ====================================================================
    # Logs
    # ====================================================================
    ErrorLog ${APACHE_LOG_DIR}/nfcom-ssl-error.log
    CustomLog ${APACHE_LOG_DIR}/nfcom-ssl-access.log combined
    
    # ====================================================================
    # Limites e Timeouts (ajuste conforme necessário)
    # ====================================================================
    # Para upload de arquivos grandes (certificados, XMLs, etc.)
    LimitRequestBody 52428800  # 50MB
    
</VirtualHost>
```

---

## 🚀 Ativação do Site

```bash
# Copiar arquivo de configuração
sudo nano /etc/apache2/sites-available/nfcom.conf

# Colar a configuração acima (ajustando caminhos dos certificados SSL)

# Ativar o site
sudo a2ensite nfcom.conf

# Testar configuração
sudo apache2ctl configtest

# Se "Syntax OK", recarregar Apache
sudo systemctl reload apache2
```

---

## 🔐 Certificado SSL

### Opção 1: Let's Encrypt (Gratuito e Recomendado)

```bash
# Instalar Certbot
sudo apt install certbot python3-certbot-apache

# Obter certificado
sudo certbot --apache -d nfcom.holeshot.com.br

# Certbot configurará automaticamente o Apache
# E criará renovação automática
```

### Opção 2: Certificado Próprio

Se já possui certificado:
1. Copie os arquivos para um local seguro (ex: `/etc/ssl/nfcom/`)
2. Ajuste os caminhos no VirtualHost:
   ```apache
   SSLCertificateFile /etc/ssl/nfcom/certificado.crt
   SSLCertificateKeyFile /etc/ssl/nfcom/chave-privada.key
   SSLCertificateChainFile /etc/ssl/nfcom/cadeia.crt
   ```

---

## 🧪 Testando a Configuração

### 1. Verificar containers Docker estão rodando
```bash
docker-compose ps
# Deve mostrar: backend (8013), frontend (3013), db (3313)
```

### 2. Testar acesso local às portas
```bash
# Backend
curl http://localhost:8013/docs
# Deve retornar a documentação da API

# Frontend
curl http://localhost:3013
# Deve retornar HTML do React
```

### 3. Testar proxy reverso
```bash
# Frontend via domínio
curl https://nfcom.holeshot.com.br

# API via domínio
curl https://nfcom.holeshot.com.br/api/docs
```

### 4. Testar no navegador
- Acesse: `https://nfcom.holeshot.com.br`
- Faça login
- Verifique console do navegador (F12) para erros de conexão

---

## 🔍 Troubleshooting

### 502 Bad Gateway
**Causa**: Apache não consegue conectar aos containers
```bash
# Verificar containers
docker-compose ps

# Verificar logs do Apache
sudo tail -f /var/log/apache2/nfcom-ssl-error.log

# Verificar conectividade
curl http://localhost:8013
curl http://localhost:3013
```

### 503 Service Unavailable
**Causa**: Containers não estão respondendo
```bash
# Ver logs dos containers
docker-compose logs backend
docker-compose logs frontend
```

### Erro de SSL/Certificado
```bash
# Verificar certificado
sudo openssl x509 -in /caminho/certificado.crt -text -noout

# Verificar validade
sudo certbot certificates
```

### Erro CORS
**Causa**: Backend não está permitindo o domínio
- Adicione `https://nfcom.holeshot.com.br` em `CORS_ORIGINS` no `backend/.env`
- Reinicie o container: `docker-compose restart backend`

---

## 📊 Monitoramento

### Ver logs em tempo real
```bash
# Apache
sudo tail -f /var/log/apache2/nfcom-ssl-access.log

# Containers Docker
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Verificar status
```bash
# Apache
sudo systemctl status apache2

# Docker
docker-compose ps
```

---

## 🔄 Após Mudanças

### Alteração na configuração Apache
```bash
sudo apache2ctl configtest
sudo systemctl reload apache2
```

### Atualização do código (redeployment)
```bash
cd /caminho/para/nfcom
docker-compose down
docker-compose up -d --build
```

---

## 📚 Referências Relacionadas

- `CONFIGURACAO_AMBIENTES.md` - Configuração geral de ambientes
- `docker-compose.yml` - Definição dos containers
- `backend/.env` - Variáveis de ambiente do backend (CORS)

---

**Nota de Segurança**: Sempre use HTTPS em produção e mantenha os certificados atualizados!
