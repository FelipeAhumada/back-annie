from pydantic import BaseModel, EmailStr
from typing import Optional, Literal, List, Dict

class LoginIn(BaseModel):
   email: EmailStr
   password: str

class SignedUploadIn(BaseModel):
    filename: str
    size_bytes: int
    mime_type: Optional[str] = None

class SignedUploadOut(BaseModel):
    mode: Literal["single","multipart"]
    storage_key: str
    expires_at: str
    put_url: Optional[str] = None
    multipart: Optional[dict] = None

class CommitIn(BaseModel):
    file: Dict
    title: Optional[str] = None
    lang: Optional[str] = "es"
    source: str = "upload"
