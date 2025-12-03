from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.crud import client_ingestion_config as crud
from app.models.models import ClientIngestionConfig
from app.schema.client_ingestion_config import ClientIngestionConfigUpdate
from app.utils.kms import encrypt_secret, decrypt_secret

async def create_config_service(
    db: AsyncSession, 
    payload,
    company_id: int
) -> ClientIngestionConfig:

    if payload.imap_password:
        payload.imap_password = encrypt_secret(payload.imap_password)

    if payload.smtp_password:
        payload.smtp_password = encrypt_secret(payload.smtp_password)

    return await crud.create_config(db, payload, company_id)

async def update_config_service(
    db: AsyncSession,
    cfg: ClientIngestionConfig,
    payload: ClientIngestionConfigUpdate
) -> ClientIngestionConfig:

    if payload.imap_password:
        payload.imap_password = encrypt_secret(payload.imap_password)

    if payload.smtp_password:
        payload.smtp_password = encrypt_secret(payload.smtp_password)

    return await crud.update_config(db, cfg, payload)


async def get_decrypted_config(
    db: AsyncSession,
    company_id: int
) -> Optional[ClientIngestionConfig]:

    cfg = await crud.get_config_by_company(db, company_id)
    if not cfg:
        return None

    if cfg.imap_password:
        cfg.imap_password = decrypt_secret(cfg.imap_password)

    if cfg.smtp_password:
        cfg.smtp_password = decrypt_secret(cfg.smtp_password)

    return cfg


async def switch_config_service(db: AsyncSession, cfg: ClientIngestionConfig) -> None:
    await crud.switch_config(db, cfg)


async def fetch_active_configs(
    db: AsyncSession
) -> List[ClientIngestionConfig]:

    return await crud.get_active_configs(db)