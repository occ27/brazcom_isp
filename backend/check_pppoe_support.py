#!/usr/bin/env python3
"""
Verificar suporte a PPPoE server no RouterOS 6.49.19
"""

import librouteros

def check_pppoe_support():
    """Verifica suporte a PPPoE server"""
    api = librouteros.connect(host='192.168.18.101', username='admin', password='gruta765')

    print('🔍 Verificando versão completa do RouterOS...')
    system_info = list(api.path('system/resource').select())[0]
    print(f'Versão: {system_info.get("version")}')
    print(f'Plataforma: {system_info.get("platform")}')
    print(f'Arquitetura: {system_info.get("architecture-name")}')

    print('\n🔍 Verificando pacotes PPP...')
    packages = list(api.path('system/package').select())
    pppoe_related = [pkg for pkg in packages if 'ppp' in pkg.get('name', '').lower()]
    print(f'Pacotes PPP relacionados: {len(pppoe_related)}')
    for pkg in pppoe_related:
        print(f'  - {pkg.get("name")}: {pkg.get("version")}')

    print('\n🔍 Testando comandos PPPoE server possíveis...')

    # Comandos que poderiam existir no RouterOS 6.x
    commands_to_try = [
        'interface/pppoe-server',
        'ppp/pppoe-server',
        'interface/pppoe',
        'ppp/pppoe'
    ]

    for cmd in commands_to_try:
        try:
            items = list(api.path(cmd).select())
            print(f'✅ {cmd}: {len(items)} itens encontrados')
            if items and len(items) > 0:
                print(f'   Exemplo: {items[0]}')
        except Exception as e:
            print(f'❌ {cmd}: {str(e)[:60]}...')

    print('\n🔍 Verificando se há configuração PPPoE em interfaces...')
    interfaces = list(api.path('interface').select())
    pppoe_interfaces = [iface for iface in interfaces if 'pppoe' in iface.get('name', '').lower() or 'pppoe' in iface.get('type', '').lower()]
    print(f'Interfaces PPPoE encontradas: {len(pppoe_interfaces)}')
    for iface in pppoe_interfaces:
        print(f'  - {iface}')

    api.close()

if __name__ == "__main__":
    check_pppoe_support()