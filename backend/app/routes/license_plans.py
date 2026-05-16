from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.models import Usuario
from app.models.license_plan import LicensePricingPlan
from app.schemas.license_plan import LicensePricingPlanCreate, LicensePricingPlanResponse, LicensePricingPlanUpdate
from app.routes.auth import get_current_active_superuser

router = APIRouter(prefix="/license-plans", tags=["License Plans"])

@router.get("/", response_model=List[LicensePricingPlanResponse])
def list_active_plans(db: Session = Depends(get_db)):
    """Lista todos os planos de licença ativos (Público)."""
    return db.query(LicensePricingPlan).filter(LicensePricingPlan.is_active == True).all()

@router.get("/admin/all", response_model=List[LicensePricingPlanResponse])
def admin_list_all_plans(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Lista todos os planos (incluindo inativos) para o admin."""
    return db.query(LicensePricingPlan).all()

@router.post("/", response_model=LicensePricingPlanResponse)
def create_plan(
    plan_in: LicensePricingPlanCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Cria um novo plano de licença (Admin apenas)."""
    db_plan = LicensePricingPlan(**plan_in.model_dump())
    db.add(db_plan)
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.put("/{plan_id}", response_model=LicensePricingPlanResponse)
def update_plan(
    plan_id: int,
    plan_in: LicensePricingPlanUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Atualiza um plano de licença (Admin apenas)."""
    db_plan = db.query(LicensePricingPlan).filter(LicensePricingPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    update_data = plan_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_plan, field, value)
    
    db.commit()
    db.refresh(db_plan)
    return db_plan

@router.delete("/{plan_id}")
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_active_superuser)
):
    """Deleta um plano de licença (Admin apenas)."""
    db_plan = db.query(LicensePricingPlan).filter(LicensePricingPlan.id == plan_id).first()
    if not db_plan:
        raise HTTPException(status_code=404, detail="Plano não encontrado")
    
    db.delete(db_plan)
    db.commit()
    return {"message": "Plano deletado com sucesso"}
