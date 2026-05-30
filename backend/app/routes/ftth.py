from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db
from app.api import deps
from app.models.models import Usuario, Empresa
from app.schemas.ftth import (
    OLT, OLTCreate, OLTUpdate,
    CTO as CTOSchema, CTOCreate, CTOUpdate,
    FTTHDashboard, ONUStatus, FTTHMonitorSnapshotOut, PingResult
)
from app.services.ftth_monitor_service import FTTHMonitorService

router = APIRouter(prefix="/ftth", tags=["FTTH Monitoramento"])


# ===========================================================================
# DASHBOARD
# ===========================================================================

@router.get("/dashboard", response_model=FTTHDashboard)
def get_dashboard(
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna resumo geral de monitoramento FTTH: KPIs de ONUs online/offline, total de OLTs e CTOs."""
    return FTTHMonitorService.get_dashboard(db, active_empresa.id)


# ===========================================================================
# ONUs / CONTRATOS FTTH
# ===========================================================================

@router.get("/onts")
def list_onts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    status: Optional[str] = Query(None, description="Filtrar por status: ONLINE, OFFLINE, DEGRADADO, DESCONHECIDO"),
    olt_nome: Optional[str] = None,
    cto_nome: Optional[str] = None,
    search: Optional[str] = None,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Lista todas as ONUs/ONTs FTTH da empresa com status de monitoramento em tempo real."""
    onus, total = FTTHMonitorService.get_onus_status(
        db,
        empresa_id=active_empresa.id,
        status_filter=status,
        olt_nome_filter=olt_nome,
        cto_nome_filter=cto_nome,
        search=search,
        skip=skip,
        limit=limit,
    )
    return {"data": onus, "total": total}


@router.get("/onts/{contrato_id}")
def get_ont(
    contrato_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna o status atual e dados de uma ONU específica pelo ID do contrato."""
    from app.models.models import ServicoContratado, Cliente
    contrato = db.query(ServicoContratado).filter(
        ServicoContratado.id == contrato_id,
        ServicoContratado.empresa_id == active_empresa.id,
        ServicoContratado.is_active == True
    ).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    cliente = db.query(Cliente).filter(Cliente.id == contrato.cliente_id).first()

    from app.models.ftth import FTTHMonitorSnapshot
    ultimo = db.query(FTTHMonitorSnapshot).filter(
        FTTHMonitorSnapshot.contrato_id == contrato_id
    ).order_by(FTTHMonitorSnapshot.timestamp.desc()).first()

    return {
        "contrato_id": contrato.id,
        "cliente_nome": cliente.nome_razao_social if cliente else None,
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
        "status": ultimo.status if ultimo else "DESCONHECIDO",
        "latencia_ms": ultimo.latencia_ms if ultimo else None,
        "rx_power": ultimo.rx_power if ultimo else None,
        "tx_power": ultimo.tx_power if ultimo else None,
        "is_reachable": ultimo.is_reachable if ultimo else None,
        "ultima_verificacao": ultimo.timestamp if ultimo else None,
        "metodo_coleta": ultimo.metodo_coleta if ultimo else None,
    }


@router.post("/onts/{contrato_id}/ping", response_model=PingResult)
def manual_ping(
    contrato_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Executa um ping manual na ONU usando o fluxo completo de monitoramento (Mikrotik API, RADIUS, etc)."""
    from app.models.models import ServicoContratado
    contrato = db.query(ServicoContratado).filter(
        ServicoContratado.id == contrato_id,
        ServicoContratado.empresa_id == active_empresa.id,
        ServicoContratado.is_active == True
    ).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    snapshot = FTTHMonitorService.check_onu(db, contrato)

    return PingResult(
        contrato_id=contrato_id,
        ip_testado=snapshot.ip_verificado or "Dinâmico / Não cadastrado",
        is_reachable=snapshot.is_reachable if snapshot.is_reachable is not None else False,
        latencia_ms=snapshot.latencia_ms,
        status=snapshot.status,
        timestamp=snapshot.timestamp
    )


@router.post("/onts/{contrato_id}/poll")
def poll_onu(
    contrato_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Força atualização de status de uma ONU via SNMP/ping e salva snapshot."""
    from app.models.models import ServicoContratado
    contrato = db.query(ServicoContratado).filter(
        ServicoContratado.id == contrato_id,
        ServicoContratado.empresa_id == active_empresa.id,
        ServicoContratado.is_active == True
    ).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    snapshot = FTTHMonitorService.check_onu(db, contrato)
    return {
        "message": "Status atualizado com sucesso",
        "contrato_id": contrato_id,
        "status": snapshot.status,
        "latencia_ms": snapshot.latencia_ms,
        "timestamp": snapshot.timestamp
    }


@router.get("/onts/{contrato_id}/historico", response_model=List[FTTHMonitorSnapshotOut])
def get_onu_historico(
    contrato_id: int,
    horas: int = Query(24, ge=1, le=720, description="Número de horas de histórico (máx 720 = 30 dias)"),
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna o histórico de snapshots de uma ONU para geração de gráficos de sinal."""
    from app.models.models import ServicoContratado
    contrato = db.query(ServicoContratado).filter(
        ServicoContratado.id == contrato_id,
        ServicoContratado.empresa_id == active_empresa.id
    ).first()
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")

    return FTTHMonitorService.get_onu_history(db, contrato_id, active_empresa.id, hours=horas)


# ===========================================================================
# ALERTAS
# ===========================================================================

@router.get("/alertas")
def get_alertas(
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna lista de ONUs com status crítico (OFFLINE ou DEGRADADO)."""
    alertas = FTTHMonitorService.get_alertas(db, active_empresa.id)
    return {"data": alertas, "total": len(alertas)}


# ===========================================================================
# POLLING EM MASSA
# ===========================================================================

@router.post("/poll-all")
def poll_all(
    background_tasks: BackgroundTasks,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Inicia verificação em massa de todas as ONUs FTTH da empresa em background."""
    empresa_id = active_empresa.id

    def _run_poll():
        from app.core.database import SessionLocal
        _db = SessionLocal()
        try:
            FTTHMonitorService.poll_all_onus(_db, empresa_id)
        finally:
            _db.close()

    background_tasks.add_task(_run_poll)
    return {"message": "Verificação em massa iniciada em background"}


# ===========================================================================
# OLTs
# ===========================================================================

@router.get("/olts", response_model=List[OLT])
def list_olts(
    search: Optional[str] = Query(None, description="Termo de busca para nome, localização ou fabricante da OLT"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Lista todas as OLTs cadastradas na empresa com suporte a busca e paginação."""
    return FTTHMonitorService.list_olts(db, active_empresa.id, search=search, skip=skip, limit=limit)


@router.get("/olts/{olt_id}", response_model=OLT)
def get_olt(
    olt_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna uma OLT pelo ID."""
    olt = FTTHMonitorService.get_olt(db, olt_id, active_empresa.id)
    if not olt:
        raise HTTPException(status_code=404, detail="OLT não encontrada")
    return olt


@router.post("/olts", response_model=OLT)
def create_olt(
    olt_data: OLTCreate,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Cadastra uma nova OLT."""
    return FTTHMonitorService.create_olt(db, olt_data.model_dump(), active_empresa.id)


@router.put("/olts/{olt_id}", response_model=OLT)
def update_olt(
    olt_id: int,
    olt_data: OLTUpdate,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Atualiza dados de uma OLT."""
    olt = FTTHMonitorService.update_olt(
        db, olt_id, active_empresa.id, olt_data.model_dump(exclude_unset=True)
    )
    if not olt:
        raise HTTPException(status_code=404, detail="OLT não encontrada")
    return olt


@router.delete("/olts/{olt_id}")
def delete_olt(
    olt_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Remove uma OLT cadastrada."""
    success = FTTHMonitorService.delete_olt(db, olt_id, active_empresa.id)
    if not success:
        raise HTTPException(status_code=404, detail="OLT não encontrada")
    return {"message": "OLT removida com sucesso"}


# ===========================================================================
# CTOs
# ===========================================================================

@router.get("/ctos")
def list_ctos(
    olt_id: Optional[int] = None,
    search: Optional[str] = Query(None, description="Termo de busca para nome, endereço ou descrição da CTO"),
    proximidade_gps: Optional[str] = Query(None, description="Coordenadas GPS do cliente no formato 'lat,lng' para ordenar por proximidade"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=10000),
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Lista CTOs. Pode filtrar por OLT, termo de busca e ordenar por proximidade GPS."""
    ctos, total = FTTHMonitorService.list_ctos(
        db,
        active_empresa.id,
        olt_id=olt_id,
        search=search,
        proximidade_gps=proximidade_gps,
        skip=skip,
        limit=limit
    )
    result = []
    for cto in ctos:
        d = {
            "id": cto.id,
            "nome": cto.nome,
            "olt_id": cto.olt_id,
            "porta_pon": cto.porta_pon,
            "splitter_ratio": cto.splitter_ratio,
            "capacidade": cto.capacidade,
            "coordenadas_gps": cto.coordenadas_gps,
            "endereco": cto.endereco,
            "descricao": cto.descricao,
            "is_active": cto.is_active,
            "empresa_id": cto.empresa_id,
            "created_at": cto.created_at,
            "updated_at": cto.updated_at,
            "olt_nome": cto.olt.nome if cto.olt else None,
            "distancia_metros": getattr(cto, "distancia_metros", None),
        }
        result.append(d)
    return {"data": result, "total": total}


@router.get("/ctos/{cto_id}", response_model=CTOSchema)
def get_cto(
    cto_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna uma CTO pelo ID."""
    cto = FTTHMonitorService.get_cto(db, cto_id, active_empresa.id)
    if not cto:
        raise HTTPException(status_code=404, detail="CTO não encontrada")
    return {
        "id": cto.id,
        "nome": cto.nome,
        "olt_id": cto.olt_id,
        "porta_pon": cto.porta_pon,
        "splitter_ratio": cto.splitter_ratio,
        "capacidade": cto.capacidade,
        "coordenadas_gps": cto.coordenadas_gps,
        "endereco": cto.endereco,
        "descricao": cto.descricao,
        "is_active": cto.is_active,
        "empresa_id": cto.empresa_id,
        "created_at": cto.created_at,
        "updated_at": cto.updated_at,
        "olt_nome": cto.olt.nome if cto.olt else None,
        "distancia_metros": getattr(cto, "distancia_metros", None),
    }


@router.post("/ctos", response_model=CTOSchema)
def create_cto(
    cto_data: CTOCreate,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Cadastra uma nova CTO."""
    # Validar OLT se informada
    if cto_data.olt_id:
        olt = FTTHMonitorService.get_olt(db, cto_data.olt_id, active_empresa.id)
        if not olt:
            raise HTTPException(status_code=404, detail="OLT não encontrada")
    cto = FTTHMonitorService.create_cto(db, cto_data.model_dump(), active_empresa.id)
    return {**cto.__dict__, "olt_nome": cto.olt.nome if cto.olt else None}


@router.put("/ctos/{cto_id}", response_model=CTOSchema)
def update_cto(
    cto_id: int,
    cto_data: CTOUpdate,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Atualiza dados de uma CTO."""
    cto = FTTHMonitorService.update_cto(
        db, cto_id, active_empresa.id, cto_data.model_dump(exclude_unset=True)
    )
    if not cto:
        raise HTTPException(status_code=404, detail="CTO não encontrada")
    return {**cto.__dict__, "olt_nome": cto.olt.nome if cto.olt else None}


@router.delete("/ctos/{cto_id}")
def delete_cto(
    cto_id: int,
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Remove uma CTO cadastrada."""
    success = FTTHMonitorService.delete_cto(db, cto_id, active_empresa.id)
    if not success:
        raise HTTPException(status_code=404, detail="CTO não encontrada")
    return {"message": "CTO removida com sucesso"}


# ===========================================================================
# MAPA
# ===========================================================================

@router.get("/map")
def get_map_data(
    _: bool = Depends(deps.permission_checker("network_manage")),
    current_user: Usuario = Depends(deps.get_current_active_user),
    active_empresa: Empresa = Depends(deps.get_active_empresa),
    db: Session = Depends(get_db)
):
    """Retorna dados de CTOs com coordenadas GPS e status para exibição em mapa."""
    from app.models.ftth import CTO, FTTHMonitorSnapshot
    from app.models.models import ServicoContratado
    ctos = db.query(CTO).filter(
        CTO.empresa_id == active_empresa.id,
        CTO.coordenadas_gps.isnot(None),
        CTO.is_active == True
    ).all()

    result = []
    for cto in ctos:
        # Conta quantas ONUs estão conectadas a esta CTO (pelo nome)
        onus_count = db.query(ServicoContratado).filter(
            ServicoContratado.empresa_id == active_empresa.id,
            ServicoContratado.cto_nome == cto.nome,
            ServicoContratado.is_active == True
        ).count()

        # Conta ONUs offline nesta CTO
        onus_ids = db.query(ServicoContratado.id).filter(
            ServicoContratado.empresa_id == active_empresa.id,
            ServicoContratado.cto_nome == cto.nome,
            ServicoContratado.is_active == True
        ).all()

        offline_count = 0
        for (cid,) in onus_ids:
            ultimo = db.query(FTTHMonitorSnapshot).filter(
                FTTHMonitorSnapshot.contrato_id == cid
            ).order_by(FTTHMonitorSnapshot.timestamp.desc()).first()
            if ultimo and ultimo.status == "OFFLINE":
                offline_count += 1

        lat, lng = None, None
        if cto.coordenadas_gps:
            parts = cto.coordenadas_gps.split(",")
            if len(parts) == 2:
                try:
                    lat, lng = float(parts[0].strip()), float(parts[1].strip())
                except ValueError:
                    pass

        result.append({
            "id": cto.id,
            "nome": cto.nome,
            "lat": lat,
            "lng": lng,
            "olt_nome": cto.olt.nome if cto.olt else None,
            "splitter_ratio": cto.splitter_ratio,
            "capacidade": cto.capacidade,
            "onus_count": onus_count,
            "offline_count": offline_count,
            "saturacao_percentual": round(onus_count / cto.capacidade * 100, 1) if cto.capacidade else None,
        })

    return {"data": result}
