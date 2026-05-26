from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models import ContractType, ProjectStatus


class ProjectBase(BaseModel):
    project_no: str | None = Field(default=None, max_length=80)
    customer_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    contract_type: ContractType = ContractType.TIME_AND_MATERIALS
    status: ProjectStatus = ProjectStatus.ACTIVE
    default_hourly_rate: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    fixed_fee_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    project_no: str | None = Field(default=None, max_length=80)
    customer_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    contract_type: ContractType | None = None
    status: ProjectStatus | None = None
    default_hourly_rate: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    fixed_fee_amount: Decimal | None = Field(default=None, ge=0, decimal_places=2)


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
