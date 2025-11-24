from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base

# Associação Role <-> Permission
role_permission_association = Table(
    'role_permission_association',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('permissions.id'), primary_key=True)
)

# Associação User <-> Role (com escopo opcional por empresa/provider)
user_role_association = Table(
    'user_role_association',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('empresa_id', Integer, ForeignKey('empresas.id'), nullable=True)
)


class Role(Base):
    __tablename__ = "roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), index=True, nullable=False)
    description = Column(String(255))
    # Escopo opcional: quando setado, a role é específica para uma empresa (provedor)
    empresa_id = Column(Integer, ForeignKey('empresas.id'), nullable=True)

    permissions = relationship(
        "Permission",
        secondary=role_permission_association,
        back_populates="roles"
    )

    # users: relação muitos-para-muitos via tabela user_role_association
    users = relationship("Usuario", secondary=user_role_association, backref="roles")


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False) # Ex: "router_create", "client_block"
    description = Column(String(255))

    roles = relationship(
        "Role",
        secondary=role_permission_association,
        back_populates="permissions"
    )