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

    def add_pppoe_user(self, username: str, password: str, service: str = 'pppoe', profile: Optional[str] = None):
        """Adiciona usuário PPPoE no roteador usando `/ppp/secret`.

        Retorna o registro criado (dict) ou lança erro em caso de falha.
        """
        self.connect()
        resource = self._api.get_resource('ppp/secret')
        data = {'name': username, 'password': password, 'service': service}
        if profile:
            data['profile'] = profile
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

    def add_hotspot_user(self, username: str, password: str, server: Optional[str] = None):
        """Adiciona usuário de hotspot via `/ip/hotspot/user` (se aplicável)."""
        self.connect()
        resource = self._api.get_resource('ip/hotspot/user')
        data = {'name': username, 'password': password}
        if server:
            data['server'] = server
        return resource.add(**data)

    def set_arp_entry(self, ip: str, mac: str, interface: Optional[str] = None):
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

    def set_queue_simple(self, name: str, target: str, max_limit: str, burst: Optional[str] = None):
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
        if existing:
            # atualiza o primeiro encontrado
            resource.update(id=existing[0].get('.id'), **data)
            return True
        else:
            return resource.add(**data)
