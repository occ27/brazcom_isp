from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.core.security import decode_access_token
from app.crud import crud_cliente, crud_servico_contratado, crud_nfcom, crud_usuario, crud_empresa
from app.schemas.cliente import ClienteResponse
from app.routes.auth import get_current_active_user
from app.routes.client_auth import get_current_cliente as get_current_cliente_auth
from app.models.models import Usuario, Cliente
from app.api import deps
from app.services.ticket_service import TicketService
from app.schemas.ticket import TicketCreate
from pydantic import BaseModel
from app.schemas.empresa import EmpresaResponse

# Schema simplificado para criação de tickets no portal do cliente
class TicketCreateCliente(BaseModel):
    titulo: str
    descricao: str
    prioridade: str = "NORMAL"
    categoria: str = "SUPORTE"

# Schema simplificado para atualização de dados do cliente no portal
class ClienteUpdatePortal(BaseModel):
    email: str = None
    telefone: str = None

router = APIRouter(prefix="/client-portal", tags=["Portal do Cliente"])

# Dependency para obter cliente logado (suporta tanto tokens de cliente quanto usuários admin com cliente_id)
def get_current_cliente(
    request: Request,
    db: Session = Depends(get_db)
) -> Cliente:
    """Obtém o cliente associado ao usuário/token logado."""
    from app.core.security import decode_access_token
    from app.crud import crud_cliente

    # Extrair token do header Authorization
    authorization = request.headers.get("Authorization")
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token não fornecido"
        )

    token = authorization.split(" ")[1]

    from app.core.security import decode_access_token
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    # Verificar tipo de token
    token_type = payload.get("type")

    if token_type == "cliente":
        # Token de cliente
        cliente_id = payload.get("sub")
        if cliente_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token de cliente inválido"
            )

        cliente = crud_cliente.get_cliente(db, cliente_id=int(cliente_id))
        if cliente is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cliente não encontrado"
            )
        return cliente

    else:
        # Token sem tipo especificado - tentar como cliente primeiro (para compatibilidade)
        cliente_id = payload.get("sub")
        if cliente_id:
            cliente = crud_cliente.get_cliente(db, cliente_id=int(cliente_id))
            if cliente:
                return cliente

        # Se não encontrou cliente, tentar como usuário admin
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        # Buscar usuário
        usuario = crud_usuario.get_usuario(db, usuario_id=int(user_id))
        if usuario is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário não encontrado"
            )

        # Verificar se usuário tem cliente_id
        if hasattr(usuario, 'cliente_id') and usuario.cliente_id:
            cliente = crud_cliente.get_cliente(db, cliente_id=usuario.cliente_id)
            if cliente:
                return cliente

        # Fallback para relacionamento antigo se existir
        if hasattr(usuario, 'cliente') and usuario.cliente:
            return usuario.cliente

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Usuário não está associado a um cliente"
    )

@router.get("/cliente", response_model=ClienteResponse)
def get_cliente_info(
    cliente: Cliente = Depends(get_current_cliente)
):
    """Retorna informações do cliente logado."""
    return cliente

@router.get("/servicos")
def get_servicos_contratados(
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Retorna serviços contratados pelo cliente."""
    servicos = crud_servico_contratado.get_servicos_by_cliente(db, cliente_id=cliente.id)
    return [
        {
            "id": s.id,
            "servico_nome": s.servico.nome if s.servico else "Serviço",
            "status": s.status,
            "valor_mensal": float(s.valor_mensal) if s.valor_mensal else 0,
            "data_contratacao": s.created_at.isoformat() if s.created_at else None
        }
        for s in servicos
    ]

@router.get("/faturas")
def get_faturas(
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Retorna faturas do cliente."""
    # Por enquanto retorna NFComs como faturas
    nfcoms = crud_nfcom.get_nfcoms_by_cliente(db, cliente_id=cliente.id)
    return [
        {
            "id": nf.id,
            "numero": f"NF{nf.id:06d}",
            "valor_total": float(nf.valor_total) if nf.valor_total else 0,
            "data_emissao": nf.created_at.isoformat() if nf.created_at else None,
            "data_vencimento": nf.data_vencimento.isoformat() if nf.data_vencimento else None,
            "status": nf.status or "Pendente"
        }
        for nf in nfcoms[:10]  # Últimas 10
    ]

@router.get("/tickets")
def get_tickets_cliente(
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Retorna tickets de suporte do cliente."""
    # Busca tickets do cliente usando o TicketService
    tickets = TicketService.get_tickets(
        db=db,
        empresa_id=cliente.empresa_id,  # Assumindo que cliente tem empresa_id
        cliente_id=cliente.id
    )
    return tickets

@router.post("/tickets")
def create_ticket_cliente(
    ticket_data: TicketCreateCliente,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Cria um novo ticket de suporte para o cliente."""
    # Tentar obter current_user se disponível (para usuários admin), senão usar cliente
    criado_por_id = None
    try:
        from app.routes.auth import get_current_active_user
        current_user = get_current_active_user(db=db)
        criado_por_id = current_user.id
    except:
        # Se não conseguir obter usuário admin, usar o próprio cliente como criado_por
        criado_por_id = cliente.id

    # Converte os dados para o formato esperado pelo TicketService
    ticket_create_data = TicketCreate(
        titulo=ticket_data.titulo,
        descricao=ticket_data.descricao,
        prioridade=ticket_data.prioridade,
        categoria=ticket_data.categoria,
        cliente_id=cliente.id
    )

    # Cria o ticket usando o TicketService
    ticket = TicketService.create_ticket(
        db=db,
        ticket_data=ticket_create_data,
        empresa_id=cliente.empresa_id,  # Assumindo que cliente tem empresa_id
        criado_por_id=criado_por_id
    )

    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar ticket"
        )

    return ticket

@router.put("/cliente")
def update_cliente_info(
    cliente_data: ClienteUpdatePortal,
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Atualiza informações do cliente."""
    # Atualiza apenas os campos permitidos no portal
    update_data = {}
    if cliente_data.email is not None:
        update_data["email"] = cliente_data.email
    if cliente_data.telefone is not None:
        update_data["telefone"] = cliente_data.telefone

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhum campo para atualizar"
        )

    # Atualiza o cliente no banco de dados
    for field, value in update_data.items():
        setattr(cliente, field, value)

    db.commit()
    db.refresh(cliente)

    return cliente


@router.get("/empresa", response_model=EmpresaResponse)
def get_empresa_for_cliente(
    cliente: Cliente = Depends(get_current_cliente),
    db: Session = Depends(get_db)
):
    """Retorna informações da empresa associada ao cliente logado."""
    empresa = crud_empresa.get_empresa(db, empresa_id=cliente.empresa_id)
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    return empresa