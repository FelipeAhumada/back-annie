"""
SQLAlchemy models for Annie-AI multi-tenant RBAC system.

These models represent the database schema for users, tenants, roles, and their relationships.
Note: The current codebase uses psycopg2 directly, but these models serve as documentation
and can be used if migrating to SQLAlchemy ORM in the future.
"""
from __future__ import annotations
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, ForeignKey, Text, 
    TIMESTAMP, Enum as SQLEnum, PrimaryKeyConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class TenantRoleEnum(PyEnum):
    """Role enum for tenant members."""
    OWNER = "owner"
    ADMIN = "admin"
    AGENT = "agent"
    OBSERVER = "observer"


class User(Base):
    """
    User model representing system users.
    
    Users can belong to multiple tenants with different roles per tenant.
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    tenant_memberships = relationship("UserTenant", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email})>"


class Tenant(Base):
    """
    Tenant model representing organizations/workspaces.
    
    Each tenant is isolated and has its own settings, members, and data.
    """
    __tablename__ = "tenants"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    domain = Column(String, nullable=True)
    timezone = Column(String, default="America/Santiago")
    locale = Column(String, default="es-CL")
    description = Column(Text, nullable=True)
    website = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    logo_url = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationships
    members = relationship("UserTenant", back_populates="tenant", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, name={self.name})>"


class Role(Base):
    """
    Role model defining available roles in the system.
    
    Roles are: owner, admin, agent, observer
    """
    __tablename__ = "roles"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)  # owner, admin, agent, observer
    describe = Column(Text, nullable=True)
    
    # Relationships
    user_tenants = relationship("UserTenant", back_populates="role")
    
    def __repr__(self) -> str:
        return f"<Role(id={self.id}, name={self.name})>"


class UserTenant(Base):
    """
    Junction table linking users to tenants with a specific role.
    
    This is the core of the multi-tenant RBAC system.
    Each user can have different roles in different tenants.
    """
    __tablename__ = "user_tenants"
    
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Composite primary key
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "tenant_id"),
        {"comment": "User-tenant membership with role assignment"}
    )
    
    # Relationships
    user = relationship("User", back_populates="tenant_memberships")
    tenant = relationship("Tenant", back_populates="members")
    role = relationship("Role", back_populates="user_tenants")
    
    def __repr__(self) -> str:
        return f"<UserTenant(user_id={self.user_id}, tenant_id={self.tenant_id}, role_id={self.role_id})>"


class GeneralSettings(Base):
    """
    General settings model for tenant-specific organization information.
    
    One record per tenant (enforced by PRIMARY KEY on tenant_id).
    Contains organization details like name, mission, vision, etc.
    """
    __tablename__ = "general_settings"
    
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    short_description = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    purpose = Column(Text, nullable=True)
    customer_problems = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # Relationship
    tenant = relationship("Tenant", backref="general_settings")
    
    def __repr__(self) -> str:
        return f"<GeneralSettings(tenant_id={self.tenant_id}, name={self.name})>"

