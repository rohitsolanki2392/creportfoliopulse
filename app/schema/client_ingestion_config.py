from pydantic import BaseModel
from typing import List, Optional

class ClientIngestionConfigCreate(BaseModel):
    imap_host: str
    imap_port: int = 993
    imap_username: str
    imap_password: str
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    building_addresses_list: List[str] = []
    trusted_sender_domains: List[str] = []
    is_active: bool = True


class ClientIngestionConfigUpdate(BaseModel):
    imap_host: Optional[str]
    imap_port: Optional[int]
    imap_username: Optional[str]
    imap_password: Optional[str]
    smtp_host: Optional[str]
    smtp_port: Optional[int]
    smtp_username: Optional[str]
    smtp_password: Optional[str]
    building_addresses_list: Optional[List[str]]
    trusted_sender_domains: Optional[List[str]]
    is_active: Optional[bool]


class ClientIngestionConfigOut(BaseModel):
    id: int
    company_id: int
    imap_host: str
    imap_port: int
    imap_username: str
    smtp_host: Optional[str]
    smtp_port: Optional[int]
    smtp_username: Optional[str]
    building_addresses_list: List[str]
    trusted_sender_domains: List[str]
    is_active: bool

    class Config:
        from_attributes = True