from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.models import ClientIngestionConfig
from app.schema.client_ingestion_config import ClientIngestionConfigUpdate


async def get_active_configs(db: AsyncSession) -> List[ClientIngestionConfig]:
    result = await db.execute(
        select(ClientIngestionConfig).where(ClientIngestionConfig.is_active.is_(True))
    )
    return result.scalars().all()


async def get_config_by_company(db: AsyncSession, company_id: int) -> Optional[ClientIngestionConfig]:
    result = await db.execute(
        select(ClientIngestionConfig).where(ClientIngestionConfig.company_id == company_id)
    )
    return result.scalars().first()


async def create_config(db: AsyncSession, config_data, company_id: int) -> ClientIngestionConfig:
    cfg = ClientIngestionConfig(
        company_id=company_id,
        imap_host=config_data.imap_host,
        imap_port=config_data.imap_port,
        imap_username=config_data.imap_username,
        imap_password=config_data.imap_password,
        smtp_host=config_data.smtp_host,
        smtp_port=config_data.smtp_port,
        smtp_username=config_data.smtp_username,
        smtp_password=config_data.smtp_password,
        building_addresses_list=config_data.building_addresses_list,
        trusted_sender_domains=config_data.trusted_sender_domains,
        is_active=config_data.is_active
    )

    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def update_config(db: AsyncSession, cfg: ClientIngestionConfig, updates: ClientIngestionConfigUpdate) -> ClientIngestionConfig:

    data = updates.model_dump(exclude_none=True, exclude_unset=True)

    for k, v in data.items():
        if v is not None:
            setattr(cfg, k, v)

    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg


async def switch_config(db: AsyncSession, cfg: ClientIngestionConfig) -> ClientIngestionConfig:
    cfg.is_active = not cfg.is_active

    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    return cfg
