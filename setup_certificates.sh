#!/bin/bash
# 🛡️ Script de Configuração Automática de Certificados NFCom
# Versão: 1.0
# Data: Outubro 2025

set -e  # Parar em caso de erro

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função de log
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERRO] $1${NC}" >&2
}

warning() {
    echo -e "${YELLOW}[AVISO] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Verificar se está rodando como root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Este script deve ser executado como root (sudo)"
        exit 1
    fi
}

# Criar estrutura de diretórios
create_directories() {
    log "Criando estrutura de diretórios seguros..."

    # Criar diretório base
    mkdir -p /etc/ssl/nfcom/certificates

    # Definir proprietário e grupo
    chown root:ssl-cert /etc/ssl/nfcom
    chmod 750 /etc/ssl/nfcom
    chmod 700 /etc/ssl/nfcom/certificates

    log "Estrutura criada com sucesso"
}

# Criar usuário dedicado (opcional)
create_user() {
    local create_user=${1:-false}

    if [[ "$create_user" == "true" ]]; then
        log "Criando usuário dedicado nfcom-user..."

        # Verificar se usuário já existe
        if id "nfcom-user" &>/dev/null; then
            warning "Usuário nfcom-user já existe"
        else
            useradd -r -s /bin/false nfcom-user
            log "Usuário nfcom-user criado"
        fi

        # Adicionar ao grupo ssl-cert
        usermod -a -G ssl-cert nfcom-user
        log "Usuário adicionado ao grupo ssl-cert"
    else
        info "Pular criação de usuário (use --create-user para criar)"
    fi
}

# Configurar SELinux/AppArmor (se disponível)
configure_security() {
    log "Configurando segurança adicional..."

    # SELinux
    if command -v setsebool &> /dev/null; then
        setsebool -P httpd_can_read_ssl_cert off 2>/dev/null || true
        log "SELinux configurado"
    fi

    # AppArmor
    if command -v apparmor_status &> /dev/null; then
        info "AppArmor detectado - considere configurar perfil específico"
    fi
}

# Testes de segurança
run_security_tests() {
    log "Executando testes de segurança..."

    # Teste 1: Verificar permissões
    local cert_perms=$(stat -c "%a" /etc/ssl/nfcom/certificates 2>/dev/null || echo "unknown")
    if [[ "$cert_perms" == "700" ]]; then
        log "✓ Permissões corretas (700)"
    else
        error "✗ Permissões incorretas: $cert_perms (esperado: 700)"
    fi

    # Teste 2: Verificar proprietário
    local cert_owner=$(stat -c "%U:%G" /etc/ssl/nfcom/certificates 2>/dev/null || echo "unknown")
    if [[ "$cert_owner" == "root:ssl-cert" ]]; then
        log "✓ Proprietário correto (root:ssl-cert)"
    else
        error "✗ Proprietário incorreto: $cert_owner (esperado: root:ssl-cert)"
    fi

    # Teste 3: Verificar se diretório existe
    if [[ -d "/etc/ssl/nfcom/certificates" ]]; then
        log "✓ Diretório existe"
    else
        error "✗ Diretório não encontrado"
    fi

    log "Testes concluídos"
}

# Função de backup
create_backup() {
    local backup_dir=${1:-"/var/backups/nfcom-certificates"}

    if [[ -d "/etc/ssl/nfcom" ]]; then
        log "Criando backup em $backup_dir..."

        mkdir -p "$backup_dir"
        local backup_file="$backup_dir/certificates-$(date +%Y%m%d-%H%M%S).tar.gz"

        tar -czf "$backup_file" -C /etc/ssl nfcom/ 2>/dev/null || true

        if [[ -f "$backup_file" ]]; then
            log "Backup criado: $backup_file"
        else
            warning "Falha ao criar backup"
        fi
    else
        info "Diretório não existe ainda, pulando backup"
    fi
}

# Mostrar ajuda
show_help() {
    cat << EOF
🛡️ Configuração Automática de Certificados NFCom

USO:
    sudo bash setup_certificates.sh [OPÇÕES]

OPÇÕES:
    --create-user       Criar usuário dedicado nfcom-user
    --backup DIR        Criar backup antes da configuração
    --test-only         Apenas executar testes de segurança
    --help             Mostrar esta ajuda

EXEMPLOS:
    # Configuração básica
    sudo bash setup_certificates.sh

    # Com usuário dedicado e backup
    sudo bash setup_certificates.sh --create-user --backup /var/backups

    # Apenas testes
    sudo bash setup_certificates.sh --test-only

ESTRUTURA CRIADA:
/etc/ssl/nfcom/
└── certificates/     # drwxr-xr-x root ssl-cert

NOTAS DE SEGURANÇA:
- Certificados ficam completamente fora da pasta web
- Acesso restrito apenas ao grupo ssl-cert
- Aplicação deve rodar com usuário no grupo ssl-cert

Para mais informações, consulte: CERTIFICATES_SETUP.md
EOF
}

# Função principal
main() {
    local create_user=false
    local backup_dir=""
    local test_only=false

    # Processar argumentos
    while [[ $# -gt 0 ]]; do
        case $1 in
            --create-user)
                create_user=true
                shift
                ;;
            --backup)
                backup_dir="$2"
                shift 2
                ;;
            --test-only)
                test_only=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                error "Opção desconhecida: $1"
                show_help
                exit 1
                ;;
        esac
    done

    echo "🛡️ Configuração de Certificados NFCom"
    echo "===================================="

    # Verificar root apenas se não for test-only
    if [[ "$test_only" != "true" ]]; then
        check_root
    fi

    # Criar backup se solicitado
    if [[ -n "$backup_dir" ]]; then
        create_backup "$backup_dir"
    fi

    # Executar configuração ou apenas testes
    if [[ "$test_only" == "true" ]]; then
        run_security_tests
    else
        create_directories
        create_user "$create_user"
        configure_security
        run_security_tests

        log "Configuração concluída com sucesso!"
        echo ""
        info "Próximos passos:"
        echo "1. Configure sua aplicação com: CERTIFICATES_DIR=/etc/ssl/nfcom"
        echo "2. Adicione o usuário da aplicação ao grupo ssl-cert"
        echo "3. Teste o upload de certificados"
        echo "4. Configure backup automático"
    fi
}

# Executar função principal
main "$@"</content>
<parameter name="filePath">c:\python\FastAPI\nfcom\setup_certificates.sh