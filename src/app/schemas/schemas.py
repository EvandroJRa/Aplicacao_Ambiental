from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from datetime import date

# A base de dados que o usuário precisa preencher
class ClienteBase(BaseModel):
    nome: str
    cnpj: str
    whatsapp_contato: str
    email: str
    senha_provisoria: str # Novo campo!
    codigo_cliente: Optional[str] = None 

class ClienteResponse(BaseModel):
    id: int
    nome: str
    cnpj: str
    whatsapp_contato: str
    email: str   
    
class Config:
        from_attributes = True     

# Usado para CRIAR um cliente (herda a base)
class ClienteCreate(ClienteBase):
    pass

# Usado para DEVOLVER os dados do cliente (inclui o ID e a data gerados pelo banco)
class ClienteResponse(ClienteBase):
    id: int
    criado_em: datetime

    class Config:
        from_attributes = True # Permite que o Pydantic leia dados do SQLAlchemy


# --- Validação de dados para os pontos de monitoramento ---

class PontoMonitoramentoBase(BaseModel):
    nome_ponto: str
    tipo: str # Ex: "Poço de Monitoramento", "Efluente Bruto"
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


# ----Atualizar filtros

class DocumentoBase(BaseModel):
    tipo_documento: str # Ex: "Laudo Laboratorial", "Ofício"
    competencia: Optional[date] = None

class DocumentoCreate(DocumentoBase):
    ponto_id: Optional[int] = None # Opcional, pois pode ser um documento geral da empresa

class DocumentoResponse(DocumentoBase):
    id: int
    cliente_id: int
    ponto_id: Optional[int]
    url_arquivo: str # Onde o arquivo está salvo
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

# 👇 Essa é a classe que o GET vai usar para devolver a lista sem mostrar as senhas!
class UsuarioResponse(UsuarioBase):
    id: int
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str

# ==========================================
# SCHEMAS DE AUDITORIA E LOGS
# ==========================================
class AuditoriaBase(BaseModel):
    evento: str
    detalhes: Optional[str] = None
    ip: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    user_agent: Optional[str] = None

# Para criar o log (O ID do usuário será pego direto do crachá de segurança!)
class AuditoriaCreate(AuditoriaBase):
    pass

# Para devolver o log no Painel Admin depois
class AuditoriaResponse(AuditoriaBase):
    id: int
    usuario_id: int
    data_hora: datetime
    
    # Adicionamos os campos novos na resposta
    email_usuario: Optional[str] = None
    nome_empresa: Optional[str] = None
    cnpj_empresa: Optional[str] = None
    telefone_empresa: Optional[str] = None

    class Config:
        from_attributes = True