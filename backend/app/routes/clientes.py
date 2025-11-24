from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, String
from typing import List

from app.core.database import get_db
from app.crud import crud_cliente, crud_empresa
from app.schemas.cliente import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
    ClienteListResponse,
)
from app.routes.auth import get_current_active_user
from app.models.models import Usuario
from app.models.models import EmpresaCliente

router = APIRouter(prefix="/clientes", tags=["Clientes"])

@router.post("/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED)
def create_cliente(
    cliente: ClienteCreate,
    empresa_id: int, # Passado como query parameter ou no body
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Cria um novo cliente para uma empresa."""
    # Verifica se a empresa existe
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verifica permissão (se o usuário pertence à empresa)
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if empresa_id not in user_empresas_ids and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão para adicionar clientes a esta empresa")

    # DEBUG: log incoming payload enderecos
    try:
        # print for server console logs
        print(f"DEBUG route create_cliente: empresa_id={empresa_id}, received enderecos={getattr(cliente, 'enderecos', None)}")
    except Exception:
        pass

    # Cria cliente e associação; informa created_by_user_id para auditoria
    return crud_cliente.create_cliente(db=db, cliente=cliente, empresa_id=empresa_id, created_by_user_id=current_user.id)

@router.get("/empresa/{empresa_id}", response_model=ClienteListResponse)
def read_clientes(
    empresa_id: int,
    skip: int = 0,
    limit: int = 100,
    q: str = None, # Adicionar parâmetro de busca
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista os clientes de uma empresa específica."""
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verifica permissão
    user_empresas_ids = [e.empresa_id for e in current_user.empresas]
    if empresa_id not in user_empresas_ids and not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Usuário não tem permissão para ver os clientes desta empresa")

    # Buscar clientes com paginação e também contar o total (mesmos filtros)
    clients = crud_cliente.get_clientes_by_empresa(db, empresa_id=empresa_id, q=q, skip=skip, limit=limit)

    # Contar total de clientes que correspondem ao filtro (sem offset/limit)
    from sqlalchemy import select
    # Use scalar_subquery() so the Select is passed explicitly to IN() (avoids SAWarning)
    subquery = select(crud_cliente.EmpresaCliente.cliente_id).where(crud_cliente.EmpresaCliente.empresa_id == empresa_id).scalar_subquery()
    
    total_query = (
        db.query(crud_cliente.Cliente)
        .filter(
            or_(
                # Clientes com associações EmpresaCliente
                crud_cliente.Cliente.id.in_(subquery),
                # Clientes legacy (diretamente associados via empresa_id)
                crud_cliente.Cliente.empresa_id == empresa_id
            )
        )
    )
    if q:
        total_query = total_query.filter(
            or_(
                crud_cliente.Cliente.nome_razao_social.ilike(f"%{q}%"),
                crud_cliente.Cliente.cpf_cnpj.ilike(f"%{q}%"),
                crud_cliente.Cliente.id.cast(String).ilike(f"%{q}%"),
                crud_cliente.Cliente.email.ilike(f"%{q}%"),
                crud_cliente.Cliente.telefone.ilike(f"%{q}%")
            )
        )
    total = total_query.count()

    # Normalizar retorno: garantir que cada cliente tenha um campo `enderecos` (lista)
    result = []
    for c in clients:
        # base fields expected by ClienteResponse
        client_dict = {
            'id': c.id,
            'empresa_id': getattr(c, 'empresa_id', None),
            'nome_razao_social': getattr(c, 'nome_razao_social', None),
            'cpf_cnpj': getattr(c, 'cpf_cnpj', None),
            'tipo_pessoa': getattr(c, 'tipo_pessoa', None),
            'ind_ie_dest': getattr(c, 'ind_ie_dest', None),
            'inscricao_estadual': getattr(c, 'inscricao_estadual', None),
            'email': getattr(c, 'email', None),
            'telefone': getattr(c, 'telefone', None),
            'is_active': getattr(c, 'is_active', True),
            'created_at': getattr(c, 'created_at', None),
            'updated_at': getattr(c, 'updated_at', None),
        }

        # Buscar endereços da empresa específica para este cliente
        enderecos = []
        empresa_enderecos = (
            db.query(crud_cliente.EmpresaClienteEndereco)
            .join(crud_cliente.EmpresaCliente, crud_cliente.EmpresaCliente.id == crud_cliente.EmpresaClienteEndereco.empresa_cliente_id)
            .filter(
                crud_cliente.EmpresaCliente.cliente_id == c.id,
                crud_cliente.EmpresaCliente.empresa_id == empresa_id
            )
            .all()
        )
        for e in empresa_enderecos:
            enderecos.append({
                'id': e.id,
                'descricao': getattr(e, 'descricao', None),
                'endereco': getattr(e, 'endereco', None),
                'numero': getattr(e, 'numero', None),
                'complemento': getattr(e, 'complemento', None),
                'bairro': getattr(e, 'bairro', None),
                'municipio': getattr(e, 'municipio', None),
                'uf': getattr(e, 'uf', None),
                'cep': getattr(e, 'cep', None),
                'codigo_ibge': getattr(e, 'codigo_ibge', None),
                'is_principal': getattr(e, 'is_principal', None),
            })

        client_dict['enderecos'] = enderecos
        result.append(client_dict)

    return { 'total': total, 'clientes': result }


@router.put("/{cliente_id}", response_model=ClienteResponse)
async def update_cliente(
    cliente_id: int,
    cliente_in: ClienteUpdate,
    empresa_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Verifica empresa
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verificar associação
    assoc = crud_cliente.get_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id)
    if not assoc:
        raise HTTPException(status_code=404, detail="Associação empresa-cliente não encontrada")

    # Permissão de edição: somente o usuário que criou a associação (ou superuser)
    if not current_user.is_superuser and assoc.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o usuário criador da associação pode editar os dados deste cliente nesta empresa")

    db_cliente = crud_cliente.get_cliente(db, cliente_id=cliente_id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # DEBUG: inspect raw payload to check for 'enderecos'
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    try:
        print(f"DEBUG route update_cliente: cliente_id={cliente_id}, raw_enderecos={raw.get('enderecos')}")
    except Exception:
        pass

    # Update basic cliente fields
    updated = crud_cliente.update_cliente(db=db, db_obj=db_cliente, obj_in=cliente_in)

    # If payload includes enderecos, process them for the empresa-client association
    enderecos = raw.get('enderecos') if isinstance(raw, dict) else None
    if enderecos is not None:
        # Ensure association exists
        assoc = crud_cliente.get_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id)
        if not assoc:
            # create association if missing
            assoc = crud_cliente.get_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id)
        # Process each endereco: create if no id, update if id present
        for addr in enderecos:
            try:
                addr_id = addr.get('id')
            except Exception:
                addr_id = None
            try:
                if addr_id:
                    crud_cliente.update_endereco_for_empresa_cliente(db, endereco_id=addr_id, empresa_id=empresa_id, cliente_id=cliente_id, update_data=addr)
                else:
                    crud_cliente.create_endereco_for_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id, endereco_data=addr)
            except Exception as e:
                # Log and continue
                try:
                    print(f"DEBUG route update_cliente: error processing endereco {addr} -> {e}")
                except Exception:
                    pass

    return updated

@router.delete("/{cliente_id}")
def delete_cliente(
    cliente_id: int,
    empresa_id: int,
    remove_orphan_cliente: bool = False,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    # Verifica empresa
    db_empresa = crud_empresa.get_empresa(db, empresa_id=empresa_id)
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    # Verificar associação
    assoc = crud_cliente.get_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id)
    if not assoc:
        raise HTTPException(status_code=404, detail="Associação empresa-cliente não encontrada")

    # Permissão de deleção: somente o usuário que criou a associação (ou superuser)
    if not current_user.is_superuser and assoc.created_by_user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o usuário criador da associação pode deletar esta associação")

    # Se superuser e remove_orphan_cliente True: deletar Cliente global
    if current_user.is_superuser and remove_orphan_cliente:
        db_cliente = crud_cliente.get_cliente(db, cliente_id=cliente_id)
        if not db_cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        crud_cliente.delete_cliente(db, db_cliente)
        return {"detail": "Cliente removido globalmente"}

    # Caso padrão: deletar apenas a associação empresa_cliente
    try:
        res = crud_cliente.delete_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id, remove_orphan_cliente=remove_orphan_cliente)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not res:
        raise HTTPException(status_code=404, detail="Associação não encontrada")
    return {"detail": "Associação removida"}


@router.get("/{cliente_id}", response_model=ClienteResponse)
def read_cliente(
    cliente_id: int,
    empresa_id: int = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Obtém um cliente pelo ID. Se `empresa_id` for fornecido valida associação/permissão."""
    db_cliente = crud_cliente.get_cliente(db, cliente_id=cliente_id)
    if not db_cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    # Se empresa_id foi fornecido, verificar permissão e associação
    if empresa_id is not None:
        # Verifica se usuário tem acesso à empresa
        user_empresas_ids = [e.empresa_id for e in current_user.empresas]
        if not current_user.is_superuser and empresa_id not in user_empresas_ids:
            raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar recursos desta empresa")
        assoc = crud_cliente.get_empresa_cliente(db, empresa_id=empresa_id, cliente_id=cliente_id)
        if not assoc:
            raise HTTPException(status_code=404, detail="Associação empresa-cliente não encontrada")

    else:
        # Se não foi fornecida empresa, garantir que o usuário tenha alguma associação com o cliente
        if not current_user.is_superuser:
            user_empresas_ids = [e.empresa_id for e in current_user.empresas]
            found = False
            for eid in user_empresas_ids:
                if crud_cliente.get_empresa_cliente(db, empresa_id=eid, cliente_id=cliente_id):
                    found = True
                    break
            if not found:
                raise HTTPException(status_code=403, detail="Usuário não tem permissão para acessar este cliente")

    # Montar o dicionário com endereços (legacy ou por associação) para corresponder ao ClienteResponse
    client_dict = {
        'id': db_cliente.id,
        'empresa_id': getattr(db_cliente, 'empresa_id', None),
        'nome_razao_social': getattr(db_cliente, 'nome_razao_social', None),
        'cpf_cnpj': getattr(db_cliente, 'cpf_cnpj', None),
        'tipo_pessoa': getattr(db_cliente, 'tipo_pessoa', None),
        'ind_ie_dest': getattr(db_cliente, 'ind_ie_dest', None),
        'inscricao_estadual': getattr(db_cliente, 'inscricao_estadual', None),
        'email': getattr(db_cliente, 'email', None),
        'telefone': getattr(db_cliente, 'telefone', None),
        'is_active': getattr(db_cliente, 'is_active', True),
        'created_at': getattr(db_cliente, 'created_at', None),
        'updated_at': getattr(db_cliente, 'updated_at', None),
    }

    # Buscar endereços da empresa específica para este cliente
    enderecos = []
    if empresa_id is not None:
        empresa_enderecos = (
            db.query(crud_cliente.EmpresaClienteEndereco)
            .join(crud_cliente.EmpresaCliente, crud_cliente.EmpresaCliente.id == crud_cliente.EmpresaClienteEndereco.empresa_cliente_id)
            .filter(
                crud_cliente.EmpresaCliente.cliente_id == db_cliente.id,
                crud_cliente.EmpresaCliente.empresa_id == empresa_id
            )
            .all()
        )
        for e in empresa_enderecos:
            enderecos.append({
                'id': e.id,
                'descricao': getattr(e, 'descricao', None),
                'endereco': getattr(e, 'endereco', None),
                'numero': getattr(e, 'numero', None),
                'complemento': getattr(e, 'complemento', None),
                'bairro': getattr(e, 'bairro', None),
                'municipio': getattr(e, 'municipio', None),
                'uf': getattr(e, 'uf', None),
                'cep': getattr(e, 'cep', None),
                'codigo_ibge': getattr(e, 'codigo_ibge', None),
                'is_principal': getattr(e, 'is_principal', None),
            })
    else:
        # Se não foi especificada empresa, buscar endereços de todas as associações do usuário
        user_empresas_ids = [e.empresa_id for e in current_user.empresas] if not current_user.is_superuser else []
        if current_user.is_superuser:
            # Superuser vê todos os endereços
            empresa_enderecos = (
                db.query(crud_cliente.EmpresaClienteEndereco)
                .join(crud_cliente.EmpresaCliente, crud_cliente.EmpresaCliente.id == crud_cliente.EmpresaClienteEndereco.empresa_cliente_id)
                .filter(crud_cliente.EmpresaCliente.cliente_id == db_cliente.id)
                .all()
            )
        else:
            # Usuário normal vê apenas endereços das empresas que tem acesso
            empresa_enderecos = (
                db.query(crud_cliente.EmpresaClienteEndereco)
                .join(crud_cliente.EmpresaCliente, crud_cliente.EmpresaCliente.id == crud_cliente.EmpresaClienteEndereco.empresa_cliente_id)
                .filter(
                    crud_cliente.EmpresaCliente.cliente_id == db_cliente.id,
                    crud_cliente.EmpresaCliente.empresa_id.in_(user_empresas_ids)
                )
                .all()
            )
        for e in empresa_enderecos:
            enderecos.append({
                'id': e.id,
                'descricao': getattr(e, 'descricao', None),
                'endereco': getattr(e, 'endereco', None),
                'numero': getattr(e, 'numero', None),
                'complemento': getattr(e, 'complemento', None),
                'bairro': getattr(e, 'bairro', None),
                'municipio': getattr(e, 'municipio', None),
                'uf': getattr(e, 'uf', None),
                'cep': getattr(e, 'cep', None),
                'codigo_ibge': getattr(e, 'codigo_ibge', None),
                'is_principal': getattr(e, 'is_principal', None),
            })

    client_dict['enderecos'] = enderecos
    return client_dict