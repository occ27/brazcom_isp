from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.models import Usuario, Empresa
from app.models.license import CompanyLicense, LicenseStatus, LicensePlan
from app.models.license_plan import LicensePricingPlan
from app.schemas.license import LicenseCreate, LicenseResponse, LicenseUpdate, LicenseAdminCreate
from app.routes.auth import get_current_active_user, get_current_active_superuser

router = APIRouter(prefix="/licenses", tags=["Licenses"])

@router.post("/", response_model=LicenseResponse)
def create_license(
    license_in: LicenseCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Cria uma nova solicitação de licença (assinatura)."""
    empresa = db.query(Empresa).filter(Empresa.id == license_in.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")
    
    # Verificar permissão de gerenciamento da empresa
    user_empresas_ids = [assoc.empresa_id for assoc in current_user.empresas]
    is_owner = empresa.user_id == current_user.id
    
    if not current_user.is_superuser and not is_owner and empresa.id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Sem permissão para solicitar licença por esta empresa")

    # Verificar se já existe uma licença pendente
    existing_pending = db.query(CompanyLicense).filter(
        CompanyLicense.empresa_id == empresa.id,
        CompanyLicense.status == LicenseStatus.PENDING
    ).first()
    if existing_pending:
        return existing_pending

    # Determinar Plano e Preço
    plan_name = license_in.plan
    price = license_in.price

    if license_in.plan_id:
        pricing_plan = db.query(LicensePricingPlan).filter(LicensePricingPlan.id == license_in.plan_id).first()
        if not pricing_plan:
            raise HTTPException(status_code=404, detail="Plano de precificação não encontrado")
        plan_name = pricing_plan.name
        price = pricing_plan.price
    
    if not plan_name or price is None:
         raise HTTPException(status_code=400, detail="Plano ou preço não informado")

    db_license = CompanyLicense(
        empresa_id=license_in.empresa_id,
        user_id=current_user.id,
        plan_id=license_in.plan_id,
        plan=plan_name,
        price=price,
        status=LicenseStatus.PENDING
    )
    db.add(db_license)
    db.commit()
    db.refresh(db_license)
    return db_license

@router.get("/my-company/{empresa_id}", response_model=List[LicenseResponse])
def get_company_licenses(
    empresa_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_user)
):
    """Lista licenças de uma empresa específica."""
    db_empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not db_empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    user_empresas_ids = [assoc.empresa_id for assoc in current_user.empresas]
    is_owner = db_empresa.user_id == current_user.id
    
    if not current_user.is_superuser and not is_owner and empresa_id not in user_empresas_ids:
        raise HTTPException(status_code=403, detail="Acesso negado")

    return db.query(CompanyLicense).filter(CompanyLicense.empresa_id == empresa_id).order_by(CompanyLicense.created_at.desc()).all()

@router.get("/admin/pending", response_model=List[LicenseResponse])
def list_pending_licenses(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Lista todas as licenças pendentes de aprovação (Admin apenas)."""
    return db.query(CompanyLicense).filter(CompanyLicense.status == LicenseStatus.PENDING).all()

@router.post("/{license_id}/approve", response_model=LicenseResponse)
def approve_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Aprova uma solicitação de licença e ativa o acesso da empresa (Admin apenas)."""
    db_license = db.query(CompanyLicense).filter(CompanyLicense.id == license_id).first()
    if not db_license:
        raise HTTPException(status_code=404, detail="Licença não encontrada")
    
    if db_license.status != LicenseStatus.PENDING:
        raise HTTPException(status_code=400, detail="Apenas licenças pendentes podem ser aprovadas")

    now = datetime.now()
    duration_days = 365 # Default
    
    if db_license.plan_id:
        pricing_plan = db.query(LicensePricingPlan).filter(LicensePricingPlan.id == db_license.plan_id).first()
        if pricing_plan:
            duration_days = pricing_plan.duration_months * 30 # Aproximação simples ou usar calendar
    else:
        # Fallback para nomes antigos
        if db_license.plan == LicensePlan.ANNUAL:
            duration_days = 365
        elif db_license.plan == LicensePlan.BIANNUAL:
            duration_days = 730

    end_date = now + timedelta(days=duration_days)

    db_license.status = LicenseStatus.ACTIVE
    db_license.start_date = now
    db_license.end_date = end_date
    db_license.payment_date = now
    db_license.approved_by_id = current_user.id
    
    # Ativar a empresa no banco de dados se ela estiver inativa
    empresa = db.query(Empresa).filter(Empresa.id == db_license.empresa_id).first()
    if empresa:
        empresa.is_active = True

    db.commit()
    db.refresh(db_license)
    return db_license

@router.get("/check-status/{empresa_id}")
def check_active_license(
    empresa_id: int,
    db: Session = Depends(get_db)
):
    """Endpoint simples para o frontend verificar se a empresa está liberada no login."""
    db_license = db.query(CompanyLicense).filter(
        CompanyLicense.empresa_id == empresa_id,
        CompanyLicense.status == LicenseStatus.ACTIVE,
        CompanyLicense.end_date > datetime.now()
    ).first()
    
    return {"is_active": db_license is not None, "license": db_license}

# --- ADMIN ROUTES COMPLEMENTARES ---

@router.get("/admin/all", response_model=List[LicenseResponse])
def list_all_licenses(
    skip: int = 0,
    limit: int = 100,
    status: Optional[LicenseStatus] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Lista todas as licenças com paginação."""
    query = db.query(CompanyLicense)
    if status:
        query = query.filter(CompanyLicense.status == status)
    return query.order_by(CompanyLicense.created_at.desc()).offset(skip).limit(limit).all()

@router.post("/admin/manual", response_model=LicenseResponse)
def create_manual_license(
    sub_in: LicenseAdminCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Cria manualmente uma licença ATIVA (ex: cortesia ou venda offline)."""
    empresa = db.query(Empresa).filter(Empresa.id == sub_in.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa não encontrada")

    now = sub_in.start_date or datetime.now()
    end = sub_in.end_date
    if not end:
        if sub_in.plan == LicensePlan.ANNUAL:
            end = now + timedelta(days=365)
        else:
            end = now + timedelta(days=730)

    db_license = CompanyLicense(
        empresa_id=sub_in.empresa_id,
        user_id=sub_in.user_id or current_user.id,
        plan=sub_in.plan,
        price=sub_in.price,
        status=sub_in.status,
        start_date=now,
        end_date=end,
        payment_date=now,
        approved_by_id=current_user.id,
        notes="Criada manualmente pelo administrador do sistema"
    )
    
    empresa.is_active = True
    
    db.add(db_license)
    db.commit()
    db.refresh(db_license)
    return db_license

@router.put("/admin/{license_id}", response_model=LicenseResponse)
def admin_update_license(
    license_id: int,
    sub_in: LicenseUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Atualiza dados de uma licença."""
    db_license = db.query(CompanyLicense).filter(CompanyLicense.id == license_id).first()
    if not db_license:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    update_data = sub_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_license, field, value)

    db.commit()
    db.refresh(db_license)
    return db_license

@router.post("/admin/{license_id}/cancel", response_model=LicenseResponse)
def cancel_license(
    license_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Cancela uma licença."""
    db_license = db.query(CompanyLicense).filter(CompanyLicense.id == license_id).first()
    if not db_license:
        raise HTTPException(status_code=404, detail="Licença não encontrada")

    db_license.status = LicenseStatus.CANCELLED
    db.commit()
    db.refresh(db_license)
    return db_license

@router.get("/admin/companies-status")
def list_companies_with_license_status(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Resumo do status de todas as empresas e suas licenças."""
    companies = db.query(Empresa).all()
    result = []
    now = datetime.now()
    
    for emp in companies:
        active = db.query(CompanyLicense).filter(
            CompanyLicense.empresa_id == emp.id,
            CompanyLicense.status == LicenseStatus.ACTIVE,
            CompanyLicense.end_date > now
        ).order_by(CompanyLicense.end_date.desc()).first()
        
        pending = db.query(CompanyLicense).filter(
            CompanyLicense.empresa_id == emp.id,
            CompanyLicense.status == LicenseStatus.PENDING
        ).first()
        
        result.append({
            "id": emp.id,
            "razao_social": emp.razao_social,
            "cnpj": emp.cnpj,
            "is_active": emp.is_active,
            "license_status": "ATIVA" if active else ("PENDENTE" if pending else "INATIVA"),
            "end_date": active.end_date if active else None,
            "plan": active.plan if active else (pending.plan if pending else None)
        })
        
    return result
