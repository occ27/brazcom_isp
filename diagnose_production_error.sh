#!/bin/bash
# Script para diagnosticar o erro 500 no endpoint servicos-contratados
# Execute este script no servidor de produção

echo "=== DIAGNÓSTICO DO ERRO 500 - NFCom Produção ==="
echo ""

echo "1. Verificando logs do backend (últimas 20 linhas):"
docker logs nfcom_backend --tail 20
echo ""

echo "2. Verificando se o container está rodando:"
docker ps | grep nfcom_backend
echo ""

echo "3. Testando conectividade com o banco dentro do container:"
docker exec nfcom_backend python -c "
from app.core.database import get_db
try:
    db = next(get_db())
    print('✓ Conexão com banco OK')
    db.close()
except Exception as e:
    print('✗ Erro na conexão com banco:', e)
"
echo ""

echo "4. Executando diagnóstico detalhado da função problemática:"
docker cp diagnose_error.py nfcom_backend:/app/diagnose_error.py
docker exec nfcom_backend python /app/diagnose_error.py
echo ""

echo "5. Verificando configurações do ambiente:"
docker exec nfcom_backend python -c "
from app.core.config import settings
print('DATABASE_URL:', settings.DATABASE_URL)
print('UPLOAD_DIR:', settings.UPLOAD_DIR)
print('CERTIFICATES_DIR:', settings.CERTIFICATES_DIR)
"
echo ""

echo "6. Verificando versões dos pacotes:"
docker exec nfcom_backend pip list | grep -E "(sqlalchemy|pymysql|fastapi)"
echo ""

echo "7. Testando uma requisição HTTP direta para o endpoint problemático:"
# Assumindo que você tem um token válido, substitua YOUR_TOKEN_HERE
curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer YOUR_TOKEN_HERE" \
     "http://localhost:8000/api/servicos-contratados/cliente/2979?empresa_id=25"
echo " - Código HTTP da requisição direta"
echo ""

echo "=== FIM DO DIAGNÓSTICO ==="