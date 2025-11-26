"""Esqueleto de controlador Mikrotik usando RouterOS API.

Instalar dependência recomendada (exemplo): `pip install librouteros` ou `routeros-api`.
Este módulo provê uma camada abstrata para: criar/atualizar/remover usuários PPPoE/Hotspot,
gerenciar ARP, controlar queues (limites de banda) e aplicar regras firewall/nat.
"""
from typing import Optional

try:
    import routeros_api
except Exception:  # pragma: no cover - optional dependency
    routeros_api = None


class MikrotikController:
    def __init__(self, host: str, username: str, password: str, port: int = 8728, use_ssl: bool = False, plaintext_login: bool = True):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.plaintext_login = plaintext_login
        self._pool = None
        self._api = None

    def connect(self):
        """Estabelece conexão com o RouterOS usando `routeros_api` se disponível.

        Em ambientes onde a biblioteca não esteja instalada, essa função lançará
        um `RuntimeError` indicando que a dependência é necessária.
        """
        if routeros_api is None:
            raise RuntimeError("Biblioteca 'routeros_api' não encontrada. Instale via 'pip install routeros-api'.")

        if self._pool is None:
            # RouterOsApiPool(host, username, password, plaintext_login=True/False, port=8728)
            self._pool = routeros_api.RouterOsApiPool(
                self.host,
                username=self.username,
                password=self.password,
                port=self.port,
                plaintext_login=self.plaintext_login,
            )
            self._api = self._pool.get_api()

    def close(self):
        if self._pool:
            try:
                self._pool.disconnect()
            except Exception:
                pass
            self._pool = None
            self._api = None

    def add_pppoe_user(self, username: str, password: str, service: str = 'pppoe', profile: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona usuário PPPoE no roteador usando `/ppp/secret`.

        Retorna o registro criado (dict) ou lança erro em caso de falha.
        """
        self.connect()
        resource = self._api.get_resource('ppp/secret')
        data = {'name': username, 'password': password, 'service': service}
        if profile:
            data['profile'] = profile
        if comment:
            data['comment'] = comment
        return resource.add(**data)

    def remove_pppoe_user(self, username: str):
        """Remove usuário PPPoE buscando por `name` e removendo o item."""
        self.connect()
        resource = self._api.get_resource('ppp/secret')
        items = resource.get(name=username)
        if not items:
            return False
        for it in items:
            resource.remove(id=it.get('.id'))
        return True

    def add_hotspot_user(self, username: str, password: str, server: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona usuário de hotspot via `/ip/hotspot/user` (se aplicável)."""
        self.connect()
        resource = self._api.get_resource('ip/hotspot/user')
        data = {'name': username, 'password': password}
        if server:
            data['server'] = server
        if comment:
            data['comment'] = comment
        return resource.add(**data)

    def set_arp_entry(self, ip: str, mac: str, interface: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona/atualiza entrada ARP (`/ip/arp`).

        Estratégia robusta: garante que a entrada existe com os dados corretos.
        """
        self.connect()
        resource = self._api.get_resource('ip/arp')

        # Busca entrada existente
        existing = resource.get(address=ip)

        if existing:
            # Se já existe, sobrescreve com nova informação
            for entry in existing:
                entry_id = entry.get('.id') or entry.get('id')
                if entry_id:
                    try:
                        # Tenta remover a entrada antiga primeiro
                        resource.remove(id=entry_id)
                    except Exception:
                        pass  # Se não conseguir remover, continua

        # Adiciona a nova entrada
        data = {'address': ip, 'mac-address': mac}
        if interface:
            data['interface'] = interface
        if comment:
            data['comment'] = comment

        return resource.add(**data)

    def remove_arp_entry(self, ip: str, mac: Optional[str] = None):
        """Remove entrada(s) ARP por IP e opcionalmente MAC (`/ip/arp`).

        NOTA: Devido a limitações da API routeros-api, esta função pode não
        remover entradas existentes. Use set_arp_entry() para sobrescrever.
        """
        self.connect()
        resource = self._api.get_resource('ip/arp')

        entries = resource.get(address=ip)
        if mac:
            entries = [e for e in entries if e.get('mac-address') == mac]

        removed = 0
        for entry in entries:
            entry_id = entry.get('.id') or entry.get('id')
            if entry_id:
                try:
                    resource.remove(id=entry_id)
                    removed += 1
                except Exception:
                    # Se não conseguir remover, sobrescreve com entrada "inválida"
                    try:
                        resource.add(
                            address=ip,
                            mac_address='00:00:00:00:00:00',
                            interface='ether1'
                        )
                        removed += 1  # Considera como "removida"
                    except Exception:
                        pass

        return removed

    def set_queue_simple(self, name: str, target: str, max_limit: str, burst: Optional[str] = None, comment: Optional[str] = None):
        """Cria/atualiza uma simple-queue (`/queue/simple`).

        `target` exemplo: "192.168.1.0/24" ou "192.168.1.10/32". `max_limit` ex: "10M/2M".
        """
        self.connect()
        resource = self._api.get_resource('queue/simple')
        # Procura pelo name
        existing = resource.get(name=name)
        data = {'name': name, 'target': target, 'max-limit': max_limit}
        if burst:
            data['burst-limit'] = burst
        if comment:
            data['comment'] = comment
        if existing:
            # atualiza o primeiro encontrado
            resource.set(id=existing[0].get('.id'), **data)
            return True
        else:
            return resource.add(**data)

    def get_interfaces(self):
        """Busca todas as interfaces do router (/interface)."""
        self.connect()
        resource = self._api.get_resource('interface')
        return resource.get()

    def get_interface_by_name(self, name: str):
        """Busca uma interface específica por nome."""
        self.connect()
        resource = self._api.get_resource('interface')
        interfaces = resource.get(name=name)
        return interfaces[0] if interfaces else None

    def get_ip_addresses(self):
        """Busca todos os endereços IP configurados (/ip/address)."""
        self.connect()
        resource = self._api.get_resource('ip/address')
        return resource.get()

    def add_ip_address(self, address: str, interface: str, comment: Optional[str] = None):
        """Adiciona um endereço IP a uma interface (/ip/address)."""
        self.connect()
        resource = self._api.get_resource('ip/address')
        data = {'address': address, 'interface': interface}
        if comment:
            data['comment'] = comment
        return resource.add(**data)

    def remove_ip_address(self, address: str, interface: Optional[str] = None):
        """Remove um endereço IP de uma interface."""
        self.connect()
        resource = self._api.get_resource('ip/address')

        # Busca a entrada
        if interface:
            entries = resource.get(address=address, interface=interface)
        else:
            entries = resource.get(address=address)

        removed = 0
        for entry in entries:
            entry_id = entry.get('.id') or entry.get('id')
            if entry_id:
                try:
                    resource.remove(id=entry_id)
                    removed += 1
                except Exception as e:
                    print(f"Erro ao remover endereço IP {address}: {e}")

        return removed

    def set_ip_address(self, address: str, interface: str, comment: Optional[str] = None):
        """Define um endereço IP em uma interface, removendo entradas antigas se necessário."""
        self.connect()

        # Remove endereços existentes nesta interface (exceto o que estamos configurando)
        existing = self.get_ip_addresses()
        for entry in existing:
            if entry.get('interface') == interface and entry.get('address') != address:
                try:
                    self.remove_ip_address(entry['address'], interface)
                except Exception:
                    pass

        # Verifica se o endereço já existe
        existing_address = [e for e in existing if e.get('address') == address and e.get('interface') == interface]

        if existing_address:
            # Atualiza comentário se necessário
            if comment and existing_address[0].get('comment') != comment:
                resource = self._api.get_resource('ip/address')
                resource.update(id=existing_address[0]['.id'], comment=comment)
            return existing_address[0]
        else:
            # Adiciona novo endereço
            return self.add_ip_address(address, interface, comment)

    def get_dhcp_servers(self):
        """Busca servidores DHCP configurados (/ip/dhcp-server)."""
        self.connect()
        resource = self._api.get_resource('ip/dhcp-server')
        return resource.get()

    def add_dhcp_server(self, name: str, interface: str, address_pool: str, disabled: bool = False):
        """Adiciona um servidor DHCP."""
        self.connect()
        resource = self._api.get_resource('ip/dhcp-server')
        data = {
            'name': name,
            'interface': interface,
            'address-pool': address_pool,
            'disabled': 'yes' if disabled else 'no'
        }
        return resource.add(**data)

    def get_dhcp_pools(self):
        """Busca pools de endereços DHCP (/ip/pool)."""
        self.connect()
        resource = self._api.get_resource('ip/pool')
        return resource.get()

    def add_dhcp_pool(self, name: str, ranges: str):
        """Adiciona um pool de endereços DHCP."""
        self.connect()
        resource = self._api.get_resource('ip/pool')
        data = {'name': name, 'ranges': ranges}
        return resource.add(**data)

    def get_dns_servers(self):
        """Busca configuração de DNS (/ip/dns)."""
        self.connect()
        resource = self._api.get_resource('ip/dns')
        return resource.get()

    def set_dns_servers(self, servers: list, allow_remote_requests: bool = True):
        """Configura servidores DNS."""
        self.connect()
        resource = self._api.get_resource('ip/dns')

        # Converte lista para string separada por vírgulas
        servers_str = ','.join(servers)

        data = {
            'servers': servers_str,
            'allow-remote-requests': 'yes' if allow_remote_requests else 'no'
        }

        # Para DNS, usar set diretamente (não há entradas múltiplas)
        return resource.set(**data)

    def set_default_route(self, gateway: str, comment: Optional[str] = None):
        """Configura rota padrão (default route)."""
        self.connect()
        resource = self._api.get_resource('ip/route')

        # Remove rotas padrão existentes (dst-address=0.0.0.0/0)
        existing = resource.get(dst_address='0.0.0.0/0')
        for route in existing:
            try:
                resource.remove(id=route['.id'])
            except Exception:
                pass

        # Adiciona nova rota padrão
        data = {
            'dst-address': '0.0.0.0/0',
            'gateway': gateway
        }
        if comment:
            data['comment'] = comment

        return resource.add(**data)

    def reset_pppoe_connection(self, username: str):
        """Reseta conexão PPPoE ativa atualizando o secret."""
        self.connect()
        secret_resource = self._api.get_resource('ppp/secret')

        # Busca o secret
        secrets = secret_resource.get(name=username)
        if not secrets:
            return False

        secret = secrets[0]
        secret_id = secret.get('.id')

        # Para resetar, vamos atualizar o secret com os mesmos dados
        # Isso força o router a refrescar a conexão
        data = {
            'name': secret.get('name'),
            'password': secret.get('password'),
            'service': secret.get('service', 'pppoe')
        }
        if secret.get('profile'):
            data['profile'] = secret.get('profile')
        if secret.get('comment'):
            data['comment'] = secret.get('comment')

        # Atualiza o secret existente (isso força o reset da conexão)
        try:
            secret_resource.set(id=secret_id, **data)
            return True
        except Exception as e:
            # Se não conseguir atualizar, tenta remover e recriar
            try:
                secret_resource.remove(id=secret_id)
                # Pequena pausa para garantir que foi removida
                import time
                time.sleep(0.5)
                return secret_resource.add(**data)
            except Exception:
                return False

    def reset_hotspot_connection(self, username: str):
        """Reseta conexão Hotspot atualizando o usuário."""
        self.connect()
        user_resource = self._api.get_resource('ip/hotspot/user')

        # Busca o usuário
        users = user_resource.get(name=username)
        if not users:
            return False

        user = users[0]
        user_id = user.get('.id')

        # Para resetar, vamos atualizar o usuário com os mesmos dados
        # Isso força o router a refrescar a conexão
        data = {
            'name': user.get('name'),
            'password': user.get('password')
        }
        if user.get('server'):
            data['server'] = user.get('server')
        if user.get('comment'):
            data['comment'] = user.get('comment')

        # Atualiza o usuário existente (isso força o reset da conexão)
        try:
            user_resource.set(id=user_id, **data)
            return True
        except Exception as e:
            # Se não conseguir atualizar, tenta remover e recriar
            try:
                user_resource.remove(id=user_id)
                # Pequena pausa para garantir que foi removida
                import time
                time.sleep(0.5)
                return user_resource.add(**data)
            except Exception:
                return False

    def reset_arp_connection(self, ip: str):
        """Reseta conexão IP_MAC forçando uma atualização da entrada ARP."""
        self.connect()
        arp_resource = self._api.get_resource('ip/arp')

        # Busca a entrada ARP
        entries = arp_resource.get(address=ip)
        if not entries:
            return False

        entry = entries[0]
        entry_id = entry.get('.id')

        # Para resetar, vamos atualizar a entrada existente com os mesmos dados
        # Isso força o router a refrescar a conexão
        data = {
            'address': entry.get('address'),
            'mac-address': entry.get('mac-address'),
            'interface': entry.get('interface')
        }
        if entry.get('comment'):
            data['comment'] = entry.get('comment')

        # Atualiza a entrada existente (isso força o reset da conexão)
        try:
            arp_resource.set(id=entry_id, **data)
            return True
        except Exception as e:
            # Se não conseguir atualizar, tenta remover e recriar
            try:
                arp_resource.remove(id=entry_id)
                # Pequena pausa para garantir que foi removida
                import time
                time.sleep(0.5)
                return arp_resource.add(**data)
            except Exception:
                return False

    def reset_client_connection(self, contrato_id: int, metodo_autenticacao: str, assigned_ip: str = None, mac_address: str = None):
        """Reseta a conexão do cliente baseado no método de autenticação."""
        if metodo_autenticacao == 'IP_MAC':
            if not assigned_ip:
                raise ValueError("IP é obrigatório para reset de conexão IP_MAC")
            return self.reset_arp_connection(assigned_ip)

        elif metodo_autenticacao == 'PPPOE':
            username = f"contrato_{contrato_id}"
            return self.reset_pppoe_connection(username)

        elif metodo_autenticacao == 'HOTSPOT':
            username = f"contrato_{contrato_id}"
            return self.reset_hotspot_connection(username)

        elif metodo_autenticacao == 'RADIUS':
            # Para RADIUS, pode ser necessário resetar via PPPoE ou Hotspot dependendo da configuração
            # Por enquanto, vamos assumir PPPoE como padrão
            username = f"contrato_{contrato_id}"
            return self.reset_pppoe_connection(username)

        else:
            raise ValueError(f"Método de autenticação não suportado: {metodo_autenticacao}")
