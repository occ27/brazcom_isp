"""
Serviço de Monitoramento FTTH

Responsável por:
- Verificar conectividade de ONUs via ICMP (ping)
- Verificar conectividade via API Mikrotik (Solução B) com fallback para ICMP
- Coletar parâmetros ópticos via SNMP (quando disponível)
- Gerar snapshots de monitoramento para histórico e alertas
"""
import socket
import struct
import time
import logging
import os
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import ServicoContratado, Cliente, StatusContrato
from app.models.ftth import OLT, CTO, FTTHMonitorSnapshot
from app.models.network import Router

logger = logging.getLogger(__name__)

# Limiar de sinal óptico para considerar "degradado" (em dBm)
RX_POWER_WARNING_THRESHOLD = -25.0   # Abaixo disso = alerta
RX_POWER_CRITICAL_THRESHOLD = -28.0  # Abaixo disso = crítico/offline

# Latência máxima para considerar link ok (ms)
LATENCY_WARNING_THRESHOLD = 100.0
LATENCY_CRITICAL_THRESHOLD = 500.0

# ── Configuração de Paralelismo ────────────────────────────────────────────────
# Número máximo de threads paralelas por empresa:
#   - Cada OLT/Mikrotik ocupa 1 thread. Contratores sem OLT usam threads extras.
#   - Aumentar se houver muitos provedores / OLTs. Reduzir se o servidor for limitado.
MAX_OLT_WORKERS = int(os.environ.get("FTTH_MAX_OLT_WORKERS", "20"))

# Threads extras para contratos FTTH sem OLT configurada (ping ICMP puro)
MAX_ICMP_WORKERS = int(os.environ.get("FTTH_MAX_ICMP_WORKERS", "15"))

# Timeout total por thread de OLT antes de ser cancelada (segundos)
OLT_THREAD_TIMEOUT = int(os.environ.get("FTTH_OLT_THREAD_TIMEOUT", "90"))
# ────────────────────────────────────────────────────────────────────────


class FTTHMonitorService:

    # =====================================================================
    # PING / ICMP
    # =====================================================================

    @staticmethod
    def ping_host(ip: str, timeout: float = 2.0, count: int = 3) -> Dict[str, Any]:
        """
        Verifica se um host responde a ping ICMP.
        
        Usa o comando 'ping' do sistema operacional para compatibilidade
        em diferentes plataformas (Linux/Mac/Windows).
        
        Returns:
            dict com: is_reachable (bool), latencia_ms (float|None), detalhe_erro (str|None)
        """
        if not ip:
            return {"is_reachable": False, "latencia_ms": None, "detalhe_erro": "IP não informado"}

        try:
            # Detecta OS para escolher parâmetros do ping
            import platform
            system = platform.system().lower()

            if system == "windows":
                cmd = ["ping", "-n", str(count), "-w", str(int(timeout * 1000)), ip]
            else:
                # Linux e macOS
                cmd = ["ping", "-c", str(count), "-W", str(int(timeout)), "-q", ip]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout * count + 2
            )

            if result.returncode == 0:
                # Extrair latência média do output
                latencia = FTTHMonitorService._parse_ping_latency(result.stdout, system)
                return {
                    "is_reachable": True,
                    "latencia_ms": latencia,
                    "detalhe_erro": None
                }
            else:
                return {
                    "is_reachable": False,
                    "latencia_ms": None,
                    "detalhe_erro": f"Host não responde (exit code {result.returncode})"
                }

        except subprocess.TimeoutExpired:
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": "Timeout ao executar ping"
            }
        except FileNotFoundError:
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": "Comando ping não encontrado no sistema"
            }
        except Exception as e:
            logger.error(f"Erro ao fazer ping para {ip}: {e}")
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": str(e)
            }

    @staticmethod
    def _parse_ping_latency(output: str, system: str) -> Optional[float]:
        """Extrai a latência média do output do ping."""
        import re
        try:
            if system == "windows":
                # "Média = 12ms"
                match = re.search(r'[Mm][éeé]dia\s*=\s*(\d+(?:[.,]\d+)?)\s*ms', output)
                if match:
                    return float(match.group(1).replace(',', '.'))
            else:
                # Linux: "rtt min/avg/max/mdev = 0.123/0.234/0.456/0.078 ms"
                # macOS: "round-trip min/avg/max/stddev = 0.123/0.234/0.456/0.078 ms"
                match = re.search(r'min/avg/max[^=]*=\s*[\d.]+/([\d.]+)/', output)
                if match:
                    return float(match.group(1))
        except Exception:
            pass
        return None

    # =====================================================================
    # MIKROTIK API MONITORING (Solução B)
    # =====================================================================

    @staticmethod
    def check_mikrotik_reachable(
        host: str,
        port: int = 8728,
        timeout: float = 3.0
    ) -> bool:
        """
        Verifica se o Mikrotik está respondendo na porta da API (TCP).

        Antes de tentar uma conexão API completa (que pode ser lenta),
        abre um socket TCP simples para confirmar que o host está acessível.
        Isso evita travar o polling caso o provedor esteja offline ou a VPN
        não esteja estabelecida.

        Returns:
            True se a porta TCP responder dentro do timeout, False caso contrário.
        """
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError) as e:
            logger.debug(f"Mikrotik {host}:{port} inacessível: {e}")
            return False

    @staticmethod
    def ping_via_mikrotik_api(
        router: Router,
        ip: str,
        count: int = 3,
        timeout_api: float = 5.0
    ) -> Dict[str, Any]:
        """
        Solicita ao Mikrotik (via API RouterOS) que execute um ping para o IP informado.

        Fluxo:
          1. Verifica se o Mikrotik responde na porta da API (TCP check).
          2. Se inacessível, retorna erro sem tentar a conexão API completa.
          3. Conecta via MikrotikController e executa /ping.
          4. Parseia a resposta e retorna latência e status.

        Args:
            router: Instância do modelo Router com credenciais do Mikrotik.
            ip: IP do cliente/ONU a pingar (dentro da rede local do provedor).
            count: Número de pacotes ICMP a enviar.
            timeout_api: Timeout em segundos para a conexão API.

        Returns:
            dict com: is_reachable (bool), latencia_ms (float|None), detalhe_erro (str|None)
        """
        from app.mikrotik.controller import MikrotikController

        host = router.ip
        port = router.porta or 8728
        user = router.usuario
        
        from app.core.security import decrypt_password
        try:
            password = decrypt_password(router.senha) if router.senha else ""
        except Exception as e:
            logger.warning(f"Falha ao descriptografar senha do roteador, usando texto plano: {e}")
            password = router.senha

        if not host or not user or not password:
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": "Credenciais Mikrotik API não configuradas no Roteador"
            }

        # ── ETAPA 1: Verificar se o Mikrotik está acessível ─────────────────
        logger.debug(f"Verificando acessibilidade do Mikrotik {host}:{port} antes do ping via API...")
        if not FTTHMonitorService.check_mikrotik_reachable(host, port, timeout=timeout_api):
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": f"Mikrotik {host}:{port} inacessível (VPN offline ou host inativo)"
            }

        # ── ETAPA 2: Executar o ping via API RouterOS ────────────────────────
        ctrl = MikrotikController(
            host=host,
            username=user,
            password=password,
            port=port,
        )
        try:
            ctrl.connect()

            # Tenta via routeros_api (primário)
            if ctrl._api is not None:
                try:
                    resource = ctrl._api.get_resource('ping')
                    results = resource.call(
                        **{'address': ip, 'count': str(count), 'interval': '0.2'}
                    )
                    return FTTHMonitorService._parse_mikrotik_ping_result(results, ip)
                except Exception as e:
                    logger.debug(f"routeros_api ping falhou: {e} — tentando librouteros...")

            # Fallback: librouteros
            if ctrl._librouteros_api is not None:
                try:
                    results = list(ctrl._librouteros_api(
                        '/ping',
                        **{'address': ip, 'count': str(count)}
                    ))
                    return FTTHMonitorService._parse_mikrotik_ping_result(results, ip)
                except Exception as e:
                    logger.debug(f"librouteros ping falhou: {e}")
                    raise

            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": "Nenhuma biblioteca RouterOS disponível para executar ping"
            }

        except Exception as e:
            logger.warning(f"Erro ao executar ping via API Mikrotik ({host}) para {ip}: {e}")
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": f"Erro API Mikrotik: {e}"
            }
        finally:
            try:
                ctrl.close()
            except Exception:
                pass

    @staticmethod
    def _parse_mikrotik_ping_result(
        results: List[Dict],
        ip: str
    ) -> Dict[str, Any]:
        """
        Interpreta a lista de respostas retornadas pelo /ping do RouterOS.

        O RouterOS retorna um dict por pacote enviado. Campos relevantes:
          - 'status'       : 'timeout' quando sem resposta
          - 'time'         : latência em string, ex: '1ms', '345us'
          - 'received'     : '1' se houve resposta
          - 'packet-loss'  : percentual de perda (string)
        """
        if not results:
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": f"Nenhuma resposta do ping para {ip} via Mikrotik"
            }

        # Filtra pacotes recebidos com sucesso
        received = [r for r in results if str(r.get('status', '')).lower() != 'timeout'
                    and str(r.get('received', '0')) == '1']

        if not received:
            # Tentativa alternativa: verificar se algum tem 'time'
            received = [r for r in results if r.get('time')]

        if not received:
            return {
                "is_reachable": False,
                "latencia_ms": None,
                "detalhe_erro": f"Host {ip} não respondeu ao ping via Mikrotik"
            }

        # Calcula latência média dos pacotes recebidos
        latencias = []
        for r in received:
            raw = str(r.get('time', '') or r.get('avg-rtt', '') or '')
            ms = FTTHMonitorService._parse_mikrotik_time_to_ms(raw)
            if ms is not None:
                latencias.append(ms)

        latencia_media = round(sum(latencias) / len(latencias), 2) if latencias else None

        return {
            "is_reachable": True,
            "latencia_ms": latencia_media,
            "detalhe_erro": None
        }

    @staticmethod
    def _parse_mikrotik_time_to_ms(time_str: str) -> Optional[float]:
        """
        Converte string de tempo do RouterOS para milissegundos.

        Exemplos de formatos:
          '1ms'   → 1.0
          '345us' → 0.345
          '1.5ms' → 1.5
          '1s'    → 1000.0
        """
        import re
        if not time_str:
            return None
        time_str = time_str.strip().lower()
        try:
            m = re.match(r'([\d.]+)\s*(ms|us|µs|s)', time_str)
            if m:
                value = float(m.group(1))
                unit = m.group(2)
                if unit == 'ms':
                    return value
                elif unit in ('us', 'µs'):
                    return value / 1000.0
                elif unit == 's':
                    return value * 1000.0
            # Tenta apenas número (assumi ms)
            return float(time_str)
        except (ValueError, AttributeError):
            return None


    @staticmethod
    def get_snmp_onu_status(
        olt_ip: str,
        community: str,
        onu_serial: Optional[str],
        port: int = 161
    ) -> Dict[str, Any]:
        """
        Tenta coletar status da ONU via SNMP.
        
        Atualmente retorna DESCONHECIDO se pysnmp não estiver instalado.
        Suporta OIDs genéricos para leitura de potência óptica.
        """
        try:
            from pysnmp.hlapi import (
                getCmd, SnmpEngine, CommunityData, UdpTransportTarget,
                ContextData, ObjectType, ObjectIdentity
            )
            # OID genérico para verificar se a OLT responde (sysDescr)
            iterator = getCmd(
                SnmpEngine(),
                CommunityData(community),
                UdpTransportTarget((olt_ip, port), timeout=2, retries=1),
                ContextData(),
                ObjectType(ObjectIdentity('1.3.6.1.2.1.1.1.0'))  # sysDescr
            )
            error_indication, error_status, error_index, var_binds = next(iterator)
            if error_indication or error_status:
                return {
                    "disponivel": False,
                    "descricao": str(error_indication or error_status),
                    "rx_power": None, "tx_power": None
                }
            return {
                "disponivel": True,
                "descricao": str(var_binds[0][1]),
                "rx_power": None,  # OID específico por fabricante
                "tx_power": None
            }
        except ImportError:
            logger.debug("pysnmp não instalado — SNMP desabilitado")
            return {"disponivel": False, "descricao": "pysnmp não instalado", "rx_power": None, "tx_power": None}
        except Exception as e:
            logger.error(f"Erro SNMP para {olt_ip}: {e}")
            return {"disponivel": False, "descricao": str(e), "rx_power": None, "tx_power": None}

    # =====================================================================
    # COLETA DE STATUS DE UMA ONU
    # =====================================================================

    @staticmethod
    def check_onu(db: Session, contrato: ServicoContratado) -> FTTHMonitorSnapshot:
        """
        Verifica o status de uma ONU e salva um snapshot no banco.

        Fluxo (Solução B com fallback):
        1. Busca o Router associado ao contrato.
        2. Se o Router tiver credenciais Mikrotik API configuradas (ip, usuario, senha):
           a. Verifica se o Mikrotik está respondendo na porta da API (TCP check).
           b. Se acessível, solicita ao Mikrotik que execute o ping internamente.
           c. O resultado (latência, status) é retornado via API RouterOS.
           → Registra metodo_coleta = 'MIKROTIK_API'
        3. Se o Router não tiver credenciais OU o Mikrotik estiver inacessível:
           → Fallback para ping ICMP direto (Solução A).
           → Registra metodo_coleta = 'PING'
        4. Salva snapshot com o resultado e retorna.
        """
        ip = contrato.assigned_ip
        status = "DESCONHECIDO"
        is_reachable = None
        latencia_ms = None
        rx_power = None
        tx_power = None
        temperature = None
        detalhe_erro = None
        metodo_coleta = "PING"

        # ── Se não há IP estático, busca sessão ativa do PPPoE no RADIUS ────────
        if not ip and contrato.pppoe_username:
            try:
                from app.models.radius import RadiusSession
                session = db.query(RadiusSession).filter(
                    RadiusSession.username == contrato.pppoe_username,
                    RadiusSession.empresa_id == contrato.empresa_id,
                    RadiusSession.end_time.is_(None)
                ).order_by(RadiusSession.start_time.desc()).first()
                
                if session:
                    ip = session.ip_address
                else:
                    detalhe_erro = "Sem sessão PPPoE ativa no RADIUS (desconectado)"
            except Exception as e:
                logger.error(f"Erro ao buscar IP dinâmico no RADIUS: {e}")
                detalhe_erro = f"Erro no RADIUS: {e}"

        if ip:
            # ── Tentativa Solução B: ping via API do Mikrotik ───────────────
            router = None
            if contrato.router_id:
                try:
                    router = db.query(Router).filter(
                        Router.id == contrato.router_id,
                        Router.empresa_id == contrato.empresa_id,
                        Router.is_active == True
                    ).first()
                except Exception as e:
                    logger.debug(f"Erro ao buscar Router para contrato {contrato.id}: {e}")

            if router and router.ip and router.usuario and router.senha:
                logger.info(
                    f"[MIKROTIK_API] Contrato {contrato.id} | Router={router.nome} | "
                    f"VPN={router.ip} | Pingando {ip}..."
                )
                ping_result = FTTHMonitorService.ping_via_mikrotik_api(router, ip)
                metodo_coleta = "MIKROTIK_API"
            else:
                # ── Fallback Solução A: ping ICMP direto ─────────────────
                logger.info(
                    f"[PING] Contrato {contrato.id} | Router sem credenciais Mikrotik "
                    f"ou não localizado — usando ping ICMP direto para {ip}..."
                )
                ping_result = FTTHMonitorService.ping_host(ip)
                metodo_coleta = "PING"

            is_reachable = ping_result["is_reachable"]
            latencia_ms = ping_result["latencia_ms"]
            detalhe_erro = ping_result["detalhe_erro"]

            if is_reachable:
                if latencia_ms and latencia_ms > LATENCY_CRITICAL_THRESHOLD:
                    status = "DEGRADADO"
                else:
                    status = "ONLINE"
            else:
                status = "OFFLINE"
        else:
            if not detalhe_erro:
                detalhe_erro = "IP não cadastrado e sem usuário PPPoE configurado"
            status = "OFFLINE"
            is_reachable = False

        # ── Salva snapshot ──────────────────────────────────────────
        snapshot = FTTHMonitorSnapshot(
            contrato_id=contrato.id,
            empresa_id=contrato.empresa_id,
            status=status,
            rx_power=rx_power,
            tx_power=tx_power,
            temperature=temperature,
            latencia_ms=latencia_ms,
            is_reachable=is_reachable,
            metodo_coleta=metodo_coleta,
            detalhe_erro=detalhe_erro,
            ip_verificado=ip,
            timestamp=datetime.utcnow()
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot

    # =====================================================================
    # DASHBOARD / ESTATÍSTICAS
    # =====================================================================

    @staticmethod
    def get_dashboard(db: Session, empresa_id: int) -> Dict[str, Any]:
        """
        Retorna os dados de resumo para o dashboard FTTH.
        """
        # Busca todos os contratos FTTH ativos (tipo_conexao = FIBRA ou com onu_serial)
        contratos_ftth = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == empresa_id,
            ServicoContratado.is_active == True,
            ServicoContratado.status != StatusContrato.CANCELADO,
        ).filter(
            # Considera FTTH se tiver onu_serial OU tipo_conexao == FIBRA
            (ServicoContratado.onu_serial.isnot(None)) |
            (ServicoContratado.tipo_conexao == "FIBRA")
        ).all()

        total_onus = len(contratos_ftth)

        # Busca o status mais recente de cada contrato
        status_counts = {"ONLINE": 0, "OFFLINE": 0, "DEGRADADO": 0, "DESCONHECIDO": 0}
        ultima_atualizacao = None

        for contrato in contratos_ftth:
            ultimo_snapshot = db.query(FTTHMonitorSnapshot).filter(
                FTTHMonitorSnapshot.contrato_id == contrato.id
            ).order_by(FTTHMonitorSnapshot.timestamp.desc()).first()

            if ultimo_snapshot:
                s = ultimo_snapshot.status
                if s in status_counts:
                    status_counts[s] += 1
                else:
                    status_counts["DESCONHECIDO"] += 1

                if ultima_atualizacao is None or ultimo_snapshot.timestamp > ultima_atualizacao:
                    ultima_atualizacao = ultimo_snapshot.timestamp
            else:
                status_counts["DESCONHECIDO"] += 1

        online = status_counts["ONLINE"]
        offline = status_counts["OFFLINE"]
        degradado = status_counts["DEGRADADO"]
        desconhecido = status_counts["DESCONHECIDO"]

        disponibilidade = (online / total_onus * 100) if total_onus > 0 else 0.0

        total_olts = db.query(OLT).filter(
            OLT.empresa_id == empresa_id, OLT.is_active == True
        ).count()

        total_ctos = db.query(CTO).filter(
            CTO.empresa_id == empresa_id, CTO.is_active == True
        ).count()

        return {
            "total_onus": total_onus,
            "onus_online": online,
            "onus_offline": offline,
            "onus_degradado": degradado,
            "onus_desconhecido": desconhecido,
            "disponibilidade_percentual": round(disponibilidade, 2),
            "total_olts": total_olts,
            "total_ctos": total_ctos,
            "ultima_atualizacao": ultima_atualizacao,
        }

    @staticmethod
    def get_onus_status(
        db: Session,
        empresa_id: int,
        status_filter: Optional[str] = None,
        olt_nome_filter: Optional[str] = None,
        cto_nome_filter: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Retorna a lista de ONUs com seu status atual e dados do contrato.
        """
        query = db.query(ServicoContratado, Cliente).join(
            Cliente, ServicoContratado.cliente_id == Cliente.id
        ).filter(
            ServicoContratado.empresa_id == empresa_id,
            ServicoContratado.is_active == True,
            ServicoContratado.status != StatusContrato.CANCELADO,
        ).filter(
            (ServicoContratado.onu_serial.isnot(None)) |
            (ServicoContratado.tipo_conexao == "FIBRA")
        )

        if olt_nome_filter:
            query = query.filter(ServicoContratado.olt_nome.ilike(f"%{olt_nome_filter}%"))
        if cto_nome_filter:
            query = query.filter(ServicoContratado.cto_nome.ilike(f"%{cto_nome_filter}%"))
        if search:
            search_like = f"%{search}%"
            query = query.filter(
                Cliente.nome_razao_social.ilike(search_like) |
                ServicoContratado.onu_serial.ilike(search_like) |
                ServicoContratado.numero_contrato.ilike(search_like)
            )

        total = query.count()
        results = query.offset(skip).limit(limit).all()

        onus = []
        for contrato, cliente in results:
            # Busca o snapshot mais recente
            ultimo = db.query(FTTHMonitorSnapshot).filter(
                FTTHMonitorSnapshot.contrato_id == contrato.id
            ).order_by(FTTHMonitorSnapshot.timestamp.desc()).first()

            onu_status = ultimo.status if ultimo else "DESCONHECIDO"

            # Filtra por status depois de descobrir (evita subquery complexa)
            if status_filter and onu_status != status_filter.upper():
                continue

            onus.append({
                "contrato_id": contrato.id,
                "cliente_nome": cliente.nome_razao_social,
                "numero_contrato": contrato.numero_contrato,
                "endereco_instalacao": contrato.endereco_instalacao,
                "onu_serial": contrato.onu_serial,
                "onu_modelo": contrato.onu_modelo,
                "onu_sinal": contrato.onu_sinal,
                "olt_nome": contrato.olt_nome,
                "olt_pon": contrato.olt_pon,
                "cto_nome": contrato.cto_nome,
                "cto_porta": contrato.cto_porta,
                "assigned_ip": contrato.assigned_ip,
                "pppoe_username": contrato.pppoe_username,
                "coordenadas_gps": contrato.coordenadas_gps,
                "vlan_id": contrato.vlan_id,
                "tipo_conexao": contrato.tipo_conexao.value if contrato.tipo_conexao else None,
                "status": onu_status,
                "latencia_ms": ultimo.latencia_ms if ultimo else None,
                "rx_power": ultimo.rx_power if ultimo else None,
                "tx_power": ultimo.tx_power if ultimo else None,
                "is_reachable": ultimo.is_reachable if ultimo else None,
                "ultima_verificacao": ultimo.timestamp if ultimo else None,
                "metodo_coleta": ultimo.metodo_coleta if ultimo else None,
            })

        return onus, total

    @staticmethod
    def get_onu_history(
        db: Session,
        contrato_id: int,
        empresa_id: int,
        hours: int = 24
    ) -> List[FTTHMonitorSnapshot]:
        """Retorna o histórico de snapshots de uma ONU nas últimas N horas."""
        since = datetime.utcnow() - timedelta(hours=hours)
        return db.query(FTTHMonitorSnapshot).filter(
            FTTHMonitorSnapshot.contrato_id == contrato_id,
            FTTHMonitorSnapshot.empresa_id == empresa_id,
            FTTHMonitorSnapshot.timestamp >= since
        ).order_by(FTTHMonitorSnapshot.timestamp.asc()).all()

    @staticmethod
    def get_alertas(db: Session, empresa_id: int) -> List[Dict[str, Any]]:
        """Retorna ONUs com status OFFLINE ou DEGRADADO (alertas ativos)."""
        onus, _ = FTTHMonitorService.get_onus_status(db, empresa_id, limit=500)
        return [o for o in onus if o["status"] in ("OFFLINE", "DEGRADADO")]

    # =====================================================================
    # OLT CRUD
    # =====================================================================

    @staticmethod
    def _parse_gps(gps_str: Optional[str]) -> Optional[Tuple[float, float]]:
        if not gps_str:
            return None
        try:
            parts = gps_str.split(",")
            if len(parts) == 2:
                return float(parts[0].strip()), float(parts[1].strip())
        except (ValueError, TypeError):
            pass
        return None

    @staticmethod
    def _calc_distance_m(coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        import math
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        # average latitude in radians
        lat_mean = math.radians((lat1 + lat2) / 2.0)
        
        delta_lat = math.radians(lat1 - lat2)
        delta_lon = math.radians(lon1 - lon2)
        
        # R = 6371000 m (Earth's radius)
        x = delta_lon * math.cos(lat_mean)
        y = delta_lat
        
        return math.sqrt(x*x + y*y) * 6371000.0

    @staticmethod
    def list_olts(
        db: Session,
        empresa_id: int,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[OLT]:
        q = db.query(OLT).filter(OLT.empresa_id == empresa_id)
        if search:
            search_like = f"%{search}%"
            q = q.filter(
                (OLT.nome.ilike(search_like)) |
                (OLT.localizacao.ilike(search_like)) |
                (OLT.fabricante.ilike(search_like)) |
                (OLT.modelo.ilike(search_like))
            )
        return q.order_by(OLT.nome).offset(skip).limit(limit).all()

    @staticmethod
    def get_olt(db: Session, olt_id: int, empresa_id: int) -> Optional[OLT]:
        return db.query(OLT).filter(
            OLT.id == olt_id, OLT.empresa_id == empresa_id
        ).first()

    @staticmethod
    def create_olt(db: Session, data: dict, empresa_id: int) -> OLT:
        olt = OLT(**data, empresa_id=empresa_id)
        db.add(olt)
        db.commit()
        db.refresh(olt)
        return olt

    @staticmethod
    def update_olt(db: Session, olt_id: int, empresa_id: int, data: dict) -> Optional[OLT]:
        olt = FTTHMonitorService.get_olt(db, olt_id, empresa_id)
        if not olt:
            return None
        for k, v in data.items():
            setattr(olt, k, v)
        db.commit()
        db.refresh(olt)
        return olt

    @staticmethod
    def delete_olt(db: Session, olt_id: int, empresa_id: int) -> bool:
        olt = FTTHMonitorService.get_olt(db, olt_id, empresa_id)
        if not olt:
            return False
        db.delete(olt)
        db.commit()
        return True

    # =====================================================================
    # CTO CRUD
    # =====================================================================

    @staticmethod
    def list_ctos(
        db: Session,
        empresa_id: int,
        olt_id: Optional[int] = None,
        search: Optional[str] = None,
        proximidade_gps: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[CTO], int]:
        q = db.query(CTO).filter(CTO.empresa_id == empresa_id)
        if olt_id:
            q = q.filter(CTO.olt_id == olt_id)
        
        if search:
            from app.models.ftth import OLT
            q = q.outerjoin(OLT, CTO.olt_id == OLT.id)
            search_like = f"%{search}%"
            q = q.filter(
                (CTO.nome.ilike(search_like)) |
                (CTO.endereco.ilike(search_like)) |
                (CTO.descricao.ilike(search_like)) |
                (OLT.nome.ilike(search_like))
            )

        if proximidade_gps:
            target_coords = FTTHMonitorService._parse_gps(proximidade_gps)
            if target_coords:
                all_ctos = q.all()
                total = len(all_ctos)
                ctos_with_dist = []
                for cto in all_ctos:
                    cto_coords = FTTHMonitorService._parse_gps(cto.coordenadas_gps)
                    if cto_coords:
                        dist = FTTHMonitorService._calc_distance_m(target_coords, cto_coords)
                        cto.distancia_metros = dist
                    else:
                        cto.distancia_metros = None
                    ctos_with_dist.append(cto)
                
                # Sort: CTOs with distance first (sorted by distance ascending), then those without distance
                ctos_with_dist.sort(key=lambda x: (x.distancia_metros is None, x.distancia_metros or 0))
                
                # Paginate in memory
                return ctos_with_dist[skip:skip + limit], total

        total = q.count()
        results = q.order_by(CTO.nome).offset(skip).limit(limit).all()
        return results, total

    @staticmethod
    def get_cto(db: Session, cto_id: int, empresa_id: int) -> Optional[CTO]:
        return db.query(CTO).filter(
            CTO.id == cto_id, CTO.empresa_id == empresa_id
        ).first()

    @staticmethod
    def create_cto(db: Session, data: dict, empresa_id: int) -> CTO:
        cto = CTO(**data, empresa_id=empresa_id)
        db.add(cto)
        db.commit()
        db.refresh(cto)
        return cto

    @staticmethod
    def update_cto(db: Session, cto_id: int, empresa_id: int, data: dict) -> Optional[CTO]:
        cto = FTTHMonitorService.get_cto(db, cto_id, empresa_id)
        if not cto:
            return None
        for k, v in data.items():
            setattr(cto, k, v)
        db.commit()
        db.refresh(cto)
        return cto

    @staticmethod
    def delete_cto(db: Session, cto_id: int, empresa_id: int) -> bool:
        cto = FTTHMonitorService.get_cto(db, cto_id, empresa_id)
        if not cto:
            return False
        db.delete(cto)
        db.commit()
        return True

    # =====================================================================
    # COLETA EM MASSA PARALELA (para o poller)
    # =====================================================================

    @staticmethod
    def poll_all_onus(db: Session, empresa_id: int) -> Dict[str, int]:
        """
        Executa verificação PARALELA de todas as ONUs FTTH ativas de uma empresa.

        Estratégia de paralelismo em dois níveis:

        NÍVEL 1 — Paralelismo entre OLTs/Mikrotiks:
          - Agrupa contratos por nome de OLT.
          - Para cada OLT com Mikrotik API configurada, dispara 1 thread que:
              • Verifica conectividade do Mikrotik (TCP check rápido).
              • Se acessível, abre UMA única conexão API e pinga todas as ONUs
                daquela OLT em sequência (muito mais eficiente que N conexões).
              • Se inacessível, marca todas as ONUs daquela OLT como OFFLINE
                instantaneamente sem esperar timeout por ONU.
          - Todas as OLTs rodam em paralelo (ThreadPoolExecutor).

        NÍVEL 2 — Paralelismo para ICMP puro:
          - Contratos sem OLT configurada ou OLTs sem credenciais Mikrotik
            são verificados com ping ICMP em threads independentes.

        Cada thread tem sua própria Session SQLAlchemy (thread-safe).
        O contador de resultados é protegido por threading.Lock().

        Configurável via variáveis de ambiente:
          FTTH_MAX_OLT_WORKERS   (padrão: 20) — threads por empresa para OLTs
          FTTH_MAX_ICMP_WORKERS  (padrão: 15) — threads para ICMP sem OLT
          FTTH_OLT_THREAD_TIMEOUT (padrão: 90s) — timeout por thread de OLT
        """
        from app.core.database import SessionLocal

        # ── Busca contratos FTTH ativos ────────────────────────────────────
        contratos = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == empresa_id,
            ServicoContratado.is_active == True,
            ServicoContratado.status != StatusContrato.CANCELADO,
        ).filter(
            (ServicoContratado.onu_serial.isnot(None)) |
            (ServicoContratado.tipo_conexao == "FIBRA")
        ).all()

        total = len(contratos)
        resumo = {"ONLINE": 0, "OFFLINE": 0, "DEGRADADO": 0, "DESCONHECIDO": 0, "total": total}

        if total == 0:
            return resumo

        # ── Pré-carrega todos os Roteadores da empresa ───────────────────────────
        routers_por_id: Dict[int, Router] = {
            router.id: router
            for router in db.query(Router).filter(
                Router.empresa_id == empresa_id,
                Router.is_active == True
            ).all()
        }

        # ── Separa contratos em grupos por Roteador e sem-Roteador ──────────────────
        # key: router_id → value: lista de contrato_ids
        por_router: Dict[int, List[int]] = {}
        sem_router: List[int] = []

        for c in contratos:
            if c.router_id and c.router_id in routers_por_id:
                router = routers_por_id[c.router_id]
                if router.ip and router.usuario and router.senha:
                    por_router.setdefault(c.router_id, []).append(c.id)
                    continue
            sem_router.append(c.id)

        # ── Lock para atualizar o resumo de forma thread-safe ─────────────
        lock = threading.Lock()

        def _update_resumo(status: str):
            with lock:
                if status in resumo:
                    resumo[status] += 1
                else:
                    resumo["DESCONHECIDO"] += 1

        # ── Worker: processa TODOS os contratos de um Roteador ────────────────
        def _worker_router(router_id: int, contrato_ids: List[int]):
            """
            Thread que gerencia um Router/Mikrotik completo.
            Abre UMA conexão API e verifica todas as ONUs do grupo.
            """
            thread_db = SessionLocal()
            try:
                router = routers_por_id[router_id]
                statuses = FTTHMonitorService._poll_router_group_via_api(
                    thread_db, router, contrato_ids
                )
                for st in statuses:
                    _update_resumo(st)
            except Exception as e:
                logger.error(f"[THREAD ROUTER={router_id}] Erro inesperado: {e}")
                for _ in contrato_ids:
                    _update_resumo("DESCONHECIDO")
            finally:
                thread_db.close()

        # ── Worker: processa um único contrato via ICMP ───────────────────
        def _worker_icmp(contrato_id: int):
            """
            Thread independente para ping ICMP (fallback ou sem Router).
            """
            thread_db = SessionLocal()
            try:
                contrato = thread_db.query(ServicoContratado).filter_by(
                    id=contrato_id
                ).first()
                if not contrato:
                    _update_resumo("DESCONHECIDO")
                    return
                snapshot = FTTHMonitorService.check_onu(thread_db, contrato)
                _update_resumo(snapshot.status)
            except Exception as e:
                logger.error(f"[THREAD ICMP contrato_id={contrato_id}] Erro: {e}")
                _update_resumo("DESCONHECIDO")
            finally:
                thread_db.close()

        # ── Dispara threads em paralelo ────────────────────────────────────
        n_router_workers = min(MAX_OLT_WORKERS, len(por_router) + 1)
        n_icmp_workers = min(MAX_ICMP_WORKERS, len(sem_router) + 1)
        total_workers = n_router_workers + n_icmp_workers

        logger.info(
            f"[POLL empresa={empresa_id}] {total} ONUs | "
            f"{len(por_router)} Roteadores (API) | {len(sem_router)} sem Router (ICMP) | "
            f"workers Router={n_router_workers} ICMP={n_icmp_workers}"
        )

        futures = []
        with ThreadPoolExecutor(max_workers=total_workers, thread_name_prefix="ftth_poll") as executor:

            # Submete 1 task por Roteador/Mikrotik
            for r_id, c_ids in por_router.items():
                futures.append(executor.submit(_worker_router, r_id, c_ids))

            # Submete tasks individuais para ICMP
            for c_id in sem_router:
                futures.append(executor.submit(_worker_icmp, c_id))

            # Aguarda conclusão com timeout global por thread
            for future in as_completed(futures, timeout=OLT_THREAD_TIMEOUT):
                try:
                    future.result()  # propaga exceptions internas já tratadas
                except Exception as e:
                    logger.error(f"[POLL] Thread encerrada com erro: {e}")

        logger.info(
            f"[POLL empresa={empresa_id}] Concluído → "
            f"Online={resumo['ONLINE']} Offline={resumo['OFFLINE']} "
            f"Degradado={resumo['DEGRADADO']} Desconhecido={resumo['DESCONHECIDO']}"
        )
        return resumo

    @staticmethod
    def _poll_router_group_via_api(
        db: Session,
        router: Router,
        contrato_ids: List[int]
    ) -> List[str]:
        """
        Processa um grupo de contratos de um único Roteador usando UMA conexão
        à API do Mikrotik (reutilizada para todas as ONUs do grupo).

        Fluxo:
          1. TCP check: verifica se o Mikrotik responde na porta da API.
             - Se não responder: marca TODAS as ONUs como OFFLINE imediatamente.
          2. Conecta à API do Mikrotik (UMA vez).
          3. Para cada contrato: executa /ping via conexão existente, salva snapshot.
          4. Fecha a conexão ao final.

        Args:
            db: Session SQLAlchemy exclusiva desta thread.
            router: Instância do modelo Router com credenciais do Mikrotik.
            contrato_ids: Lista de IDs de contratos a verificar.

        Returns:
            Lista de strings com o status de cada contrato (mesma ordem).
        """
        from app.mikrotik.controller import MikrotikController

        host = router.ip
        port = router.porta or 8728
        statuses: List[str] = []

        logger.info(
            f"[Router={router.nome}] Iniciando verificação de {len(contrato_ids)} ONUs "
            f"via API {host}:{port}..."
        )

        # ── ETAPA 1: TCP check ─────────────────────────────────────────────
        if not FTTHMonitorService.check_mikrotik_reachable(host, port, timeout=3.0):
            logger.warning(
                f"[Router={router.nome}] Mikrotik {host}:{port} inacessível — "
                f"marcando {len(contrato_ids)} ONUs como OFFLINE"
            )
            for c_id in contrato_ids:
                contrato = db.query(ServicoContratado).filter_by(id=c_id).first()
                if not contrato:
                    statuses.append("DESCONHECIDO")
                    continue
                snap = FTTHMonitorSnapshot(
                    contrato_id=c_id,
                    empresa_id=contrato.empresa_id,
                    status="OFFLINE",
                    is_reachable=False,
                    metodo_coleta="MIKROTIK_API",
                    detalhe_erro=f"Mikrotik {host}:{port} inacessível (VPN offline ou host inativo)",
                    ip_verificado=contrato.assigned_ip,
                    timestamp=datetime.utcnow(),
                )
                db.add(snap)
                statuses.append("OFFLINE")
            db.commit()
            return statuses

        # ── ETAPA 2: Conecta à API (UMA vez para todo o grupo) ────────────
        from app.core.security import decrypt_password
        try:
            password = decrypt_password(router.senha) if router.senha else ""
        except Exception as e:
            logger.warning(f"Falha ao descriptografar senha do roteador no lote, usando texto plano: {e}")
            password = router.senha

        ctrl = MikrotikController(
            host=host,
            username=router.usuario,
            password=password,
            port=port,
        )
        try:
            ctrl.connect()
            logger.info(f"[Router={router.nome}] Conexão API estabelecida — pingando {len(contrato_ids)} ONUs...")

            for c_id in contrato_ids:
                contrato = db.query(ServicoContratado).filter_by(id=c_id).first()
                if not contrato:
                    statuses.append("DESCONHECIDO")
                    continue

                ip = contrato.assigned_ip
                detalhe_erro = None

                # ── Se não há IP estático, busca sessão ativa do PPPoE no RADIUS ────────
                if not ip and contrato.pppoe_username:
                    try:
                        from app.models.radius import RadiusSession
                        session = db.query(RadiusSession).filter(
                            RadiusSession.username == contrato.pppoe_username,
                            RadiusSession.empresa_id == contrato.empresa_id,
                            RadiusSession.end_time.is_(None)
                        ).order_by(RadiusSession.start_time.desc()).first()
                        
                        if session:
                            ip = session.ip_address
                        else:
                            detalhe_erro = "Sem sessão PPPoE ativa no RADIUS (desconectado)"
                    except Exception as e:
                        logger.error(f"Erro ao buscar IP dinâmico no RADIUS: {e}")
                        detalhe_erro = f"Erro no RADIUS: {e}"

                if not ip:
                    is_radius_offline = (detalhe_erro == "Sem sessão PPPoE ativa no RADIUS (desconectado)")
                    snap = FTTHMonitorSnapshot(
                        contrato_id=c_id,
                        empresa_id=contrato.empresa_id,
                        status="OFFLINE" if is_radius_offline else "DESCONHECIDO",
                        is_reachable=False if is_radius_offline else None,
                        metodo_coleta="MIKROTIK_API",
                        detalhe_erro=detalhe_erro or "IP não cadastrado no contrato",
                        ip_verificado=None,
                        timestamp=datetime.utcnow(),
                    )
                    db.add(snap)
                    statuses.append("OFFLINE" if is_radius_offline else "DESCONHECIDO")
                    continue

                # ── Executa ping via conexão já aberta ─────────────────────
                try:
                    ping_result = FTTHMonitorService._execute_ping_on_ctrl(ctrl, ip)
                except Exception as e:
                    logger.warning(f"[Router={router.nome}] Ping para {ip} falhou: {e}")
                    ping_result = {
                        "is_reachable": False,
                        "latencia_ms": None,
                        "detalhe_erro": f"Erro ping via API: {e}"
                    }

                is_reachable = ping_result["is_reachable"]
                latencia_ms = ping_result["latencia_ms"]
                detalhe_erro = ping_result["detalhe_erro"]

                if is_reachable:
                    status = "DEGRADADO" if (latencia_ms and latencia_ms > LATENCY_CRITICAL_THRESHOLD) else "ONLINE"
                else:
                    status = "OFFLINE"

                snap = FTTHMonitorSnapshot(
                    contrato_id=c_id,
                    empresa_id=contrato.empresa_id,
                    status=status,
                    is_reachable=is_reachable,
                    latencia_ms=latencia_ms,
                    metodo_coleta="MIKROTIK_API",
                    detalhe_erro=detalhe_erro,
                    ip_verificado=ip,
                    timestamp=datetime.utcnow(),
                )
                db.add(snap)
                statuses.append(status)

            db.commit()
            logger.info(f"[Router={router.nome}] Concluído — {len(statuses)} ONUs verificadas.")
            return statuses

        except Exception as e:
            logger.error(f"[Router={router.nome}] Erro na verificação via API: {e}")
            # Tenta salvar OFFLINE para os contratos não processados
            processed = len(statuses)
            remaining = contrato_ids[processed:]
            for c_id in remaining:
                contrato = db.query(ServicoContratado).filter_by(id=c_id).first()
                if contrato:
                    snap = FTTHMonitorSnapshot(
                        contrato_id=c_id,
                        empresa_id=contrato.empresa_id,
                        status="OFFLINE",
                        is_reachable=False,
                        metodo_coleta="MIKROTIK_API",
                        detalhe_erro=f"Erro conexão API: {e}",
                        ip_verificado=contrato.assigned_ip,
                        timestamp=datetime.utcnow(),
                    )
                    db.add(snap)
                statuses.append("OFFLINE")
            try:
                db.commit()
            except Exception:
                db.rollback()
            return statuses
        finally:
            try:
                ctrl.close()
            except Exception:
                pass

    @staticmethod
    def _execute_ping_on_ctrl(ctrl, ip: str, count: int = 3) -> Dict[str, Any]:
        """
        Executa /ping em uma conexão Mikrotik já estabelecida.

        Diferente de ping_via_mikrotik_api(), este método recebe o
        MikrotikController já conectado para reutilização da conexão
        no contexto do _poll_olt_group_via_api().

        Returns:
            dict com: is_reachable (bool), latencia_ms (float|None), detalhe_erro (str|None)
        """
        # Tenta via routeros_api (primário)
        if ctrl._api is not None:
            try:
                resource = ctrl._api.get_resource('ping')
                results = resource.call(
                    **{'address': ip, 'count': str(count), 'interval': '0.2'}
                )
                return FTTHMonitorService._parse_mikrotik_ping_result(results, ip)
            except Exception as e:
                logger.debug(f"_execute_ping_on_ctrl via routeros_api falhou para {ip}: {e}")

        # Fallback: librouteros
        if ctrl._librouteros_api is not None:
            try:
                results = list(ctrl._librouteros_api(
                    '/ping',
                    **{'address': ip, 'count': str(count)}
                ))
                return FTTHMonitorService._parse_mikrotik_ping_result(results, ip)
            except Exception as e:
                logger.debug(f"_execute_ping_on_ctrl via librouteros falhou para {ip}: {e}")
                raise

        return {
            "is_reachable": False,
            "latencia_ms": None,
            "detalhe_erro": "Nenhuma biblioteca RouterOS disponível"
        }
