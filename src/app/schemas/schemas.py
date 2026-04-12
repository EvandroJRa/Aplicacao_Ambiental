from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# A base de dados que o usuário precisa preencher
class ClienteBase(BaseModel):
    nome: str
    cnpj: str
    whatsapp_contato: str
    email: Optional[str] = None

# Usado para CRIAR um cliente (herda a base)
class ClienteCreate(ClienteBase):
    pass

# Usado para DEVOLVER os dados do cliente (inclui o ID e a data gerados pelo banco)
class ClienteResponse(ClienteBase):
    id: int
    criado_em: datetime

    class Config:
        from_attributes = True # Permite que o Pydantic leia dados do SQLAlchemy