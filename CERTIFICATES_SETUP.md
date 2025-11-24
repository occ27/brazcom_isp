# 🛡️ Configuração de Certificados Digitais - NFCom
## Guia de Produção para Linux Debian

### 📋 Pré-requisitos
- Servidor Linux Debian/Ubuntu
- Acesso root ou sudo
- Aplicação NFCom instalada

---

## 🔐 1. Criar Diretório Seguro para Certificados

### Comando Principal
```bash
# Criar diretório base seguro
sudo mkdir -p /etc/ssl/nfcom/certificates

# Definir proprietário e grupo
sudo chown root:ssl-cert /etc/ssl/nfcom

# Definir permissões restritas
sudo chmod 750 /etc/ssl/nfcom
sudo chmod 700 /etc/ssl/nfcom/certificates
```

### Verificação
```bash
# Verificar estrutura criada
ls -la /etc/ssl/nfcom/
# drwxr-x--- 3 root ssl-cert 4096 Oct 22 22:30 .
# drwxr-xr-x 4 root root     4096 Oct 22 22:30 ..
# drwxr-xr-x 2 root ssl-cert 4096 Oct 22 22:30 certificates
```

---

## 👤 2. Configurar Usuário da Aplicação

### Criar Usuário Dedicado (Recomendado)
```bash
# Criar usuário do sistema para a aplicação
sudo useradd -r -s /bin/false nfcom-user

# Adicionar ao grupo ssl-cert
sudo usermod -a -G ssl-cert nfcom-user
```

### Ou Usar Usuário Existente
```bash
# Se usar www-data (Apache/Nginx)
sudo usermod -a -G ssl-cert www-data

# Se usar usuário específico
sudo usermod -a -G ssl-cert seu_usuario
```

---

## 🔧 3. Configurar Aplicação

### Arquivo de Configuração
Certifique-se que `CERTIFICATES_DIR` está configurado:

```python
# app/core/config.py
CERTIFICATES_DIR: str = "/etc/ssl/nfcom"
```

### Variável de Ambiente (Opcional)
```bash
# .env
CERTIFICATES_DIR=/etc/ssl/nfcom
```

---

## 📁 4. Estrutura Final Esperada

```
/etc/ssl/nfcom/
├── certificates/           # drwxr-xr-x root ssl-cert
│   ├── 1/                 # Empresa ID 1
│   │   └── abc123-cert.p12
│   ├── 2/                 # Empresa ID 2
│   │   └── def456-cert.p12
│   └── 3/                 # Empresa ID 3
│       └── ghi789-cert.p12
```

---

## 🔍 5. Testes de Segurança

### Testar Acesso Direto (Deve Falhar)
```bash
# Tentar acessar via web (deve retornar 404)
curl http://seusite.com/certificates/1/cert.p12
# Resultado esperado: 404 Not Found
```

### Testar Rota Protegida (Deve Requerer Auth)
```bash
# Sem token (deve retornar 401)
curl http://seusite.com/uploads/empresa/1/certificado/download
# Resultado esperado: 401 Unauthorized
```

### Testar Acesso Backend (Deve Funcionar)
```bash
# Verificar se aplicação consegue ler
sudo -u nfcom-user ls -la /etc/ssl/nfcom/certificates/
```

---

## 🔄 6. Backup e Restauração

### Backup Seguro
```bash
# Criar backup criptografado
sudo tar -czf /backup/certificates-$(date +%Y%m%d).tar.gz -C /etc/ssl nfcom/

# Ou usar rsync
sudo rsync -avz /etc/ssl/nfcom/ /backup/nfcom-certificates/
```

### Restauração
```bash
# Restaurar backup
sudo tar -xzf /backup/certificates-20231022.tar.gz -C /etc/ssl/

# Ajustar permissões após restauração
sudo chown -R root:ssl-cert /etc/ssl/nfcom/
sudo chmod 750 /etc/ssl/nfcom/
sudo chmod 700 /etc/ssl/nfcom/certificates/
```

---

## 🚨 7. Troubleshooting

### Erro: "Permission denied"
```bash
# Verificar permissões
ls -la /etc/ssl/nfcom/

# Corrigir se necessário
sudo chown root:ssl-cert /etc/ssl/nfcom
sudo chmod 750 /etc/ssl/nfcom
```

### Erro: "Directory not found"
```bash
# Criar diretório se não existe
sudo mkdir -p /etc/ssl/nfcom/certificates
sudo chown root:ssl-cert /etc/ssl/nfcom
```

### Erro: Aplicação não consegue escrever
```bash
# Adicionar usuário ao grupo ssl-cert
sudo usermod -a -G ssl-cert nfcom-user

# Reiniciar aplicação
sudo systemctl restart nfcom
```

---

## 📊 8. Monitoramento

### Logs de Acesso
```bash
# Monitorar tentativas de acesso
sudo tail -f /var/log/auth.log | grep nfcom

# Ou configurar audit
sudo auditctl -w /etc/ssl/nfcom/ -p rwxa
```

### Verificar Certificados
```bash
# Listar certificados por empresa
find /etc/ssl/nfcom/certificates/ -name "*.p12" -o -name "*.pfx" | sort

# Verificar datas de validade (se possível)
for cert in $(find /etc/ssl/nfcom/certificates/ -name "*.p12"); do
    echo "Certificado: $cert"
    openssl pkcs12 -in "$cert" -info -nokeys 2>/dev/null | grep "valid"
done
```

---

## ⚠️ 9. Avisos de Segurança

### ✅ Práticas Seguras
- ✅ Nunca coloque certificados em `/var/www/`
- ✅ Use permissões restritas (700/750)
- ✅ Faça backup criptografado
- ✅ Monitore tentativas de acesso
- ✅ Renove certificados antes da expiração

### ❌ Evite
- ❌ Permissões 777 ou 755
- ❌ Certificados em pastas web públicas
- ❌ Mesmo usuário para múltiplas aplicações
- ❌ Logs com senhas ou chaves privadas

---

## 📞 Suporte

Em caso de problemas:
1. Verifique logs da aplicação: `/var/log/nfcom/`
2. Teste permissões: `sudo -u nfcom-user touch /etc/ssl/nfcom/test`
3. Verifique configuração: `CERTIFICATES_DIR` no config.py

**Data de criação:** Outubro 2025
**Versão:** 1.0
**Responsável:** Equipe NFCom</content>
<parameter name="filePath">c:\python\FastAPI\nfcom\CERTIFICATES_SETUP.md