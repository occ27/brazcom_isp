from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app import crud
from app.api import deps
from app.models import models
from app.schemas.network import (
    RouterInterfaceResponse, RouterInterfaceCreate, RouterInterfaceUpdate,
    InterfaceIPAddressResponse, InterfaceIPAddressCreate, InterfaceIPAddressUpdate,
    IPClassResponse, IPClassCreate, IPClassUpdate,
    InterfaceIPClassAssignmentCreate, InterfaceIPClassAssignmentResponse,
    RouterWithInterfacesResponse
)

router = APIRouter(prefix="/network", tags=["Network"])

# Rotas para Router Interfaces
@router.post("/routers/{router_id}/interfaces/", response_model=RouterInterfaceResponse)
def create_router_interface(
    *,
    db: Session = Depends(deps.get_db),
    router_id: int,
    interface_in: RouterInterfaceCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Criar uma nova interface para um router.
    """
    # Verificar se o router pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Router não encontrado")

    return crud.crud_network.create_router_interface(db=db, interface=interface_in, router_id=router_id)

@router.get("/routers/{router_id}/interfaces/", response_model=List[RouterInterfaceResponse])
def read_router_interfaces(
    *,
    db: Session = Depends(deps.get_db),
    router_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Buscar todas as interfaces de um router.
    """
    # Verificar se o router pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Router não encontrado")

    interfaces = crud.crud_network.get_router_interfaces_by_router(db=db, router_id=router_id)
    return interfaces

@router.put("/interfaces/{interface_id}", response_model=RouterInterfaceResponse)
def update_router_interface(
    *,
    db: Session = Depends(deps.get_db),
    interface_id: int,
    interface_in: RouterInterfaceUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Atualizar uma interface.
    """
    interface = crud.crud_network.get_router_interface(db=db, interface_id=interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    # Verificar se o router da interface pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return crud.crud_network.update_router_interface(db=db, db_interface=interface, interface_in=interface_in)

@router.delete("/interfaces/{interface_id}", response_model=RouterInterfaceResponse)
def delete_router_interface(
    *,
    db: Session = Depends(deps.get_db),
    interface_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    confirm: bool = False,
):
    """
    Deletar uma interface.

    ⚠️ IMPACTO DA OPERAÇÃO:
    - Remove a interface do sistema permanentemente
    - Remove todas as atribuições de classes IP associadas
    - Pode afetar configurações de rede ativas no router
    - Interfaces sincronizadas podem ser recriadas na próxima sincronização

    🔒 CONFIRMAÇÃO OBRIGATÓRIA:
    - Use confirm=true para confirmar a exclusão
    - Sem confirmação, retorna apenas informações do impacto
    """
    interface = crud.crud_network.get_router_interface(db=db, interface_id=interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    # Verificar se o router da interface pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Verificar impacto da exclusão
    ip_classes_assigned = crud.crud_network.get_ip_classes_by_interface(db=db, interface_id=interface_id)
    ip_addresses = crud.crud_network.get_ip_addresses_by_interface(db=db, interface_id=interface_id)

    impact_info = {
        "interface_name": interface.nome,
        "router_name": router.nome,
        "ip_classes_assigned": len(ip_classes_assigned),
        "ip_addresses_configured": len(ip_addresses),
        "warning": "Esta operação é irreversível e pode afetar configurações de rede ativas!"
    }

    # Se não confirmado, retornar informações do impacto
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Confirmação necessária para exclusão",
                "impact": impact_info,
                "message": "Use confirm=true para confirmar a exclusão desta interface",
                "confirmation_required": True
            }
        )

    # Confirmado - executar exclusão
    return crud.crud_network.remove_router_interface(db=db, db_interface=interface)

# Rotas para Endereços IP das Interfaces
@router.post("/interfaces/{interface_id}/ip-addresses/", response_model=InterfaceIPAddressResponse)
def create_interface_ip_address(
    *,
    db: Session = Depends(deps.get_db),
    interface_id: int,
    ip_address_in: InterfaceIPAddressCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Criar um novo endereço IP para uma interface.
    """
    interface = crud.crud_network.get_router_interface(db=db, interface_id=interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    # Verificar se o router da interface pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return crud.crud_network.create_interface_ip_address(db=db, ip_address=ip_address_in, interface_id=interface_id)

@router.get("/interfaces/{interface_id}/ip-addresses/", response_model=List[InterfaceIPAddressResponse])
def read_interface_ip_addresses(
    *,
    db: Session = Depends(deps.get_db),
    interface_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Buscar todos os endereços IP de uma interface.
    """
    interface = crud.crud_network.get_router_interface(db=db, interface_id=interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    # Verificar se o router da interface pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return crud.crud_network.get_ip_addresses_by_interface(db=db, interface_id=interface_id)

# Rotas para Classes IP
@router.post("/ip-classes/", response_model=IPClassResponse)
def create_ip_class(
    *,
    db: Session = Depends(deps.get_db),
    ip_class_in: IPClassCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Criar uma nova classe IP para a empresa do usuário.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    return crud.crud_network.create_ip_class(db=db, ip_class=ip_class_in, empresa_id=empresa_id)

@router.get("/ip-classes/", response_model=List[IPClassResponse])
def read_ip_classes(
    *,
    db: Session = Depends(deps.get_db),
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Buscar todas as classes IP da empresa do usuário.
    """
    empresa_id = current_user.active_empresa_id or 2  # Usar 2 como fallback
    return crud.crud_network.get_ip_classes_by_empresa(db=db, empresa_id=empresa_id)

@router.put("/ip-classes/{class_id}", response_model=IPClassResponse)
def update_ip_class(
    *,
    db: Session = Depends(deps.get_db),
    class_id: int,
    ip_class_in: IPClassUpdate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Atualizar uma classe IP.
    """
    ip_class = crud.crud_network.get_ip_class(db=db, class_id=class_id)
    if not ip_class:
        raise HTTPException(status_code=404, detail="Classe IP não encontrada")

    # Verificar se a classe IP pertence à empresa do usuário
    if ip_class.empresa_id != current_user.active_empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return crud.crud_network.update_ip_class(db=db, db_class=ip_class, class_in=ip_class_in)

@router.delete("/ip-classes/{class_id}", response_model=IPClassResponse)
def delete_ip_class(
    *,
    db: Session = Depends(deps.get_db),
    class_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    confirm: bool = False,
):
    """
    Deletar uma classe IP.

    ⚠️ IMPACTO CRÍTICO DA OPERAÇÃO:
    - Remove a classe IP permanentemente do sistema
    - Remove todas as atribuições desta classe IP de interfaces
    - Pode desconectar redes ativas no router MikroTik
    - Afeta todas as interfaces que usam esta classe IP
    - Configurações de IP, gateway e DNS podem ser perdidas

    🔒 CONFIRMAÇÃO OBRIGATÓRIA:
    - Use confirm=true para confirmar a exclusão
    - Sem confirmação, retorna informações detalhadas do impacto
    """
    ip_class = crud.crud_network.get_ip_class(db=db, class_id=class_id)
    if not ip_class:
        raise HTTPException(status_code=404, detail="Classe IP não encontrada")

    # Verificar se a classe IP pertence à empresa do usuário
    if ip_class.empresa_id != current_user.active_empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Verificar impacto da exclusão
    interfaces_assigned = crud.crud_network.get_interfaces_by_ip_class(db=db, class_id=class_id)

    impact_info = {
        "class_name": ip_class.nome,
        "network": ip_class.rede,
        "interfaces_affected": len(interfaces_assigned),
        "interfaces_list": [f"{iface.nome} (Router: {iface.router.nome})" for iface in interfaces_assigned],
        "gateway_configured": bool(ip_class.gateway),
        "dns_configured": bool(ip_class.dns1 or ip_class.dns2),
        "critical_warning": "Esta operação pode desconectar redes ativas e afetar múltiplos routers!"
    }

    # Se não confirmado, retornar informações do impacto
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Confirmação necessária para exclusão",
                "impact": impact_info,
                "message": "Use confirm=true para confirmar a exclusão desta classe IP",
                "confirmation_required": True
            }
        )

    # Confirmado - executar exclusão
    return crud.crud_network.remove_ip_class(db=db, db_class=ip_class)

# Rotas para atribuição de classes IP às interfaces
@router.post("/interface-ip-assignments/", response_model=InterfaceIPClassAssignmentResponse)
def assign_ip_class_to_interface(
    *,
    db: Session = Depends(deps.get_db),
    assignment_in: InterfaceIPClassAssignmentCreate,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Atribuir uma classe IP a uma interface e aplicar automaticamente no router MikroTik.

    🔄 ATRIBUIÇÃO AUTOMÁTICA:
    - Atribui a classe IP à interface no banco de dados
    - Aplica automaticamente a configuração IP no router MikroTik
    - Configura endereço IP, gateway e DNS se especificados
    - Retorna sucesso da atribuição e aplicação

    💡 RESULTADO: Configuração aplicada automaticamente no router!
    """
    # Verificar se a interface pertence à empresa do usuário
    interface = crud.crud_network.get_router_interface(db=db, interface_id=assignment_in.interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado à interface")

    # Verificar se a classe IP pertence à empresa do usuário
    ip_class = crud.crud_network.get_ip_class(db=db, class_id=assignment_in.ip_class_id)
    if not ip_class or ip_class.empresa_id != current_user.active_empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado à classe IP")

    # Atribuir classe IP à interface
    assignment = crud.crud_network.assign_ip_class_to_interface(db=db, assignment=assignment_in)

    # Verificar se a classe IP tem dados válidos para aplicação
    if not ip_class.rede:
        assignment.applied_configs = []
        assignment.application_status = "error: Classe IP não possui rede configurada"
        return assignment

    # Aplicar configuração automaticamente no router MikroTik
    try:
        # Conectar ao router MikroTik
        from app.core.security import decrypt_password
        from app.mikrotik.controller import MikrotikController

        # Tentar descriptografar senha, se falhar usar em texto plano
        try:
            password = decrypt_password(router.senha)
        except Exception as pwd_error:
            # Se não conseguir descriptografar, assumir que está em texto plano
            password = router.senha
            print(f"Aviso: Usando senha em texto plano para router {router.id}: {str(pwd_error)}")

        # Verificar se os dados do router estão completos
        if not router.ip or not router.usuario:
            raise Exception("Dados do router incompletos: IP ou usuário não configurados")

        mk = MikrotikController(
            host=router.ip,
            username=router.usuario,
            password=password,
            port=router.porta or 8728
        )

        # Aplicar configuração IP da classe à interface
        applied_configs = []
        if ip_class.rede:
            # Extrair endereço IP da rede (primeiro endereço disponível)
            # Exemplo: 192.168.1.0/24 -> 192.168.1.1/24
            network_parts = ip_class.rede.split('/')
            if len(network_parts) == 2:
                base_ip = network_parts[0]
                mask = network_parts[1]

                # Calcular primeiro IP disponível (gateway + 1)
                ip_parts = base_ip.split('.')
                if len(ip_parts) == 4:
                    # Para redes /24, usar .1 como endereço da interface
                    interface_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1/{mask}"

                    # Aplicar endereço IP
                    try:
                        result = mk.set_ip_address(
                            address=interface_ip,
                            interface=interface.nome,
                            comment=f"Classe IP: {ip_class.nome}"
                        )
                        applied_configs.append(f"IP {interface_ip} aplicado à {interface.nome}")
                    except Exception as ip_error:
                        raise Exception(f"Falha ao configurar IP {interface_ip} na interface {interface.nome}: {str(ip_error)}")

                    # Configurar gateway se especificado
                    if ip_class.gateway:
                        try:
                            mk.set_default_route(ip_class.gateway)
                            applied_configs.append(f"Gateway {ip_class.gateway} configurado")
                        except Exception as gw_error:
                            raise Exception(f"Falha ao configurar gateway {ip_class.gateway}: {str(gw_error)}")

                    # Configurar DNS se especificado
                    if ip_class.dns1 or ip_class.dns2:
                        dns_servers = []
                        if ip_class.dns1:
                            dns_servers.append(ip_class.dns1)
                        if ip_class.dns2:
                            dns_servers.append(ip_class.dns2)

                        if dns_servers:
                            try:
                                mk.set_dns_servers(dns_servers)
                                applied_configs.append(f"DNS configurado: {', '.join(dns_servers)}")
                            except Exception as dns_error:
                                raise Exception(f"Falha ao configurar DNS {dns_servers}: {str(dns_error)}")
                else:
                    raise Exception(f"Formato de IP inválido na classe IP: {ip_class.rede}")
            else:
                raise Exception(f"Formato de rede inválido na classe IP: {ip_class.rede}")
        else:
            raise Exception("Classe IP não possui rede configurada")

        mk.close()

        # Adicionar informações da aplicação ao response
        assignment.applied_configs = applied_configs
        assignment.application_status = "success"

    except Exception as e:
        # Capturar detalhes completos do erro
        error_details = f"{type(e).__name__}: {str(e) or 'Erro sem mensagem'}"
        print(f"Erro na aplicação automática da classe IP {ip_class.id} à interface {interface.id}: {error_details}")

        # Se falhar a aplicação, ainda retorna a atribuição mas com status de erro
        assignment.applied_configs = []
        assignment.application_status = f"error: {error_details}"
        # Não lança exception para não impedir a atribuição no banco

    return assignment

@router.delete("/interface-ip-assignments/{interface_id}/{ip_class_id}")
def remove_ip_class_from_interface(
    *,
    db: Session = Depends(deps.get_db),
    interface_id: int,
    ip_class_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
    confirm: bool = False,
):
    """
    Remover a atribuição de uma classe IP de uma interface.

    ⚠️ IMPACTO DA OPERAÇÃO:
    - Remove apenas a atribuição (não deleta a classe IP ou interface)
    - Pode desconectar a rede configurada no router MikroTik
    - Afeta apenas esta interface específica
    - Configurações de IP, gateway e DNS desta classe serão removidas do router

    🔒 CONFIRMAÇÃO OBRIGATÓRIA:
    - Use confirm=true para confirmar a remoção
    - Sem confirmação, retorna informações do impacto
    """
    # Verificar se a interface pertence à empresa do usuário
    interface = crud.crud_network.get_router_interface(db=db, interface_id=interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado à interface")

    # Verificar se a classe IP existe e pertence à empresa
    ip_class = crud.crud_network.get_ip_class(db=db, class_id=ip_class_id)
    if not ip_class or ip_class.empresa_id != current_user.active_empresa_id:
        raise HTTPException(status_code=403, detail="Acesso negado à classe IP")

    impact_info = {
        "interface_name": interface.nome,
        "router_name": router.nome,
        "ip_class_name": ip_class.nome,
        "network": ip_class.rede,
        "gateway_configured": bool(ip_class.gateway),
        "dns_configured": bool(ip_class.dns1 or ip_class.dns2),
        "warning": "Esta operação pode desconectar a rede desta interface no router!"
    }

    # Se não confirmado, retornar informações do impacto
    if not confirm:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Confirmação necessária para remoção",
                "impact": impact_info,
                "message": "Use confirm=true para confirmar a remoção desta atribuição",
                "confirmation_required": True
            }
        )

    # Confirmado - executar remoção
    crud.crud_network.remove_ip_class_from_interface(db=db, interface_id=interface_id, ip_class_id=ip_class_id)
    return {"message": "Classe IP removida da interface com sucesso"}

# Rota especial para sincronizar interfaces do router
@router.post("/routers/{router_id}/sync-interfaces/", response_model=RouterWithInterfacesResponse)
def sync_router_interfaces(
    *,
    db: Session = Depends(deps.get_db),
    router_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Sincronizar interfaces do router com o dispositivo MikroTik.
    Estratégia completa e segura:

    🔄 SINCRONIZAÇÃO DE INTERFACES:
    - Interfaces existentes no MikroTik: atualiza ou cria no sistema
    - Interfaces removidas do MikroTik: marca como inativas (não remove)
    - Interfaces criadas manualmente: preserva intactas

    🌐 IMPORTAÇÃO DE ENDEREÇOS IP:
    - Importa todos os IPs configurados nas interfaces do MikroTik
    - Evita duplicatas de endereços IP

    🏷️ CRIAÇÃO AUTOMÁTICA DE CLASSES IP:
    - Para cada IP encontrado, cria uma classe IP correspondente se não existir
    - Nome: "Rede {network}" (ex: "Rede 192.168.18.0/24")
    - Associa automaticamente a classe IP à interface
    - Gateway e DNS ficam vazios para configuração manual posterior

    💡 RESULTADO: Sincronização completa em um clique!
    """
    # Verificar se o router pertence à empresa do usuário
    router = crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=404, detail="Router não encontrado")

    try:
        # Conectar ao router MikroTik
        from app.core.security import decrypt_password
        from app.mikrotik.controller import MikrotikController

        # Tentar descriptografar senha, se falhar usar em texto plano
        try:
            password = decrypt_password(router.senha)
        except Exception:
            # Se não conseguir descriptografar, assumir que está em texto plano
            password = router.senha

        mk = MikrotikController(
            host=router.ip,
            username=router.usuario,
            password=password,
            port=router.porta or 8728
        )

        # Buscar interfaces do router
        mikrotik_interfaces = mk.get_interfaces()

        # Obter interfaces atuais do banco
        current_interfaces = crud.crud_network.get_router_interfaces_by_router(db=db, router_id=router_id)

        # Criar conjunto de nomes de interfaces do MikroTik
        mikrotik_interface_names = {mk_interface.get('name') for mk_interface in mikrotik_interfaces}

        # Processar cada interface do MikroTik
        for mk_interface in mikrotik_interfaces:
            interface_name = mk_interface.get('name')
            # Mapear tipos do MikroTik para tipos do sistema
            mikrotik_type = mk_interface.get('type', 'ether')
            type_mapping = {
                'ether': 'ethernet',
                'wlan': 'wireless',
                'vlan': 'vlan',
                'bridge': 'bridge',
                'ppp': 'ppp',
            }
            interface_type = type_mapping.get(mikrotik_type, 'other')
            mac_address = mk_interface.get('mac-address')
            comment = mk_interface.get('comment')

            # Verificar se a interface já existe no banco
            existing_interface = next((i for i in current_interfaces if i.nome == interface_name), None)

            if existing_interface:
                # Atualizar interface existente
                interface_update = RouterInterfaceUpdate(
                    nome=interface_name,
                    tipo=interface_type,
                    mac_address=mac_address,
                    comentario=comment,
                    is_active=True
                )
                crud.crud_network.update_router_interface(
                    db=db,
                    db_interface=existing_interface,
                    interface_in=interface_update
                )
            else:
                # Criar nova interface descoberta no MikroTik
                interface_create = RouterInterfaceCreate(
                    nome=interface_name,
                    tipo=interface_type,
                    mac_address=mac_address,
                    comentario=f"[Sincronizado] {comment}" if comment else "[Sincronizado do MikroTik]",
                    is_active=True
                )
                crud.crud_network.create_router_interface(
                    db=db,
                    interface=interface_create,
                    router_id=router_id
                )

        # Processar interfaces que existem no banco mas não no MikroTik
        for db_interface in current_interfaces:
            if db_interface.nome not in mikrotik_interface_names:
                # Interface existe no banco mas não no MikroTik
                if db_interface.mac_address:
                    # Interface foi sincronizada anteriormente, marcar como inativa
                    interface_update = RouterInterfaceUpdate(
                        is_active=False,
                        comentario=f"{db_interface.comentario or ''} [Inativa - não encontrada no MikroTik]".strip()
                    )
                    crud.crud_network.update_router_interface(
                        db=db,
                        db_interface=db_interface,
                        interface_in=interface_update
                    )
                # Se não tem mac_address, é uma interface criada manualmente - preservar

        # Buscar endereços IP configurados
        mikrotik_ips = mk.get_ip_addresses()

        # Atualizar endereços IP das interfaces
        for mk_ip in mikrotik_ips:
            address = mk_ip.get('address')
            interface_name = mk_ip.get('interface')
            comment = mk_ip.get('comment')

            # Encontrar interface no banco (usar current_interfaces atualizada)
            current_interfaces_updated = crud.crud_network.get_router_interfaces_by_router(db=db, router_id=router_id)
            interface = next((i for i in current_interfaces_updated if i.nome == interface_name), None)

            if interface:
                # Verificar se o endereço IP já existe
                existing_ips = crud.crud_network.get_ip_addresses_by_interface(db=db, interface_id=interface.id)
                existing_ip = next((ip for ip in existing_ips if ip.endereco_ip == address), None)

                if not existing_ip:
                    # Criar novo endereço IP
                    ip_create = InterfaceIPAddressCreate(
                        endereco_ip=address,
                        comentario=comment,
                        is_primary=len(existing_ips) == 0  # Primeiro IP é primário
                    )
                    crud.crud_network.create_interface_ip_address(
                        db=db,
                        ip_address=ip_create,
                        interface_id=interface.id
                    )

        # Criar classes IP automaticamente baseadas nos IPs encontrados
        empresa_id = current_user.active_empresa_id or 2
        for mk_ip in mikrotik_ips:
            address = mk_ip.get('address')
            interface_name = mk_ip.get('interface')

            # Encontrar interface correspondente
            interface = next((i for i in current_interfaces_updated if i.nome == interface_name), None)
            if not interface:
                continue

            # Extrair rede do endereço IP
            if '/' in address:
                ip_part, mask_part = address.split('/')
                ip_parts = ip_part.split('.')

                if len(ip_parts) == 4 and mask_part.isdigit():
                    mask = int(mask_part)

                    # Calcular endereço de rede baseado na máscara
                    if mask >= 24:  # Para /24 ou maior, usar o terceiro octeto
                        network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/{mask}"
                    elif mask >= 16:  # Para /16
                        network = f"{ip_parts[0]}.{ip_parts[1]}.0.0/{mask}"
                    elif mask >= 8:  # Para /8
                        network = f"{ip_parts[0]}.0.0.0/{mask}"
                    else:
                        network = f"0.0.0.0/{mask}"

                    # Verificar se já existe uma classe IP para esta rede
                    existing_classes = crud.crud_network.get_ip_classes_by_empresa(db=db, empresa_id=empresa_id)
                    existing_class = next((c for c in existing_classes if c.rede == network), None)

                    if not existing_class:
                        # Criar nova classe IP
                        class_name = f"Rede {network}"
                        ip_class_create = IPClassCreate(
                            nome=class_name,
                            rede=network,
                            gateway=None,  # Pode ser configurado depois
                            dns1=None,
                            dns2=None
                        )
                        new_class = crud.crud_network.create_ip_class(
                            db=db,
                            ip_class=ip_class_create,
                            empresa_id=empresa_id
                        )

                        # Associar classe IP à interface
                        assignment_create = InterfaceIPClassAssignmentCreate(
                            interface_id=interface.id,
                            ip_class_id=new_class.id
                        )
                        crud.crud_network.assign_ip_class_to_interface(db=db, assignment=assignment_create)

                        print(f"Classe IP criada e associada: {class_name} -> {interface_name}")

        mk.close()

        # Retornar router com interfaces atualizadas
        return crud.crud_router.get_router(db=db, router_id=router_id, empresa_id=current_user.active_empresa_id)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao sincronizar interfaces: {str(e)}")

# Rota para aplicar configuração IP à interface no router
@router.post("/interfaces/{interface_id}/apply-ip-config/")
def apply_ip_config_to_interface(
    *,
    db: Session = Depends(deps.get_db),
    interface_id: int,
    current_user: models.Usuario = Depends(deps.get_current_active_user),
):
    """
    Aplicar configuração de IP da classe atribuída à interface no router MikroTik.
    """
    # Verificar se a interface pertence à empresa do usuário
    interface = crud.crud_network.get_router_interface(db=db, interface_id=interface_id)
    if not interface:
        raise HTTPException(status_code=404, detail="Interface não encontrada")

    router = crud.crud_router.get_router(db=db, router_id=interface.router_id, empresa_id=current_user.active_empresa_id)
    if not router:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Verificar se há classes IP atribuídas à interface
    ip_classes = crud.crud_network.get_ip_classes_by_interface(db=db, interface_id=interface_id)
    if not ip_classes:
        raise HTTPException(status_code=400, detail="Nenhuma classe IP atribuída à interface")

    try:
        # Conectar ao router MikroTik
        from app.core.security import decrypt_password
        from app.mikrotik.controller import MikrotikController

        # Tentar descriptografar senha, se falhar usar em texto plano
        try:
            password = decrypt_password(router.senha)
        except Exception as pwd_error:
            # Se não conseguir descriptografar, assumir que está em texto plano
            password = router.senha
            print(f"Aviso: Usando senha em texto plano para router {router.id}: {str(pwd_error)}")

        mk = MikrotikController(
            host=router.ip,
            username=router.usuario,
            password=password,
            port=router.porta or 8728
        )

        # Aplicar configuração para cada classe IP atribuída
        applied_configs = []
        for ip_class in ip_classes:
            # Aplicar endereço IP da classe à interface
            if ip_class.rede:
                # Extrair endereço IP da rede (primeiro endereço disponível)
                # Exemplo: 192.168.1.0/24 -> 192.168.1.1/24
                network_parts = ip_class.rede.split('/')
                if len(network_parts) == 2:
                    base_ip = network_parts[0]
                    mask = network_parts[1]

                    # Calcular primeiro IP disponível (gateway + 1)
                    ip_parts = base_ip.split('.')
                    if len(ip_parts) == 4:
                        # Para redes /24, usar .1 como endereço da interface
                        interface_ip = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.1/{mask}"

                        # Aplicar endereço IP
                        try:
                            result = mk.set_ip_address(
                                address=interface_ip,
                                interface=interface.nome,
                                comment=f"Classe IP: {ip_class.nome}"
                            )
                            applied_configs.append(f"IP {interface_ip} aplicado à {interface.nome}")
                        except Exception as ip_error:
                            raise Exception(f"Falha ao configurar IP {interface_ip} na interface {interface.nome}: {str(ip_error)}")

                        # Configurar DNS se especificado
                        if ip_class.dns1 or ip_class.dns2:
                            dns_servers = []
                            if ip_class.dns1:
                                dns_servers.append(ip_class.dns1)
                            if ip_class.dns2:
                                dns_servers.append(ip_class.dns2)

                            if dns_servers:
                                try:
                                    mk.set_dns_servers(dns_servers)
                                    applied_configs.append(f"DNS configurado: {', '.join(dns_servers)}")
                                except Exception as dns_error:
                                    raise Exception(f"Falha ao configurar DNS {dns_servers}: {str(dns_error)}")
                    else:
                        raise Exception(f"Formato de IP inválido na classe IP: {ip_class.rede}")
                else:
                    raise Exception(f"Formato de rede inválido na classe IP: {ip_class.rede}")
            else:
                raise Exception("Classe IP não possui rede configurada")

        return {
            "message": f"Configuração IP aplicada à interface {interface.nome} com sucesso",
            "applied_configs": applied_configs
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao aplicar configuração IP: {str(e)}")