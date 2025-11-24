from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.models import Tenant
from app.schema.email_draft import TenantCreate


async def create_tenant(db: AsyncSession, tenant: TenantCreate, user_id: int):
    db_obj = Tenant(**tenant.dict(), user_id=user_id)
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def get_tenant(db: AsyncSession, tenant_id: int, user_id: int):
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def update_tenant(db: AsyncSession, tenant_id: int, tenant_data: TenantCreate, user_id: int):
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.user_id == user_id
        )
    )
    db_obj = result.scalar_one_or_none()
    if not db_obj:
        return None

    db_obj.name = tenant_data.name
    db_obj.data = tenant_data.data
    await db.commit()
    await db.refresh(db_obj)
    return db_obj


async def delete_tenant(db: AsyncSession, tenant_id: int, user_id: int):
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.user_id == user_id
        )
    )
    db_obj = result.scalar_one_or_none()
    if not db_obj:
        return False

    await db.delete(db_obj)
    await db.commit()
    return True


async def get_all_tenants(db: AsyncSession, user_id: int):
    result = await db.execute(
        select(Tenant).where(Tenant.user_id == user_id).order_by(Tenant.id.desc())
    )
    return result.scalars().all()
