# -*- coding: utf-8 -*-
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
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        port: int = 8728,
        use_ssl: bool = False,
        plaintext_login: bool = True,
        api_encoding: str = None
    ):
        self.host = host
        self.username = username
        self.password = password
        self.port = port
        self.use_ssl = use_ssl
        self.plaintext_login = plaintext_login
        
        # Se api_encoding não for informado, tenta buscar a configuração do banco de dados pelo IP do Router
        if not api_encoding:
            try:
                from app.core.database import SessionLocal
                from app.models.network import Router
                db_session = SessionLocal()
                try:
                    router_db = db_session.query(Router).filter(Router.ip == host).first()
                    if router_db and router_db.api_encoding:
                        api_encoding = router_db.api_encoding
                finally:
                    db_session.close()
            except Exception:
                pass
                
        self.api_encoding = api_encoding if api_encoding else "utf-8"
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
                # Ajusta a codificação padrão do routeros_api dinamicamente para este roteador
                import collections
                import routeros_api.api_structure as api_struct
                api_struct.default_structure = collections.defaultdict(
                    lambda: api_struct.StringField(encoding=self.api_encoding)
                )

                logger.info(f"Tentando conectar via routeros_api: {self.host}:{self.port} (user: {self.username}, encoding: {self.api_encoding})")
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
                logger.info(f"Tentando conectar via librouteros: {self.host}:{self.port} (user: {self.username}, encoding: {self.api_encoding})")
                self._librouteros_api = librouteros.connect(
                    host=self.host,
                    username=self.username,
                    password=self.password,
                    port=self.port,
                    encoding=self.api_encoding
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

    def add_pppoe_user(self, username: str, password: str, service: str = 'pppoe', profile: Optional[str] = None, rate_limit: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona usuário PPPoE no roteador usando `/ppp/secret`.

        Se o usuário já existir, remove e recria. Caso contrário, cria um novo.
        Retorna o registro criado (dict) ou lança erro em caso de falha.
        """
        import logging
        logger = logging.getLogger(__name__)
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
        if rate_limit:
            data['rate-limit'] = rate_limit
        if comment:
            data['comment'] = comment

        # Log payload enviado ao RouterOS para debug
        try:
            logger.debug(f"add_pppoe_user payload: {data}")
        except Exception:
            pass

        added = None
        try:
            added = resource.add(**data)
        except Exception as exc:
            msg = str(exc)
            logger.error(f"Erro ao adicionar PPPoE user {username}: {exc}")
            # Alguns RouterOS (ou versões da API) não aceitam 'rate-limit' no /ppp/secret
            # Se for esse o caso, tentar novamente sem o parâmetro 'rate-limit'
            if ('unknown parameter rate-limit' in msg) or (b'unknown parameter rate-limit' in getattr(exc, 'args', [])):
                try:
                    logger.warning(f"Router não aceita 'rate-limit' no secret; tentando criar secret {username} sem rate-limit")
                    data_retry = dict(data)
                    data_retry.pop('rate-limit', None)
                    added = resource.add(**data_retry)
                except Exception as exc2:
                    logger.error(f"Tentativa sem 'rate-limit' também falhou para {username}: {exc2}")
                    raise
            else:
                raise

        # Ler e logar o secret criado para verificar quais campos o Router aplicou
        try:
            created = resource.get(name=username)
            if created:
                # Pode retornar lista; logar primeiro item
                item = created[0]
                logger.info(f"Secret PPPoE criado. name={item.get('name')}, profile={item.get('profile')}, rate-limit={item.get('rate-limit')}")
            else:
                logger.warning(f"Secret PPPoE {username} não encontrado após criação")
        except Exception as exc2:
            logger.debug(f"Falha ao recuperar secret PPPoE criado para {username}: {exc2}")

        return added

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

    def set_dhcp_lease(self, ip: str, mac: str, comment: Optional[str] = None):
        """Adiciona/atualiza entrada de Lease Estático no DHCP (`/ip/dhcp-server/lease`)."""
        import logging
        logger = logging.getLogger(__name__)
        self.connect()
        try:
            resource = self._api.get_resource('ip/dhcp-server/lease')
            # Verifica se já existe lease para o IP ou MAC
            entries = resource.get(address=ip)
            if not entries:
                entries = resource.get(mac_address=mac)
            
            data = {'address': ip, 'mac-address': mac}
            if comment:
                data['comment'] = comment

            if entries:
                entry_id = entries[0].get('.id') or entries[0].get('id')
                if entries[0].get('dynamic') == 'true':
                    # Se era dinâmico, primeiro temos que torná-lo estático ou remover e recriar
                    resource.remove(id=entry_id)
                    return resource.add(**data)
                else:
                    return resource.set(id=entry_id, **data)
            else:
                return resource.add(**data)
        except Exception as e:
            logger.error(f"Falha ao configurar DHCP Lease para {ip}: {e}")
            pass # Lidar graciosamente se o DHCP não estiver configurado

    def remove_dhcp_lease(self, ip: str, mac: Optional[str] = None):
        """Remove entrada(s) de Lease no DHCP por IP e opcionalmente MAC."""
        import logging
        logger = logging.getLogger(__name__)
        self.connect()
        try:
            resource = self._api.get_resource('ip/dhcp-server/lease')
            entries = resource.get(address=ip)
            for e in entries:
                if mac and e.get('mac-address') != mac:
                    continue
                eid = e.get('.id') or e.get('id')
                if eid:
                    resource.remove(id=eid)
        except Exception as e:
            logger.error(f"Falha ao remover DHCP Lease para {ip}: {e}")
            pass


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
        # Procura localmente para ser mais robusto
        all_queues = resource.get()
        existing = [q for q in all_queues if q.get('name') == name]
        
        # O cliente não quer que preencha o comentário para Simple Queues.
        # Definimos 'comment': '' para limpar qualquer comentário existente no RouterOS.
        data = {'name': name, 'target': target, 'max-limit': max_limit, 'comment': ''}
        if burst:
            data['burst-limit'] = burst
            
        if existing:
            # atualiza o primeiro encontrado
            qid = existing[0].get('.id') or existing[0].get('id')
            if qid:
                resource.set(id=qid, **data)
                return True
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
                aid = existing_address[0].get('.id') or existing_address[0].get('id')
                if aid: resource.set(id=aid, comment=comment)
            return existing_address[0]
        else:
            # Adiciona novo endereço
            return self.add_ip_address(address, interface, comment)

    def add_to_address_list(self, address: str, list_name: str, comment: str = None):
        """Adiciona um IP a uma Address List."""
        self.connect()
        resource = self._api.get_resource('ip/firewall/address-list')
        
        # Normalizar IP
        ip_clean = address.split('/')[0]
        
        # Buscar todas as entradas da lista para conferir localmente (mais robusto)
        try:
            all_entries = resource.get(list=list_name)
        except Exception:
            all_entries = []
            
        exists = False
        for e in all_entries:
            e_addr = e.get('address', '').split('/')[0]
            if e_addr == ip_clean:
                exists = True
                break
                
        if not exists:
            data = {'address': ip_clean, 'list': list_name}
            if comment:
                data['comment'] = comment
            
            try:
                resource.add(**data)
                return True
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Falha ao adicionar na address-list: {e}")
                return False
        return True

    def kill_client_connections(self, ip: str):
        """Remove todas as conexões ativas de um IP na tabela de Connection Tracking."""
        self.connect()
        try:
            resource = self._api.get_resource('ip/firewall/connection')
            ip_clean = ip.split('/')[0]
            
            # Busca todas as conexões e filtra localmente ou via query se suportado
            # Usar o operador '~' (contém) é mais seguro para pegar IP:Porta
            all_conns = resource.get()
            count = 0
            for conn in all_conns:
                src = conn.get('src-address', '')
                dst = conn.get('dst-address', '')
                if ip_clean in src or ip_clean in dst:
                    cid = conn.get('.id') or conn.get('id')
                    if cid:
                        resource.remove(id=cid)
                        count += 1
            
            import logging
            logging.getLogger(__name__).info(f"Derrubadas {count} conexões do IP {ip_clean}")
            return True
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Falha ao derrubar conexões do IP {ip}: {e}")
            return False

    def setup_suspension_nat_rule(self, notice_url: str):
        """
        Mantida por compatibilidade. A configuração de NAT agora é feita dentro de
        setup_full_suspension_system() usando DST-NAT direto (sem Web Proxy).
        """
        pass

    def setup_suspension_firewall_rules(self, suspension_url: str = None):
        """
        Configura regras de Firewall Filter para clientes bloqueados (pg_corte).

        Lógica (espelhando o padrão Altarede):
          - Permite UDP/53 (DNS) → clientes podem resolver nomes
          - Permite TCP para o IP do portal captivo → página de aviso carrega
          - Bloqueia TCP que não seja para a porta do portal (ex: HTTPS/443)
          - Bloqueia ICMP (ping)
          - Bloqueia UDP (exceto DNS já liberado acima)
        """
        self.connect()
        import logging
        from urllib.parse import urlparse
        logger = logging.getLogger(__name__)

        try:
            filter_rules = self._api.get_resource('ip/firewall/filter')
            all_rules = filter_rules.get()

            # Extrair IP/Host e porta do portal captivo para liberar acesso
            portal_ip = None
            portal_port = None
            if suspension_url:
                try:
                    parsed = urlparse(suspension_url)
                    portal_ip = parsed.hostname
                    portal_port = str(parsed.port) if parsed.port else '80'
                except Exception:
                    pass

            # Obter host público principal para garantir liberação do redirecionamento HTTP 302
            backend_host = None
            try:
                from app.core.config import settings
                backend_host = urlparse(settings.BACKEND_URL).hostname
            except Exception:
                pass

            # Configurar Walled Garden via Address List na RB
            if portal_ip:
                self.add_to_address_list(portal_ip, 'liberados_corte', 'Portal do Provedor (Host)')
            if backend_host and backend_host != portal_ip:
                self.add_to_address_list(backend_host, 'liberados_corte', 'Portal do Provedor (Public)')
            if '10.20.0.1' not in (portal_ip, backend_host):
                self.add_to_address_list('10.20.0.1', 'liberados_corte', 'Portal do Provedor (VPN)')

            # Definição de todas as regras de firewall em ordem de prioridade
            # (serão inseridas na ordem inversa pois usamos place_before no topo)
            rules_to_apply = [
                # 1. Permitir DNS UDP/53 Input — caso o cliente use a própria RB como DNS
                {
                    'chain': 'input',
                    'src-address-list': 'pg_corte',
                    'protocol': 'udp',
                    'dst-port': '53',
                    'action': 'accept',
                    'comment': 'ISP_ALLOW_DNS_INPUT_BLOQUEADOS'
                },
                # 1b. Permitir ICMP Input — cliente bloqueado consegue pingar o roteador (10.20.0.1)
                {
                    'chain': 'input',
                    'src-address-list': 'pg_corte',
                    'protocol': 'icmp',
                    'action': 'accept',
                    'comment': 'ISP_ALLOW_ICMP_INPUT_BLOQUEADOS'
                },
                # 2. Permitir DNS UDP/53 Forward — clientes bloqueados ainda precisam resolver nomes externos
                {
                    'chain': 'forward',
                    'src-address-list': 'pg_corte',
                    'protocol': 'udp',
                    'dst-port': '53',
                    'action': 'accept',
                    'comment': 'ISP_ALLOW_DNS_BLOQUEADOS'
                },
                # 3. Permitir Ping (ICMP) especificamente para os destinos do portal (ex: VPN/Domínio)
                {
                    'chain': 'forward',
                    'src-address-list': 'pg_corte',
                    'dst-address-list': 'liberados_corte',
                    'protocol': 'icmp',
                    'action': 'accept',
                    'comment': 'ISP_ALLOW_ICMP_PORTAL'
                },
                # 4. Bloquear ICMP (ping) para o resto da internet
                {
                    'chain': 'forward',
                    'src-address-list': 'pg_corte',
                    'protocol': 'icmp',
                    'action': 'drop',
                    'comment': 'ISP_DROP_ICMP_BLOQUEADOS'
                },
                # 5. Bloquear UDP (exceto DNS já liberado)
                {
                    'chain': 'forward',
                    'src-address-list': 'pg_corte',
                    'protocol': 'udp',
                    'action': 'drop',
                    'comment': 'ISP_DROP_UDP_BLOQUEADOS'
                },
                # 6. Bloquear TCP que não seja para o portal captivo
                #    (HTTPS/443 e demais portas devem ser bloqueados — só HTTP/80 é redirecionado via NAT)
                {
                    'chain': 'forward',
                    'src-address-list': 'pg_corte',
                    'protocol': 'tcp',
                    'dst-port': f'!{portal_port}' if portal_port else '!80',
                    'action': 'drop',
                    'comment': 'ISP_DROP_TCP_NOPORTAL_BLOQUEADOS'
                },
            ]

            # Se soubermos o IP do portal, adicionar regra de accept explícita para garantir
            # que o tráfego redirecionado e subsequente (incluindo HTTPS/443) chegue ao portal
            if portal_ip:
                rules_to_apply.insert(3, {
                    'chain': 'forward',
                    'src-address-list': 'pg_corte',
                    'dst-address-list': 'liberados_corte',
                    'action': 'accept',
                    'comment': 'ISP_ALLOW_PORTAL_BLOQUEADOS'
                })

            # ── ESTRATÉGIA: Apagar TODAS as regras ISP_ existentes e recriar na ordem certa ──
            # Usar set() não move a regra de posição — a regra de DROP continuaria antes das de ALLOW.
            # Deletar e recriar garante a ordem correta sempre.
            # IMPORTANTE: all_rules vem de /ip/firewall/filter, portanto só apaga regras de filtro,
            # nunca regras de NAT (masquerade). Isso é seguro.
            for r in all_rules:
                if r.get('comment', '').startswith('ISP_'):
                    rid = r.get('.id') or r.get('id')
                    if rid:
                        try:
                            filter_rules.remove(id=rid)
                        except Exception:
                            pass

            # Descobrir a ID da primeira regra não-ISP (para inserir antes dela = no topo)
            current_top_id = None
            fresh_rules = filter_rules.get()
            if fresh_rules:
                current_top_id = fresh_rules[0].get('.id') or fresh_rules[0].get('id')

            # Inserir em ordem REVERSA: como cada add(place_before=X) coloca a regra antes de X,
            # inserindo do final para o início da lista, a primeira regra da lista acaba no topo real.
            for rule in reversed(rules_to_apply):
                if current_top_id:
                    filter_rules.add(place_before=current_top_id, **rule)
                else:
                    filter_rules.add(**rule)

            logger.info("Regras de Firewall Filter para suspensão configuradas com sucesso.")

        except Exception as e:
            logger.error(f"Erro ao configurar Firewall Filter de suspensão: {e}")



    def setup_full_suspension_system(self, suspension_url: str):
        """
        Configura o sistema de suspensão/bloqueio na RB usando DST-NAT direto (sem Web Proxy).

        Fluxo para clientes na address-list 'pg_corte':
          1. TCP/80  -> DST-NAT para IP:porta do portal captivo do sistema
          2. TCP/!80 -> return (o cliente recebe RST - HTTPS falha instantaneamente)
          3. UDP/!53 -> drop (ICMP e UDP bloqueados, DNS liberado)
          4. Firewall Filter complementar garante o drop no chain forward

        O cliente que tenta abrir qualquer página HTTP é redirecionado IMEDIATAMENTE
        para a página de aviso do provedor correto (identificada pelo ID na URL).
        Não depende de Web Proxy, portanto funciona de forma transparente e instantânea.

        Args:
            suspension_url: URL completa da página de aviso do provedor.
                            Exemplo: 'http://10.20.0.1:3015/aviso/empresa/1'
                            O IP e a porta são extraídos desta URL para configurar o DST-NAT.
        """
        self.connect()
        import logging
        from urllib.parse import urlparse
        logger = logging.getLogger(__name__)

        results = []

        # Extrair IP e porta do portal captivo a partir da suspension_url
        try:
            parsed = urlparse(suspension_url)
            portal_host = parsed.hostname
            portal_port = str(parsed.port) if parsed.port else '80'
            if not portal_host:
                raise ValueError("Não foi possível extrair o host da suspension_url")
        except Exception as e:
            results.append(f"ERRO: suspension_url inválida ('{suspension_url}'): {e}")
            logger.error(f"setup_full_suspension_system: suspension_url inválida: {e}")
            return results

        logger.info(f"Configurando suspensão: portal={portal_host}:{portal_port}, url={suspension_url}")

        # ── Passo 1: Desabilitar Web Proxy (não é mais necessário) ────────────────
        try:
            proxy = self._api.get_resource('ip/proxy')
            proxy.set(enabled='no')
            results.append("Web Proxy desabilitado (não utilizado nesta configuração).")
        except Exception as e:
            # Não crítico — alguns RouterOS não permitem desabilitar via API
            results.append(f"Aviso: não foi possível desabilitar Web Proxy: {e}")

        # ── Passo 2: Limpar regras antigas de proxy (migração) ────────────────────
        try:
            proxy_access = self._api.get_resource('ip/proxy/access')
            for rule in proxy_access.get():
                if rule.get('comment') in ('REDIRECIONAMENTO_SUSPENSAO',):
                    rid = rule.get('.id') or rule.get('id')
                    if rid:
                        proxy_access.remove(id=rid)
            results.append("Regras antigas de Proxy Access removidas.")
        except Exception as e:
            results.append(f"Aviso: não foi possível limpar regras de Proxy Access: {e}")

        # ── Passo 3: Configurar DST-NAT (TCP/80 → portal captivo) ─────────────────
        #
        # Espelha o padrão Altarede:
        #   chain=dstnat action=dst-nat to-addresses=<portal_host> to-ports=<portal_port>
        #   protocol=tcp src-address-list=pg_corte dst-port=80
        #
        # Uma segunda regra 'return' para TCP/!80 garante que o cliente receba
        # uma resposta imediata (RST) para HTTPS e outras portas, sem ficar esperando.
        try:
            nat = self._api.get_resource('ip/firewall/nat')
            all_nat = nat.get()

            # Regra principal: redirecionar HTTP (porta 80) para o portal captivo
            dstnat_http = {
                'chain': 'dstnat',
                'protocol': 'tcp',
                'src-address-list': 'pg_corte',
                'dst-port': '80',
                'action': 'dst-nat',
                'to-addresses': portal_host,
                'to-ports': portal_port,
                'comment': 'ISP_BLOQUEIO_REDIR_HTTP'
            }

            # Regra de retorno: outros protocolos TCP (ex: HTTPS) saem do chain dstnat
            # sem ser redirecionados — o Firewall Filter irá dropá-los
            dstnat_return = {
                'chain': 'dstnat',
                'protocol': 'tcp',
                'src-address-list': 'pg_corte',
                'dst-port': '!80',
                'action': 'return',
                'comment': 'ISP_BLOQUEIO_RETURN_TCP'
            }

            # Regra de retorno para UDP bloqueados (DNS passa, o resto vai pro filter)
            dstnat_udp_return = {
                'chain': 'dstnat',
                'protocol': 'udp',
                'src-address-list': 'pg_corte',
                'action': 'return',
                'comment': 'ISP_BLOQUEIO_RETURN_UDP'
            }

            for rule_data in [dstnat_http, dstnat_return, dstnat_udp_return]:
                comment = rule_data['comment']
                existing = [r for r in all_nat if r.get('comment') == comment]
                if existing:
                    rid = existing[0].get('.id') or existing[0].get('id')
                    if rid:
                        nat.set(id=rid, **rule_data)
                else:
                    # Inserir no topo da tabela NAT para ter precedencia
                    if all_nat:
                        first_id = all_nat[0].get('.id') or all_nat[0].get('id')
                        if first_id:
                            nat.add(place_before=first_id, **rule_data)
                        else:
                            nat.add(**rule_data)
                    else:
                        nat.add(**rule_data)
                    # Recarregar para atualizar first_id nas proximas iteracoes
                    all_nat = nat.get()

            results.append(
                f"Regras DST-NAT configuradas: HTTP->{portal_host}:{portal_port}, "
                f"TCP/!80->return, UDP->return."
            )

            # -- SNAT Masquerade: "assina" os pacotes com o IP VPN do MikroTik ------
            #
            # PROBLEMA: Todos os ISPs usam o mesmo IP de destino (IP VPN do servidor).
            # O backend nao saberia qual ISP esta fazendo a chamada apenas pela URL.
            #
            # SOLUCAO: Adicionamos uma regra SNAT (masquerade) para o trafego dos
            # clientes bloqueados que vai em direcao aos IPs liberados no Walled Garden.
            snat_masquerade = {
                'chain': 'srcnat',
                'protocol': 'tcp',
                'src-address-list': 'pg_corte',
                'dst-address-list': 'liberados_corte',
                'action': 'masquerade',
                'comment': 'ISP_SNAT_PORTAL_CAPTIVO'
            }
            existing_snat = [r for r in all_nat if r.get('comment') == 'ISP_SNAT_PORTAL_CAPTIVO']
            if existing_snat:
                rid = existing_snat[0].get('.id') or existing_snat[0].get('id')
                if rid:
                    nat.set(id=rid, **snat_masquerade)
            else:
                nat.add(**snat_masquerade)
            results.append("Regra SNAT masquerade configurada para o Walled Garden (bypassa problemas de roteamento reverso).")

        except Exception as e:
            results.append(f"Erro ao configurar DST-NAT: {e}")
            logger.error(f"setup_full_suspension_system: erro no DST-NAT: {e}")

        # -- Passo 4: Configurar Firewall Filter -----------------------------------
        try:
            self.setup_suspension_firewall_rules(suspension_url)
            results.append("Regras de Firewall Filter configuradas.")
        except Exception as e:
            results.append(f"Erro ao configurar Firewall Filter: {e}")
            logger.error(f"setup_full_suspension_system: erro no Firewall Filter: {e}")

        logger.info(f"setup_full_suspension_system concluído: {results}")
        return results

    def remove_from_address_list(self, address: str, list_name: str):
        """Remove um IP de uma Address List."""
        self.connect()
        resource = self._api.get_resource('ip/firewall/address-list')
        existing = resource.get(address=address, list=list_name)
        for e in existing:
            eid = e.get('.id') or e.get('id')
            if eid: resource.remove(id=eid)
        return True


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

    def get_ppp_profiles(self):
        """Busca profiles PPP (/ppp/profile)."""
        self.connect()
        resource = self._api.get_resource('ppp/profile')
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
            rid = route.get('.id') or route.get('id')
            if rid:
                try:
                    resource.remove(id=rid)
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

    def disconnect_pppoe_active(self, username: str) -> bool:
        """
        Derruba IMEDIATAMENTE a sessão PPPoE ativa de um usuário.

        Remove a entrada em /ppp/active, o que força a Mikrotik a encerrar
        o túnel PPPoE instantaneamente. O cliente perde a internet no mesmo
        instante, sem esperar pelo keepalive timeout.

        Args:
            username: Login PPPoE do cliente (ex: 'joao.silva').

        Returns:
            True se a sessão foi encerrada, False se o usuário não estava conectado.
        """
        self.connect()
        disconnected = False
        try:
            active_resource = self._api.get_resource('ppp/active')
            actives = active_resource.get(name=username)
            for session in actives:
                sid = session.get('.id') or session.get('id')
                if sid:
                    active_resource.remove(id=sid)
                    disconnected = True
                    logger.info(f"[Mikrotik] Sessão PPPoE ativa de '{username}' (id={sid}) encerrada imediatamente.")
        except Exception as e:
            logger.error(f"[Mikrotik] Erro ao encerrar sessão PPPoE ativa de '{username}': {e}")
        return disconnected

    def configure_radius_on_mikrotik(
        self,
        radius_server_ip: str,
        radius_secret: str,
        auth_port: int = 1812,
        acct_port: int = 1813,
        incoming_port: int = 3799,
    ) -> dict:
        """
        Configura automaticamente o servidor RADIUS no Mikrotik.

        Executa os três passos necessários para integrar a RB ao FreeRadius:
          1. Adiciona (ou atualiza) a entrada em /radius com service=ppp
          2. Habilita /ppp aaa (use-radius=yes, accounting=yes)
          3. Habilita /radius incoming (accept=yes, port=3799)

        Args:
            radius_server_ip:  IP do servidor FreeRadius (ex: '10.20.0.1').
            radius_secret:     Segredo compartilhado configurado no NAS.
            auth_port:         Porta de autenticação (padrão 1812).
            acct_port:         Porta de accounting (padrão 1813).
            incoming_port:     Porta CoA/Disconnect (padrão 3799).

        Returns:
            dict com chaves 'success' (bool) e 'steps' (list[str]) relatando cada ação.
        """
        import logging
        logger = logging.getLogger(__name__)
        self.connect()
        steps = []
        success = True

        # ── 1. Configurar entrada /radius ─────────────────────────────────
        try:
            radius_res = self._api.get_resource('radius')
            existing = [r for r in radius_res.get() if r.get('address') == radius_server_ip]

            entry_data = {
                'address': radius_server_ip,
                'secret': radius_secret,
                'service': 'ppp,login',
                'authentication-port': str(auth_port),
                'accounting-port': str(acct_port),
                'comment': 'Brazcom ISP — configurado automaticamente',
            }

            if existing:
                rid = existing[0].get('.id') or existing[0].get('id')
                if rid:
                    radius_res.set(id=rid, **entry_data)
                    steps.append(f"✅ Entrada RADIUS atualizada para {radius_server_ip}:{auth_port}")
                else:
                    radius_res.add(**entry_data)
                    steps.append(f"✅ Entrada RADIUS adicionada para {radius_server_ip}:{auth_port}")
            else:
                radius_res.add(**entry_data)
                steps.append(f"✅ Entrada RADIUS adicionada para {radius_server_ip}:{auth_port}")
        except Exception as e:
            steps.append(f"❌ Falha ao configurar /radius: {e}")
            success = False
            logger.error(f"configure_radius_on_mikrotik: falha no passo 1 (/radius): {e}")

        # ── 2. Habilitar /ppp aaa (use-radius=yes) ────────────────────────
        try:
            ppp_aaa = self._api.get_resource('ppp/aaa')
            ppp_aaa.set(**{'use-radius': 'yes', 'accounting': 'yes'})
            steps.append("✅ /ppp aaa: use-radius=yes, accounting=yes habilitados")
        except Exception as e:
            steps.append(f"❌ Falha ao configurar /ppp aaa: {e}")
            success = False
            logger.error(f"configure_radius_on_mikrotik: falha no passo 2 (/ppp aaa): {e}")

        # ── 3. Habilitar /radius incoming ─────────────────────────────────
        try:
            incoming = self._api.get_resource('radius/incoming')
            incoming.set(**{'accept': 'yes', 'port': str(incoming_port)})
            steps.append(f"✅ /radius incoming: accept=yes, port={incoming_port} habilitados")
        except Exception as e:
            steps.append(f"❌ Falha ao configurar /radius incoming: {e}")
            success = False
            logger.error(f"configure_radius_on_mikrotik: falha no passo 3 (/radius incoming): {e}")

        return {'success': success, 'steps': steps}

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

    def sync_client_connection(self, contrato_id: int, metodo_autenticacao: str, assigned_ip: str = None, mac_address: str = None, interface: str = None, comment: str = None, profile: str = None, max_limit: str = None):
        """Sincroniza a configuração do cliente no router, removendo configurações antigas de outros métodos."""
        self.connect()
        import logging
        logger = logging.getLogger(__name__)

        # 1. Tentar remover configurações de outros métodos (limpeza)
        username = f"contrato_{contrato_id}"
        
        # Remover PPPoE
        try:
            ppp_res = self._api.get_resource('ppp/secret')
            secrets = ppp_res.get(name=username)
            for s in secrets:
                sid = s.get('.id') or s.get('id')
                if sid: ppp_res.remove(id=sid)
        except Exception: pass

        # Remover Hotspot
        try:
            hs_res = self._api.get_resource('ip/hotspot/user')
            users = hs_res.get(name=username)
            for u in users:
                uid = u.get('.id') or u.get('id')
                if uid: hs_res.remove(id=uid)
        except Exception: pass

        # Remover ARP (se o IP for diferente do atual, ou sempre por segurança)
        if assigned_ip:
            try:
                arp_res = self._api.get_resource('ip/arp')
                entries = arp_res.get(address=assigned_ip)
                for e in entries:
                    aid = e.get('.id') or e.get('id')
                    if aid: arp_res.remove(id=aid)
            except Exception: pass

        # Remover Simple Queue antiga (pelo nome antigo ou atual se existir)
        try:
            q_res = self._api.get_resource('queue/simple')
            # Tenta remover pelo nome do cliente (atual) e pelo nome antigo (contrato-ID)
            for qname in [comment, f"contrato-{contrato_id}"]:
                if not qname: continue
                queues = q_res.get(name=qname)
                for q in queues:
                    qid = q.get('.id') or q.get('id')
                    if qid: q_res.remove(id=qid)
        except Exception: pass

        # 3. Remover ARP e DHCP Lease (se IP fornecido)
        if assigned_ip:
            try:
                self.remove_arp_entry(assigned_ip)
            except Exception: pass
            try:
                self.remove_dhcp_lease(assigned_ip)
            except Exception: pass

        # 2. Aplicar a configuração ATUAL
        if metodo_autenticacao == 'PPPOE':
            password_pppoe = f"pppoe_{contrato_id}"
            self.add_pppoe_user(username, password_pppoe, profile=profile, comment=comment)
        
        elif metodo_autenticacao == 'IP_MAC':
            if not assigned_ip or not mac_address or not interface:
                raise ValueError("IP, MAC e Interface são obrigatórios para IP+MAC")
            self.set_arp_entry(assigned_ip, mac_address, interface, comment)
            self.set_dhcp_lease(assigned_ip, mac_address, comment)
        
        elif metodo_autenticacao == 'HOTSPOT':
            password_hs = f"hs_{contrato_id}"
            self.add_hotspot_user(username, password_hs, profile=profile, comment=comment)
        
        # 3. Aplicar QoS (Simple Queue) para IP_MAC
        if metodo_autenticacao == 'IP_MAC' and assigned_ip and max_limit:
            # O nome da queue agora é o nome do cliente (passado no comment)
            queue_name = comment if comment else f"contrato-{contrato_id}"
            self.set_queue_simple(
                name=queue_name,
                target=f"{assigned_ip}/32",
                max_limit=max_limit,
                comment=comment
            )
        
        return True

    def suspend_client_connection(self, contrato_id: int, metodo_autenticacao: str, assigned_ip: str = None, comment: str = None):
        """Bloqueia a conexão do cliente no router."""
        self.connect()
        import logging
        logger = logging.getLogger(__name__)

        if metodo_autenticacao == 'PPPOE':
            username = f"contrato_{contrato_id}"
            resource = self._api.get_resource('ppp/secret')
            secrets = resource.get(name=username)
            if secrets:
                # Em vez de desabilitar, vamos colocar em um Address List de bloqueio
                # O Profile SUSPENSO deve estar configurado no Router com o address-list=pg_corte
                # Ou podemos setar o remote-address-list diretamente no secret se o RouterOS suportar
                # Mas o mais comum é mudar o Profile.
                
                # Por simplicidade e eficiência, vamos adicionar o IP do usuário (se estiver conectado) 
                # a uma Address List e também marcar o secret para que futuras conexões caiam no bloqueio.
                
                # 1. Marcar o Secret com um comentário ou profile específico
                sid = secrets[0].get('.id') or secrets[0].get('id')
                if sid: resource.set(id=sid, comment="SUSPENSO_POR_FALTA_DE_PAGAMENTO")
                
                # 2. Se o usuário estiver ativo, pegamos o IP dele e adicionamos à Address List 'pg_corte'
                try:
                    active_resource = self._api.get_resource('ppp/active')
                    actives = active_resource.get(name=username)
                    for a in actives:
                        user_ip = a.get('address')
                        if user_ip:
                            # Usa o nome do cliente se disponível, senão usa o padrão
                            list_comment = comment if comment else f"Bloqueio Contrato {contrato_id}"
                            self.add_to_address_list(user_ip, 'pg_corte', list_comment)
                            # Derruba conexões ativas para o bloqueio ser instantâneo
                            self.kill_client_connections(user_ip)
                except Exception:
                    pass
                return True
            return False

        elif metodo_autenticacao == 'IP_MAC':
            if not assigned_ip:
                return False
            # Em vez de remover o ARP, vamos adicionar à Address List de bloqueio
            # Isso permite que o redirecionamento via NAT funcione
            try:
                # Usa o nome do cliente se disponível, senão usa o padrão
                list_comment = comment if comment else f"Bloqueio Contrato {contrato_id}"
                self.add_to_address_list(assigned_ip, 'pg_corte', list_comment)
                # Derruba conexões ativas para o bloqueio ser instantâneo
                self.kill_client_connections(assigned_ip)
            except Exception as e:
                logger.warning(f"Falha ao adicionar IP {assigned_ip} à pg_corte: {e}")

            # Conexão bloqueada sem alteração de velocidade, mantendo as configurações de Simple Queue do cliente intactas.
            pass
            return True

        elif metodo_autenticacao == 'HOTSPOT':
            username = f"contrato_{contrato_id}"
            resource = self._api.get_resource('ip/hotspot/user')
            users = resource.get(name=username)
            if users:
                uid = users[0].get('.id') or users[0].get('id')
                if uid: resource.set(id=uid, disabled='yes')
                # Remover do active
                try:
                    active_resource = self._api.get_resource('ip/hotspot/active')
                    actives = active_resource.get(user=username)
                    for a in actives:
                        aid = a.get('.id') or a.get('id')
                        if aid: active_resource.remove(id=aid)
                except Exception:
                    pass
                return True
            return False

        return False

    def unsuspend_client_connection(self, contrato_id: int, metodo_autenticacao: str, assigned_ip: str = None, mac_address: str = None, interface: str = None, comment: str = None):
        """Desbloqueia a conexão do cliente no router."""
        self.connect()
        
        if metodo_autenticacao == 'PPPOE':
            username = f"contrato_{contrato_id}"
            resource = self._api.get_resource('ppp/secret')
            secrets = resource.get(name=username)
            if secrets:
                # 1. Remover comentário de suspensão e garantir que está habilitado
                sid = secrets[0].get('.id') or secrets[0].get('id')
                if sid: resource.set(id=sid, disabled='no', comment="")
                
                # 2. Remover IP da Address List 'pg_corte' se estiver lá
                try:
                    active_resource = self._api.get_resource('ppp/active')
                    actives = active_resource.get(name=username)
                    for a in actives:
                        user_ip = a.get('address')
                        if user_ip:
                            self.remove_from_address_list(user_ip, 'pg_corte')
                except Exception:
                    pass
                return True
            return False

        elif metodo_autenticacao == 'IP_MAC':
            if not assigned_ip:
                return False
            # 1. Remover da Address List de bloqueio
            try:
                self.remove_from_address_list(assigned_ip, 'pg_corte')
            except Exception:
                pass
            
            # 2. Garantir que a entrada ARP e DHCP existem (caso tenham sido removidas)
            if mac_address and interface:
                self.set_arp_entry(ip=assigned_ip, mac=mac_address, interface=interface, comment=comment)
                self.set_dhcp_lease(ip=assigned_ip, mac=mac_address, comment=comment)
            
            # Nota: O limite de banda (Simple Queue) será restaurado na próxima sincronização 
            # ou podemos tentar restaurar aqui se tivéssemos o limite.
            # Como o 'isp_service' chama o sincronismo logo após, isso deve se resolver.
            return True

        elif metodo_autenticacao == 'HOTSPOT':
            username = f"contrato_{contrato_id}"
            resource = self._api.get_resource('ip/hotspot/user')
            users = resource.get(name=username)
            if users:
                uid = users[0].get('.id') or users[0].get('id')
                if uid: resource.set(id=uid, disabled='no')
                return True
            return False

        return False

    def add_pppoe_profile(self, name: str, local_address: str, remote_address_pool: str,
                         rate_limit: Optional[str] = None, comment: Optional[str] = None):
        """Adiciona um profile PPPoE (/ppp/profile)."""
        import logging
        logger = logging.getLogger(__name__)
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

        try:
            logger.debug(f"add_pppoe_profile payload: {data}")
        except Exception:
            pass

        # Criar/atualizar profile
        result = None
        if existing:
            entry_id = existing[0].get('.id') or existing[0].get('id')
            try:
                if entry_id:
                    resource.set(id=entry_id, **data)
                    result = existing[0]
                else:
                    resource.remove(name=name)
                    result = resource.add(**data)
            except Exception as exc:
                logger.error(f"Erro ao atualizar PPP profile {name}: {exc}")
                raise
        else:
            try:
                result = resource.add(**data)
            except Exception as exc:
                logger.error(f"Erro ao criar PPP profile {name}: {exc}")
                raise

        # Ler e logar o profile aplicado no roteador
        try:
            created = resource.get(name=name)
            if created:
                p = created[0]
                logger.info(f"PPP profile aplicado. name={p.get('name')}, remote-address={p.get('remote-address')}, rate-limit={p.get('rate-limit')}")
            else:
                logger.warning(f"PPP profile {name} não encontrado após criação/atualização")
        except Exception as e:
            logger.debug(f"Falha ao recuperar ppp profile criado para {name}: {e}")

        return result

    def add_pppoe_server(self, name: str, interface: str, profile: str, max_sessions: Optional[int] = None, 
                         max_sessions_per_host: Optional[int] = None, authentication: Optional[str] = None,
                         keepalive_timeout: Optional[str] = None):
        """Adiciona um servidor PPPoE (/interface/pppoe-server server).
        
        Usa o comando correto do Winbox: /interface pppoe-server server add
        service-name=server-clientes interface=ether2 default-profile=perfil-padrao disabled=no one-session-per-host=yes
        """
        self.connect()

        # Verificar versão do RouterOS: RouterOS 6.x não suporta PPPoE Server dedicado
        try:
            if self._api is not None:
                sys_res = self._api.get_resource('system/resource').get()
                if sys_res:
                    version = sys_res[0].get('version', '')
                    if version.startswith('6.'):
                        raise RuntimeError(
                            "RouterOS 6.x não suporta configuração de 'PPPoe Server' dedicada via API. "
                            "Atualize para RouterOS 7.x ou use alternativa (Hotspot/PPP secrets)."
                        )
            elif self._librouteros_api is not None:
                try:
                    sys_res = list(self._librouteros_api.path('system/resource').select())[0]
                    version = sys_res.get('version', '')
                    if version.startswith('6.'):
                        raise RuntimeError(
                            "RouterOS 6.x não suporta configuração de 'PPPoe Server' dedicada via API. "
                            "Atualize para RouterOS 7.x ou use alternativa (Hotspot/PPP secrets)."
                        )
                except Exception:
                    # Se falhar ao obter versão via librouteros, seguir em frente e tentar criar;
                    # chamadas subsequentes vão falhar de modo claro se não suportadas.
                    pass
        except RuntimeError:
            # Re-raise para que a rota capture e retorne mensagem clara
            raise
        except Exception:
            # Falha ao obter versão - não interromper, tentaremos executar e lidar com erros abaixo
            pass

        # Tentar com routeros_api primeiro (se disponível)
        last_error = None
        if self._api is not None:
            try:
                return self._add_pppoe_server_routeros_api(name, interface, profile, max_sessions, max_sessions_per_host, authentication, keepalive_timeout)
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
                return self._add_pppoe_server_librouteros(name, interface, profile, max_sessions, max_sessions_per_host, authentication, keepalive_timeout)
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

    def _add_pppoe_server_routeros_api(self, name: str, interface: str, profile: str, max_sessions: Optional[int] = None, 
                                       max_sessions_per_host: Optional[int] = None, authentication: Optional[str] = None,
                                       keepalive_timeout: Optional[str] = None):
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

        # Verificar se já existe um servidor PPPoE com o mesmo service-name
        try:
            existing = self._api.get_resource('interface/pppoe-server server').get(service_name=name)
            if existing:
                # Se já existe, vamos atualizá-lo
                server_id = existing[0].get('.id') or existing[0].get('id')
                if server_id:
                    # Atualizar apenas os campos necessários
                    update_data = {'disabled': 'no'}
                    if interface:
                        update_data['interface'] = interface
                    if profile:
                        update_data['default-profile'] = profile
                    if max_sessions is not None:
                        update_data['max-sessions'] = str(max_sessions)
                    if max_sessions_per_host is not None:
                        update_data['one-session-per-host'] = 'yes' if max_sessions_per_host == 1 else 'no'
                    if authentication:
                        update_data['authentication'] = authentication
                    if keepalive_timeout:
                        update_data['keepalive-timeout'] = keepalive_timeout
                    self._api.get_resource('interface/pppoe-server server').set(id=server_id, **update_data)
                    return existing[0]
                else:
                    # Se não conseguir identificar pelo ID, remover e recriar
                    self._api.get_resource('interface/pppoe-server server').remove(service_name=name)
        except Exception as e:
            logger.debug(f"Erro ao verificar servidores existentes: {e}")

        # Criar novo servidor PPPoE com parâmetros completos
        try:
            create_data = {
                'service-name': name,
                'interface': interface,
                'default-profile': profile,
                'disabled': 'no'
            }
            
            # Adicionar parâmetros opcionais se fornecidos
            if max_sessions is not None:
                create_data['max-sessions'] = str(max_sessions)
            if max_sessions_per_host is not None:
                create_data['one-session-per-host'] = 'yes' if max_sessions_per_host == 1 else 'no'
            if authentication:
                create_data['authentication'] = authentication
            if keepalive_timeout:
                create_data['keepalive-timeout'] = keepalive_timeout
            
            # Criar usando o recurso de servidor PPPoE do menu Interface (mesmo que o Winbox mostre /interface pppoe-server server)
            logger.debug(f"Criando PPPoE server via routeros_api: resource='interface/pppoe-server/server' data={create_data}")
            result = self._api.get_resource('interface/pppoe-server/server').add(**create_data)
            logger.info(f"Servidor PPPoE '{name}' criado com sucesso na interface {interface}")
            return result
        except Exception as e:
            logger.error(f"Falha ao criar servidor PPPoE com parâmetros completos: {str(e)}")
            raise

    def _add_pppoe_server_simple(self):
        """Cria servidor PPPoE usando comando mais simples possível (sem parâmetros)."""
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Tentar criar via caminho de servidores PPPoE ('ppp/pppoe-server') primeiro.
            # Evitar chamar diretamente 'interface/pppoe-server' sem parâmetros pois isso
            # costuma criar entradas na aba Interface (pppoe-in), não na aba PPP > PPPoE Servers.
            if self._api is not None:
                # Preferir o recurso exato usado pelo comando Winbox: '/interface pppoe-server server add'
                try:
                    result = self._api.get_resource('interface/pppoe-server/server').add()
                    logger.info("Servidor PPPoE criado com comando simples (interface/pppoe-server/server, routeros_api)")
                    return result
                except Exception as e1:
                    logger.debug(f"Falha criando via 'interface/pppoe-server server': {e1}")
                    # Tentar alternativa histórica
                    try:
                        result = self._api.get_resource('ppp/pppoe-server').add()
                        logger.info("Servidor PPPoE criado com comando simples (ppp/pppoe-server, routeros_api)")
                        return result
                    except Exception as e2:
                        logger.debug(f"Falha criando via 'ppp/pppoe-server': {e2}")
                        raise RuntimeError(f"Não foi possível criar servidor PPPoE via API: {e1} / {e2}")
            elif self._librouteros_api is not None:
                try:
                    result = self._librouteros_api.path('interface/pppoe-server/server').add()
                    logger.info("Servidor PPPoE criado com comando simples (interface/pppoe-server/server, librouteros)")
                    return result
                except Exception as e1:
                    logger.debug(f"Falha criando via librouteros 'interface/pppoe-server server': {e1}")
                    try:
                        result = self._librouteros_api.path('ppp/pppoe-server').add()
                        logger.info("Servidor PPPoE criado com comando simples (ppp/pppoe-server, librouteros)")
                        return result
                    except Exception as e2:
                        logger.debug(f"Falha criando via librouteros 'ppp/pppoe-server': {e2}")
                        raise RuntimeError(f"Não foi possível criar servidor PPPoE via librouteros: {e1} / {e2}")
            else:
                raise RuntimeError("Nenhuma API disponível")
        except Exception as e:
            logger.error(f"Erro no comando simples: {str(e)}")
            raise

    def _add_pppoe_server_librouteros(self, name: str, interface: str, profile: str, max_sessions: Optional[int] = None, 
                                     max_sessions_per_host: Optional[int] = None, authentication: Optional[str] = None,
                                     keepalive_timeout: Optional[str] = None):
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
        existing_servers = tuple(self._librouteros_api.path('interface/pppoe-server server').select())

        # Filtrar manualmente por service-name
        existing = [s for s in existing_servers if s.get('service-name') == name]

        if existing:
            # Atualizar servidor existente
            server = existing[0]
            update_cmd = {
                '.id': server['.id'],
                'disabled': 'no'
            }
            if interface:
                update_cmd['interface'] = interface
            if profile:
                update_cmd['default-profile'] = profile
            if max_sessions is not None:
                update_cmd['max-sessions'] = str(max_sessions)
            if max_sessions_per_host is not None:
                update_cmd['one-session-per-host'] = 'yes' if max_sessions_per_host == 1 else 'no'
            if authentication:
                update_cmd['authentication'] = authentication
            if keepalive_timeout:
                update_cmd['keepalive-timeout'] = keepalive_timeout

            logger.debug(f"Atualizando PPPoE server via librouteros: resource='interface/pppoe-server server' update={update_cmd}")
            self._librouteros_api.path('interface/pppoe-server server').update(**update_cmd)
            logger.info(f"Servidor PPPoE '{name}' atualizado")
            return server
        else:
            # Criar novo servidor
            create_cmd = {
                'service-name': name,
                'interface': interface,
                'disabled': 'no'
            }
            if profile:
                create_cmd['default-profile'] = profile
            if max_sessions is not None:
                create_cmd['max-sessions'] = str(max_sessions)
            if max_sessions_per_host is not None:
                create_cmd['one-session-per-host'] = 'yes' if max_sessions_per_host == 1 else 'no'
            if authentication:
                create_cmd['authentication'] = authentication
            if keepalive_timeout:
                create_cmd['keepalive-timeout'] = keepalive_timeout

            try:
                logger.debug(f"Criando PPPoE server via librouteros: resource='interface/pppoe-server server' data={create_cmd}")
                result = self._librouteros_api.path('interface/pppoe-server server').add(**create_cmd)
                logger.info(f"Servidor PPPoE '{name}' criado na interface {interface}")
                return result
            except Exception as e:
                logger.error(f"Falha ao criar servidor PPPoE '{name}' na interface {interface}: {e}")
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

        ATENCAO - LIMITACOES CRITICAS - RouterOS 6.49.19:
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
            
            # Servidores (usar o recurso de servidor dentro do menu Interface)
            server_resource = self._api.get_resource('interface/pppoe-server server')
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

    def get_pppoe_servers(self):
        """Retorna lista de servidores PPPoE configurados no router."""
        import logging
        logger = logging.getLogger(__name__)
        
        servers = []
        
        try:
            # Garantir que a conexão seja feita dentro do try para capturar e logar falhas
            self.connect()
            
            logger.info(f"[DEBUG] Buscando servidores PPPoE...")
            
            # Primeiro tentar via librouteros (funciona melhor para PPPoE servers)
            if self._librouteros_api is not None:
                try:
                    logger.info("[DEBUG] Tentando via librouteros")
                    # Caminho que funciona no teste: interface/pppoe-server/server
                    items = list(self._librouteros_api.path('interface/pppoe-server/server').select())
                    logger.info(f"[DEBUG] librouteros encontrou {len(items)} servidores")
                    if items:
                        for it in items:
                            # librouteros retorna dict-like, normalizar keys para str
                            servers.append(dict(it))
                        logger.info(f"[DEBUG] Sucesso via librouteros! Servidores: {servers}")
                        return servers  # Retornar imediatamente se encontrou
                except Exception as e_lib:
                    logger.warning(f"[DEBUG] librouteros falhou: {e_lib}")
            
            # Fallback: tentar via routeros_api
            logger.info("[DEBUG] Tentando via routeros_api")
            try:
                resource = self._api.get_resource('interface/pppoe-server')
                servers_data = resource.get()
                logger.info(f"[DEBUG] routeros_api encontrou {len(servers_data)} servidores")
                if servers_data:
                    servers.extend(servers_data)
                    logger.info(f"[DEBUG] Sucesso via routeros_api! Servidores: {servers}")
            except Exception as e_api:
                logger.warning(f"[DEBUG] routeros_api também falhou: {e_api}")
        
        except Exception as e:
            logger.error(f"[DEBUG] Erro geral ao obter servidores PPPoE: {str(e)}")
        
        logger.info(f"[DEBUG] Total final de servidores PPPoE encontrados: {len(servers)}")
        return servers
