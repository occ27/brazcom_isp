#!/bin/bash

# Joga as variáveis de ambiente para um arquivo que o cron possa usar
printenv | grep -E "DATABASE_URL|MYSQL_|RADIUS_" > /etc/environment

echo "Starting cron..."
# Inicia o serviço cron em primeiro plano
cron -f
