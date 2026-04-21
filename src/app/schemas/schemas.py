from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, date


# ==========================================
# SCHEMAS DE CLIENTE
# ==========================================
class ClienteBase(BaseModel):
    nome: str
    cnpj: str
    whatsapp_contato: str
    email: str
    senha_provisoria: str
    codigo_cliente: Optional[str] = None


class ClienteCreate(ClienteBase):
    pass


class ClienteResponse(BaseModel):
    id: int
    nome: str
    cnpj: str
    email: str
    whatsapp_contato: str
    codigo_identificador: Optional[str] = None
    criado_em: datetime

    class Config:
        from_attributes = True


# ==========================================
# SCHEMAS DE PONTO DE MONITORAMENTO
# ==========================================
class PontoMonitoramentoBase(BaseModel):
    nome_ponto: str
    tipo: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ativo: bool = True


class PontoMonitoramentoCreate(PontoMonitoramentoBase):
    pass


class PontoMonitoramentoResponse(PontoMonitoramentoBase):
    id: int
    cliente_id: int

    class Config:
        from_attributes = True


# ==========================================
# SCHEMAS DE DOCUMENTO
# ==========================================
class DocumentoBase(BaseModel):
    tipo_documento: str
    competencia: Optional[date] = None


class DocumentoCreate(DocumentoBase):
    ponto_id: Optional[int] = None


class DocumentoResponse(DocumentoBase):
    id: int
    cliente_id: int
    ponto_id: Optional[int] = None
    processo_id: Optional[int] = None
    url_arquivo: str
    hash_arquivo: Optional[str] = None  # SHA-256 — prova de integridade
    data_upload: datetime

    class Config:
        from_attributes = True


# ==========================================
# SCHEMAS DE USUÁRIO E AUTENTICAÇÃO
# ==========================================
class UsuarioBase(BaseModel):
    email: EmailStr
    cliente_id: int


class UsuarioCreate(UsuarioBase):
    senha: str


class UsuarioResponse(UsuarioBase):
    id: int
    ultima_atividade: Optional[datetime] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    is_admin: bool = False


# ==========================================
# SCHEMAS DE AUDITORIA
# ==========================================
class AuditoriaBase(BaseModel):
    evento: str
    detalhes: Optional[str] = None
    ip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_agent: Optional[str] = None


class AuditoriaCreate(AuditoriaBase):
    pass


class AuditoriaResponse(AuditoriaBase):
    id: int
    usuario_id: int
    cliente_id: Optional[int] = None
    email_usuario: Optional[str] = None
    nome_empresa: Optional[str] = None
    cnpj_empresa: Optional[str] = None
    telefone_empresa: Optional[str] = None
    data_hora: datetime

    class Config:
        from_attributes = True
