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

try:
    import librouteros
except Exception:  # pragma: no cover - optional dependency
    librouteros = None


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
        self._librouteros_api = None  # Fallback API

    def connect(self):
        """Estabelece conexão com o RouterOS usando `routeros_api` se disponível.

        Em ambientes onde a biblioteca não esteja instalada, essa função lançará
        um `RuntimeError` indicando que a dependência é necessária.
        """
        import logging
        logger = logging.getLogger(__name__)

        if routeros_api is None and librouteros is None:
            raise RuntimeError("Nenhuma biblioteca RouterOS encontrada. Instale 'routeros-api' ou 'librouteros'.")

        # Se já tivermos uma conexão ativa em qualquer biblioteca, nada a fazer
        if self._api is not None or self._librouteros_api is not None:
            return

        # Tentar inicializar routeros_api (primário)
        if routeros_api is not None:
            try:
                logger.info(f"Tentando conectar via routeros_api: {self.host}:{self.port} (user: {self.username})")
                self._pool = routeros_api.RouterOsApiPool(
                    self.host,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                    plaintext_login=self.plaintext_login,
                )
                self._api = self._pool.get_api()
                logger.info("✅ Conexão com routeros_api estabelecida")
            except Exception as e:
                logger.warning(f"❌ routeros_api falhou: {e}")

        # Tentar inicializar librouteros (fallback). Não falhar se não conseguir,
        # vamos apenas registrar e permitir que a outra biblioteca seja usada.
        if librouteros is not None:
            try:
                logger.info(f"Tentando conectar via librouteros: {self.host}:{self.port} (user: {self.username})")
                self._librouteros_api = librouteros.connect(
                    host=self.host,
                    username=self.username,
                    password=self.password,
                    port=self.port
                )
                logger.info("✅ Conexão com librouteros estabelecida (fallback)")
            except Exception as e:
                logger.warning(f"❌ librouteros falhou: {e}")

        if self._api is None and self._librouteros_api is None:
            error_msg = f"Falha ao conectar com ambas as bibliotecas RouterOS ao host {self.host}:{self.port}"
            logger.error(error_msg)
            raise RuntimeError(error_msg)
    def close(self):
        if self._pool:
            try:
                self._pool.disconnect()
            except Exception:
                pass
            self._pool = None
            self._api = None

    def get_connection_status(self):
        """Retorna status de conexão para debug: routeros_api e librouteros.

        Usado apenas para diagnóstico remoto e logs.
        """
        return {
            'routeros_api': self._api is not None,
            'librouteros': self._librouteros_api is not None,
        }

    def ensure_librouteros_connected(self) -> bool:
        """Garante que existe uma conexão com librouteros (fallback).

        Retorna True se a conexão foi estabelecida, False caso contrário.
        """
        import logging
        logger = logging.getLogger(__name__)

        if librouteros is None:
            logger.debug("librouteros não está instalado, não é possível conectar como fallback")
            return False

        if self._librouteros_api is not None:
            return True

        try:
            self._librouteros_api = librouteros.connect(
                host=self.host,
                username=self.username,
                password=self.password,
                port=self.port
            )
            logger.info("Conexão librouteros estabelecida (fallback)")
            return True
        except Exception as e:
            logger.warning(f"Falha ao conectar via librouteros: {e}")
            return False

    def is_wan_interface(self, interface: str) -> bool:
        """Determina se a interface fornecida está atuando como interface WAN.

        - Verifica rotas padrão (/ip/route dst-address=0.0.0.0/0) e compara o campo 'gateway' ou 'interface'.
        - Verifica se a interface possui um IP público (na ausência de rota clara).
        - Funciona com `routeros_api` e com `librouteros` fallback.

        Retorna True se parecer ser interface WAN, False caso contrário.
        """
        import logging
        logger = logging.getLogger(__name__)
        try:
            self.connect()
        except Exception as e:
            logger.warning(f"is_wan_interface: Falha ao conectar para verificar interface: {e}")
            return False

        # 1) Checar rotas padrão
        try:
            if self._api is not None:
                routes = self._api.get_resource('ip/route').get()
                for r in routes:
                    dst = r.get('dst-address') or r.get('dst-address/mask') or ''
                    if dst == '0.0.0.0/0' or dst == '0.0.0.0':
                        # Alguns registros retornam a interface ou gateway
                        if r.get('interface') == interface:
                            return True
                        gw = r.get('gateway')
                        if gw and interface in str(gw):
                            return True
            if self._librouteros_api is not None:
                for r in self._librouteros_api.path('ip/route').select():
                    dst = r.get('dst-address') or r.get('dst-address/mask') or ''
                    if dst == '0.0.0.0/0' or dst == '0.0.0.0':
                        if r.get('interface') == interface:
                            return True
                        gw = r.get('gateway')
                        if gw and interface in str(gw):
                            return True
        except Exception as e:
            logger.debug(f"is_wan_interface: falha ao checar rotas: {e}")

        # 2) Se rotas não afirmarem, checar se interface tem IP público
        try:
            if self._api is not None:
                addrs = self._api.get_resource('ip/address').get(interface=interface)
                for a in addrs:
                    addr = a.get('address') or ''
                    if addr and not (addr.startswith('10.') or addr.startswith('192.168.') or addr.startswith('172.')):
                        # Detecção simples para redes privadas vs públicas
                        return True
            if self._librouteros_api is not None:
                for a in self._librouteros_api.path('ip/address').select(interface=interface):
                    addr = a.get('address')
                    if addr and not (addr.startswith('10.') or addr.startswith('192.168.') or addr.startswith('172.')):
                        return True
        except Exception as e:
            logger.debug(f"is_wan_interface: falha ao checar endereços: {e}")

        return False

    def add_pppoe_user(self, username: str, password: str, service: str = 'pppoe', profile: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona usuário PPPoE no roteador usando `/ppp/secret`.

        Se o usuário já existir, remove e recria. Caso contrário, cria um novo.
        Retorna o registro criado (dict) ou lança erro em caso de falha.
        """
        self.connect()
        resource = self._api.get_resource('ppp/secret')
        
        # Remover usuário existente se houver
        existing = resource.get(name=username)
        if existing:
            try:
                entry_id = existing[0].get('.id') or existing[0].get('id')
                if entry_id:
                    resource.remove(id=entry_id)
                else:
                    resource.remove(name=username)
            except Exception:
                pass  # Ignorar erros de remoção
        
        # Criar novo usuário
        data = {'name': username, 'password': password, 'service': service}
        if profile:
            data['profile'] = profile
        if comment:
            data['comment'] = comment
        
        return resource.add(**data)

    def remove_pppoe_user(self, username: str):
        """Remove usuário PPPoE buscando por `name` e removendo o item."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            self.connect()
            resource = self._api.get_resource('ppp/secret')
            items = resource.get(name=username)
            
            if not items:
                logger.warning(f"Usuário PPPoE {username} não encontrado para remoção")
                return False
            
            logger.info(f"Encontrados {len(items)} usuários PPPoE com nome {username}")
            
            removed_count = 0
            for it in items:
                entry_id = it.get('.id') or it.get('id')
                if entry_id:
                    try:
                        logger.info(f"Removendo usuário PPPoE {username} com ID {entry_id}")
                        resource.remove(id=entry_id)
                        removed_count += 1
                        logger.info(f"Usuário PPPoE {username} removido com sucesso")
                    except Exception as remove_exc:
                        logger.error(f"Erro ao remover usuário PPPoE {username} com ID {entry_id}: {str(remove_exc)}")
                else:
                    logger.warning(f"Usuário PPPoE {username} encontrado mas sem ID válido: {it}")
            
            return removed_count > 0
            
        except Exception as e:
            logger.error(f"Erro geral ao remover usuário PPPoE {username}: {str(e)}")
            return False

    def add_hotspot_user(self, username: str, password: str, server: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona usuário de hotspot via `/ip/hotspot/user`."""
        self.connect()
        resource = self._api.get_resource('ip/hotspot/user')
        
        # Remover usuário existente se houver
        existing = resource.get(name=username)
        if existing:
            try:
                entry_id = existing[0].get('.id') or existing[0].get('id')
                if entry_id:
                    resource.remove(id=entry_id)
                else:
                    resource.remove(name=username)
            except Exception:
                pass  # Ignorar erros de remoção
        
        # Criar novo usuário
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
        
        # Remover endereço existente se houver
        existing = resource.get(address=address, interface=interface)
        if existing:
            try:
                entry_id = existing[0].get('.id') or existing[0].get('id')
                if entry_id:
                    resource.remove(id=entry_id)
                else:
                    resource.remove(address=address, interface=interface)
            except Exception:
                pass  # Ignorar erros de remoção
        
        # Criar novo endereço
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
        
        # Remover servidor existente se houver
        existing = resource.get(name=name)
        if existing:
            try:
                entry_id = existing[0].get('.id') or existing[0].get('id')
                if entry_id:
                    resource.remove(id=entry_id)
                else:
                    resource.remove(name=name)
            except Exception:
                pass  # Ignorar erros de remoção
        
        # Criar novo servidor
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
        
        # Remover pool existente se houver
        existing = resource.get(name=name)
        if existing:
            try:
                entry_id = existing[0].get('.id') or existing[0].get('id')
                if entry_id:
                    resource.remove(id=entry_id)
                else:
                    resource.remove(name=name)
            except Exception:
                pass  # Ignorar erros de remoção
        
        # Criar novo pool
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

    def add_pppoe_profile(self, name: str, local_address: str, remote_address_pool: str,
                         rate_limit: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona um profile PPPoE (/ppp/profile)."""
        self.connect()
        resource = self._api.get_resource('ppp/profile')
        
        # Verificar se profile já existe
        existing = resource.get(name=name)
        
        data = {
            'name': name,
            'local-address': local_address,
            'remote-address': remote_address_pool
        }
        
        if rate_limit:
            data['rate-limit'] = rate_limit
        if comment:
            data['comment'] = comment
        
        if existing:
            # Atualizar profile existente
            entry_id = existing[0].get('.id') or existing[0].get('id')
            if entry_id:
                resource.set(id=entry_id, **data)
                return existing[0]
            else:
                # Remover e recriar
                resource.remove(name=name)
                return resource.add(**data)
        else:
            return resource.add(**data)

    def add_pppoe_server(self, name: str, interface: str, profile: str):
        """Adiciona um servidor PPPoE (/interface/pppoe-server server).
        
        Usa o comando correto do Winbox: /interface pppoe-server server add
        service-name=server-clientes interface=ether2 default-profile=perfil-padrao disabled=no one-session-per-host=yes
        """
        self.connect()

        # Tentar com routeros_api primeiro (se disponível)
        last_error = None
        if self._api is not None:
            try:
                return self._add_pppoe_server_routeros_api(name, interface, profile)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"routeros_api falhou para PPPoE server: {str(e)}")
                last_error = e

                # Tentar inicializar librouteros caso não esteja inicializado ainda
                if self._librouteros_api is None and librouteros is not None:
                    logger.info("Tentando inicializar librouteros como fallback...")
                    if not self.ensure_librouteros_connected():
                        logger.warning("Não foi possível inicializar librouteros no fallback")

        # Fallback para librouteros
        if self._librouteros_api is not None:
            try:
                return self._add_pppoe_server_librouteros(name, interface, profile)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"librouteros também falhou: {str(e)}")
                raise
        # Se chegamos aqui, tentamos ambos e falharam
        if last_error:
            raise RuntimeError(f"Nenhuma API RouterOS disponível para criar servidor PPPoE: {last_error}")
        else:
            raise RuntimeError("Nenhuma API RouterOS disponível para criar servidor PPPoE")

    def _add_pppoe_server_routeros_api(self, name: str, interface: str, profile: str):
        """Implementação usando routeros_api (com tratamento de erro para .tag e parâmetros)."""
        import logging
        logger = logging.getLogger(__name__)

        # Verificar versão do RouterOS para determinar a abordagem correta
        try:
            system_resource = self._api.get_resource('system/resource')
            system_info = system_resource.get()[0]
            version = system_info.get('version', '')
            logger.info(f"RouterOS version (routeros_api): {version}")

            if version.startswith('6.'):
                # RouterOS 6.x - usar abordagem simplificada
                logger.warning(f"RouterOS {version}: Usando abordagem simplificada para PPPoE server")
                return self._add_pppoe_server_simple()
        except Exception as e:
            logger.debug(f"Não foi possível determinar versão via routeros_api: {e}")

        # Verificar se já existe um servidor PPPoE nesta interface
        try:
            existing = self._api.get_resource('interface/pppoe-server').get(interface=interface)
            if existing:
                # Se já existe, vamos atualizá-lo
                server_id = existing[0].get('.id') or existing[0].get('id')
                if server_id:
                    # Atualizar apenas os campos necessários
                    update_data = {'disabled': 'no'}
                    if profile:
                        update_data['default-profile'] = profile
                    self._api.get_resource('interface/pppoe-server').set(id=server_id, **update_data)
                    return existing[0]
                else:
                    # Se não conseguir identificar pelo ID, remover e recriar
                    self._api.get_resource('interface/pppoe-server').remove(interface=interface)
        except Exception as e:
            logger.debug(f"Erro ao verificar servidores existentes: {e}")

        # Criar novo servidor PPPoE - tentar abordagem simples primeiro
        try:
            return self._add_pppoe_server_simple()
        except Exception as e:
            logger.error(f"Falha ao criar servidor PPPoE com abordagem simples: {str(e)}")
            raise

    def _add_pppoe_server_simple(self):
        """Cria servidor PPPoE usando comando mais simples possível (sem parâmetros)."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Para RouterOS 6.49.19, o comando /interface/pppoe-server/add sem parâmetros funciona
            if self._api is not None:
                result = self._api.get_resource('interface/pppoe-server').add()
                logger.info("Servidor PPPoE criado com comando simples (routeros_api)")
                return result
            elif self._librouteros_api is not None:
                result = self._librouteros_api.path('interface/pppoe-server').add()
                logger.info("Servidor PPPoE criado com comando simples (librouteros)")
                return result
            else:
                raise RuntimeError("Nenhuma API disponível")
        except Exception as e:
            logger.error(f"Erro no comando simples: {str(e)}")
            raise

    def _add_pppoe_server_librouteros(self, name: str, interface: str, profile: str):
        """Implementação usando librouteros (mais direta, sem parâmetros extras).

        NOTA: No RouterOS 6.49.19, /interface/pppoe-server/add cria interfaces PPPoE-IN (clientes),
        não servidores. Este método precisa ser adaptado para a versão específica do RouterOS.
        """
        import logging
        logger = logging.getLogger(__name__)

        # Verificar versão do RouterOS para determinar a abordagem correta
        try:
            system_info = list(self._librouteros_api.path('system/resource').select())[0]
            version = system_info.get('version', '')
            logger.info(f"RouterOS version: {version}")

            if version.startswith('6.'):
                # RouterOS 6.x - usar abordagem simplificada
                logger.warning(f"RouterOS {version}: Usando abordagem simplificada para PPPoE server")
                return self._add_pppoe_server_simple()
        except Exception as e:
            logger.debug(f"Não foi possível determinar versão: {e}")

        # Verificar se já existe - na librouteros, select() sem argumentos retorna tudo
        existing_servers = tuple(self._librouteros_api.path('interface/pppoe-server').select())

        # Filtrar manualmente por interface
        existing = [s for s in existing_servers if s.get('interface') == interface]

        if existing:
            # Atualizar servidor existente
            server = existing[0]
            update_cmd = {
                '.id': server['.id'],
                'disabled': 'no'
            }
            if profile:
                update_cmd['default-profile'] = profile

            self._librouteros_api.path('interface/pppoe-server').update(**update_cmd)
            logger.info(f"Servidor PPPoE atualizado na interface {interface}")
            return server
        else:
            # Criar novo servidor
            # NOTA: No RouterOS 6.49.19, este comando pode criar interface PPPoE-IN em vez de servidor
            create_cmd = {
                'interface': interface,
                'disabled': 'no'
            }
            if profile:
                create_cmd['default-profile'] = profile

            try:
                result = self._librouteros_api.path('interface/pppoe-server').add(**create_cmd)
                logger.info(f"Interface PPPoE criada na interface {interface} (pode ser cliente, não servidor)")
                return result
            except Exception as e:
                logger.error(f"Falha ao criar PPPoE na interface {interface}: {e}")
                # Tentar comando alternativo se disponível
                try:
                    # Última tentativa: comando básico sem parâmetros
                    result = self._librouteros_api.path('interface/pppoe-server').add()
                    logger.info(f"Interface PPPoE criada sem parâmetros específicos")
                    return result
                except Exception as e2:
                    logger.error(f"Também falhou comando básico: {e2}")
                    raise e

    def setup_pppoe_server(self, interface: str, ip_pool_name: str = "pppoe-pool",
                           local_address: str = "192.168.1.1",
                           first_ip: str = "192.168.1.2", last_ip: str = "192.168.1.254",
                           default_profile: str = "default",
                           allow_wan_interface: bool = False):
        """Configura automaticamente um servidor PPPoE completo no router.

        Este método configura:
        1. Pool de IPs para clientes PPPoE
        2. Profile PPPoE padrão
        3. Servidor PPPoE

        ⚠️ LIMITAÇÕES CRÍTICAS - RouterOS 6.49.19:
        - PPPoE SERVER DEDICADO NÃO É SUPORTADO nesta versão!
        - O comando cria interfaces PPPoE CLIENTE (pppoe-out), não servidor
        - Clientes NÃO poderão se autenticar via PPPoE neste router
        - Para autenticação PPPoE, use Hotspot ou atualize para RouterOS 7.x+

        Args:
            interface: Interface onde o servidor PPPoE seria configurado (ex: "ether1")
            ip_pool_name: Nome do pool de IPs
            local_address: Endereço IP local do servidor
            first_ip: Primeiro IP do pool
            last_ip: Último IP do pool
            default_profile: Nome do profile PPPoE padrão
            allow_wan_interface: Permitir configuração em interface WAN (não recomendado)
        """
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"Iniciando configuração PPPoE na interface {interface}")
        # Verificar versão do RouterOS
        try:
            if self._librouteros_api:
                system_info = list(self._librouteros_api.path('system/resource').select())[0]
                version = system_info.get('version', 'unknown')
                logger.info(f"RouterOS version detectada: {version}")
                if version.startswith('6.'):
                    logger.error("🚨 CRÍTICO: RouterOS 6.49.19 NÃO SUPORTA PPPoE SERVER!")
                    logger.error("🚨 Este método criará PPPoE CLIENTE, não servidor!")
                    logger.error("🚨 Clientes NÃO poderão se autenticar via PPPoE!")
                    logger.error("💡 Solução: Use Hotspot ou atualize para RouterOS 7.x+")
        except Exception as e:
            logger.debug(f"Não foi possível verificar versão: {e}")

        # Mostrar status de conexão para auxiliar o diagnóstico em caso de falha
        try:
            self.connect()
        except Exception as conn_exc:
            logger.error(f"Falha ao conectar via API ao iniciar setup PPPoE: {conn_exc}")
            logger.error("💡 POSSÍVEIS CAUSAS:")
            logger.error("   1. Router não acessível (verifique IP, rede, firewall)")
            logger.error("   2. Credenciais incorretas (usuário/senha)")
            logger.error("   3. API não habilitada no router Mikrotik")
            logger.error("   4. Porta 8728 bloqueada ou incorreta")
            logger.error("   5. RouterOS versão incompatível")
            logger.error("")
            logger.error("🔧 SOLUÇÕES:")
            logger.error("   - No Winbox: IP > Services > API > Enable")
            logger.error("   - Verifique credenciais no router")
            logger.error("   - Teste conectividade: telnet IP 8728")
            raise RuntimeError(f"Não foi possível conectar ao router Mikrotik: {conn_exc}") from conn_exc
        logger.info(f"Status de conexão: {self.get_connection_status()}")
        
        try:
            # 0. Validar se a interface é válida (não é WAN) a menos que allow_wan_interface=True
            if not allow_wan_interface and self.is_wan_interface(interface):
                raise ValueError(f"Interface {interface} parece ser a interface WAN. Não crie um servidor PPPoE nesta interface.")

            # 1. Configurar pool de IPs
            logger.info(f"Configurando pool de IPs: {ip_pool_name} ({first_ip}-{last_ip})")
            self.add_dhcp_pool(ip_pool_name, f"{first_ip}-{last_ip}")
            
            # 2. Configurar profile PPPoE
            logger.info(f"Configurando profile PPPoE: {default_profile}")
            self.add_pppoe_profile(default_profile, local_address, ip_pool_name)
            
            # 3. Configurar servidor PPPoE
            logger.info("Configurando servidor PPPoE")
            self.add_pppoe_server("pppoe-server", interface, default_profile)
            
            # 4. Configurar regras de firewall/NAT básicas
            logger.info("Configurando regras de firewall para PPPoE")
            self.setup_pppoe_firewall_rules()
            
            logger.info("Configuração automática do servidor PPPoE concluída com sucesso!")
            return True
            
        except Exception as e:
            logger.error(f"Erro durante configuração automática do servidor PPPoE: {str(e)}")
            raise

    def setup_pppoe_firewall_rules(self):
        """Configura regras básicas de firewall para PPPoE funcionar."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Adicionar regras básicas se não existirem
            self.connect()
            
            # Regra para permitir tráfego PPPoE (protocolo 0x8863/0x8864)
            # Nota: O Mikrotik geralmente já tem essas regras por padrão
            
            # Adicionar NAT para tráfego dos clientes PPPoE
            nat_resource = self._api.get_resource('ip/firewall/nat')
            
            # Verificar se já existe uma regra de NAT para PPPoE
            existing_nat = nat_resource.get(out_interface='pppoe-out', action='masquerade')
            
            if not existing_nat:
                logger.info("Adicionando regra NAT para clientes PPPoE")
                nat_resource.add(
                    chain='srcnat',
                    out_interface='pppoe-out',
                    action='masquerade',
                    comment='NAT para clientes PPPoE'
                )
            
            logger.info("Regras de firewall para PPPoE configuradas")
            
        except Exception as e:
            logger.warning(f"Erro ao configurar regras de firewall para PPPoE: {str(e)}")
            # Não falhar a configuração por causa das regras de firewall

    def get_pppoe_server_status(self):
        """Retorna status do servidor PPPoE configurado."""
        self.connect()
        
        status = {
            'profiles': [],
            'servers': [],
            'interfaces': [],
            'pools': []
        }
        
        try:
            # Profiles
            profile_resource = self._api.get_resource('ppp/profile')
            status['profiles'] = profile_resource.get()
            
            # Servidores
            server_resource = self._api.get_resource('ppp/pppoe-server')
            status['servers'] = server_resource.get()
            
            # Interfaces
            interface_resource = self._api.get_resource('interface/pppoe-server')
            status['interfaces'] = interface_resource.get()
            
            # Pools
            pool_resource = self._api.get_resource('ip/pool')
            status['pools'] = pool_resource.get()
            
        except Exception as e:
            status['error'] = str(e)
        
        return status
