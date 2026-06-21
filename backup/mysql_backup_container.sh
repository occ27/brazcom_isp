#!/bin/bash

# Script de backup para execu????o DENTRO do container Docker
# Configura????es do backup
BACKUP_DIR="/backups"
DB_HOST="${DB_HOST:-db}"  # Nome do servi??o no docker-compose
DB_NAME="${DB_NAME:-brazcom}"
DB_USER="${DB_USER:-root}"
DB_PASSWORD="${DB_PASSWORD:-Altavista740}"
DATE=$(date +%Y%m%d)
TIME=$(date +%H%M%S)
# Usar somente a data no nome do arquivo para evitar criar muitos arquivos por dia.
BACKUP_FILE="${BACKUP_DIR}/brazcom_backup_${DATE}.sql"
LOG_FILE="${BACKUP_DIR}/backup.log"

# Criar diret??rio de backup se n??o existir
mkdir -p "${BACKUP_DIR}"

# Fun????o para log
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "${LOG_FILE}"
}

log "Iniciando backup do banco de dados ${DB_NAME} - ${TIME}"

# Verificar conectividade com o banco
if ! mysqladmin -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASSWORD}" ping >/dev/null 2>&1; then
    log "ERRO: N??o foi poss??vel conectar ao banco de dados em ${DB_HOST}"
    exit 1
fi

log "Conectividade com banco verificada"

# Realizar o backup diretamente (estamos dentro de um container MySQL)
if mysqldump -h"${DB_HOST}" -u"${DB_USER}" -p"${DB_PASSWORD}" --single-transaction --routines --triggers "${DB_NAME}" > "${BACKUP_FILE}"; then
    log "Backup criado com sucesso: ${BACKUP_FILE}"
    
    # Verificar se o arquivo foi criado e n??o est?? vazio
    if [ -s "${BACKUP_FILE}" ]; then
        # Comprimir o backup (for??a sobrescrita caso exista e usa maior compress??o)
        if gzip -9 -f "${BACKUP_FILE}"; then
            log "Backup comprimido: ${BACKUP_FILE}.gz"
            BACKUP_FILE="${BACKUP_FILE}.gz"
        else
            log "AVISO: Falha ao comprimir o backup"
        fi
        
        # Verificar tamanho do arquivo
        SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
        log "Tamanho do backup: ${SIZE}"
        
        # Remover backups antigos (manter apenas os ??ltimos 7 dias)
        find "${BACKUP_DIR}" -name "brazcom_backup_*.sql.gz" -mtime +7 -delete 2>/dev/null
        REMOVED=$(find "${BACKUP_DIR}" -name "brazcom_backup_*.sql.gz" -mtime +7 2>/dev/null | wc -l)
        if [ "$REMOVED" -gt 0 ]; then
            log "Backups antigos removidos (> 7 dias): $REMOVED arquivos"
        fi
        
        # Upload para o Google Drive via Rclone
        log "Enviando backup para o Google Drive..."
        if rclone copy "${BACKUP_FILE}" "gdrive:backups_brazcom"; then
            log "Upload para Google Drive conclu??do com sucesso"
        else
            log "ERRO: Falha ao enviar para o Google Drive"
        fi
        
        log "Backup conclu??do com sucesso"
        exit 0
    else
        log "ERRO: Arquivo de backup criado mas est?? vazio"
        rm -f "${BACKUP_FILE}"
        exit 1
    fi
else
    log "ERRO: Falha ao criar backup"
    exit 1
fi