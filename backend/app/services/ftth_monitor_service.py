"""
Serviço de Monitoramento FTTH

Responsável por:
- Verificar conectividade de ONUs via ICMP (ping)
- Coletar parâmetros ópticos via SNMP (quando disponível)
- Gerar snapshots de monitoramento para histórico e alertas
"""
import socket
import struct
import time
import logging
import os
import subprocess
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.models import ServicoContratado, Cliente, StatusContrato
from app.models.ftth import OLT, CTO, FTTHMonitorSnapshot

logger = logging.getLogger(__name__)

# Limiar de sinal óptico para considerar "degradado" (em dBm)
RX_POWER_WARNING_THRESHOLD = -25.0   # Abaixo disso = alerta
RX_POWER_CRITICAL_THRESHOLD = -28.0  # Abaixo disso = crítico/offline

# Latência máxima para considerar link ok (ms)
LATENCY_WARNING_THRESHOLD = 100.0
LATENCY_CRITICAL_THRESHOLD = 500.0


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
    # SNMP (básico — não requer dependência extra no MVP)
    # =====================================================================

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
        
        Fluxo:
        1. Tenta fazer ping no IP atribuído ao contrato
        2. Se tiver OLT com SNMP configurado, tenta coletar parâmetros ópticos
        3. Salva snapshot com o resultado
        4. Retorna o snapshot criado
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

        # 1. Ping
        if ip:
            ping_result = FTTHMonitorService.ping_host(ip)
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
            detalhe_erro = "IP não cadastrado no contrato"

        # 2. Snapshot
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
    ) -> List[CTO]:
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
                return ctos_with_dist[skip:skip + limit]

        return q.order_by(CTO.nome).offset(skip).limit(limit).all()

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
    # COLETA EM MASSA (para o poller)
    # =====================================================================

    @staticmethod
    def poll_all_onus(db: Session, empresa_id: int) -> Dict[str, int]:
        """
        Executa verificação de todas as ONUs FTTH ativas de uma empresa.
        Retorna um resumo com totais por status.
        """
        contratos = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == empresa_id,
            ServicoContratado.is_active == True,
            ServicoContratado.status != StatusContrato.CANCELADO,
        ).filter(
            (ServicoContratado.onu_serial.isnot(None)) |
            (ServicoContratado.tipo_conexao == "FIBRA")
        ).all()

        resumo = {"ONLINE": 0, "OFFLINE": 0, "DEGRADADO": 0, "DESCONHECIDO": 0, "total": len(contratos)}

        for contrato in contratos:
            try:
                snapshot = FTTHMonitorService.check_onu(db, contrato)
                s = snapshot.status
                if s in resumo:
                    resumo[s] += 1
                else:
                    resumo["DESCONHECIDO"] += 1
            except Exception as e:
                logger.error(f"Erro ao verificar ONU do contrato {contrato.id}: {e}")
                resumo["DESCONHECIDO"] += 1

        return resumo
