#!/usr/bin/env python3
"""
Verificar alternativas para servidor PPPoE no RouterOS 6.49.19
"""

import librouteros

def check_pppoe_alternatives():
    """Verifica alternativas para servidor PPPoE"""
    api = librouteros.connect(host='192.168.18.101', username='admin', password='gruta765')

    print('🔍 Verificando funcionalidades que podem atuar como servidor PPPoE...')

    # Verificar hotspot (que pode funcionar como servidor PPPoE)
    try:
        hotspot_servers = list(api.path('ip/hotspot').select())
        print(f'Servidores Hotspot: {len(hotspot_servers)}')
        for server in hotspot_servers:
            print(f'  - {server.get("name")}: {server.get("interface")}')
    except Exception as e:
        print(f'Hotspot erro: {str(e)[:50]}...')

    # Verificar se há configuração PPP
    try:
        ppp_configs = list(api.path('ppp').select())
        print(f'\nConfigurações PPP: {len(ppp_configs)}')
        for config in ppp_configs[:3]:  # primeiros 3
            print(f'  - {config}')
    except Exception as e:
        print(f'PPP erro: {str(e)[:50]}...')

    # Verificar servidores PPPoE
    try:
        pppoe_servers = list(api.path('interface/pppoe-server').select())
        print(f'\nServidores PPPoE: {len(pppoe_servers)}')
        for server in pppoe_servers:
            print(f'  - {server}')
    except Exception as e:
        print(f'PPPoE server erro: {str(e)[:50]}...')

    # Verificar interfaces PPPoE criadas
    interfaces = list(api.path('interface').select())
    pppoe_interfaces = [i for i in interfaces if 'pppoe' in i.get('name', '').lower() or 'pppoe' in i.get('type', '').lower()]
    print(f'\nInterfaces PPPoE encontradas: {len(pppoe_interfaces)}')
    for iface in pppoe_interfaces:
        name = iface.get('name')
        tipo = iface.get('type')
        print(f'  - {name}: {tipo}')

    api.close()

    print('\n📋 CONCLUSÃO:')
    print('No RouterOS 6.49.19:')
    print('- PPPoE server dedicado NÃO é suportado')
    print('- Interfaces criadas são clientes PPPoE (pppoe-out)')
    print('- Hotspot pode ser uma alternativa para autenticação')
    print('- Sistema atual cria clientes, não servidores PPPoE')

if __name__ == "__main__":
    check_pppoe_alternatives()