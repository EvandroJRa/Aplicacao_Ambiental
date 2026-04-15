from datetime import datetime, timezone 
from typing import List, Optional
from sqlalchemy import Float, DateTime

from sqlalchemy import String, Text, Boolean, Numeric, Date, DateTime, ForeignKey, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ==========================================
# 1. CLASSE BASE (Sempre a primeira coisa!)
# ==========================================
class Base(DeclarativeBase):
    pass

# ==========================================
# 2. MODELOS DO BANCO DE DADOS
# ==========================================
class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), unique=True, nullable=False)
    whatsapp_contato: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relacionamentos 
    pontos: Mapped[List["PontoMonitoramento"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    processos: Mapped[List["Processo"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    documentos: Mapped[List["Documento"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    notificacoes: Mapped[List["NotificacaoWhatsApp"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    
    # CORREÇÃO: A linha de usuários adicionada no lugar certo e no padrão 2.0!
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Chave estrangeira
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)

    # Relacionamento
    cliente: Mapped["Cliente"] = relationship(back_populates="usuarios")


class PontoMonitoramento(Base):
    __tablename__ = "pontos_monitoramento"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    nome_ponto: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False) 
    latitude: Mapped[Optional[float]] = mapped_column(Numeric)
    longitude: Mapped[Optional[float]] = mapped_column(Numeric)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

    cliente: Mapped["Cliente"] = relationship(back_populates="pontos")
    documentos: Mapped[List["Documento"]] = relationship(back_populates="ponto")


class Processo(Base):
    __tablename__ = "processos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    numero_processo: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    orgao_ambiental: Mapped[str] = mapped_column(String(100), nullable=False)
    descricao: Mapped[Optional[str]] = mapped_column(Text)
    status_atual: Mapped[str] = mapped_column(String(50), nullable=False)
    data_protocolo: Mapped[Optional[date]] = mapped_column(Date)
    ultima_atualizacao: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    cliente: Mapped["Cliente"] = relationship(back_populates="processos")
    documentos: Mapped[List["Documento"]] = relationship(back_populates="processo")


class Documento(Base):
    __tablename__ = "documentos"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    ponto_id: Mapped[Optional[int]] = mapped_column(ForeignKey("pontos_monitoramento.id"))
    processo_id: Mapped[Optional[int]] = mapped_column(ForeignKey("processos.id"))
    tipo_documento: Mapped[str] = mapped_column(String(50), nullable=False)
    competencia: Mapped[Optional[date]] = mapped_column(Date) 
    url_arquivo: Mapped[str] = mapped_column(String(500), nullable=False)
    data_upload: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente: Mapped["Cliente"] = relationship(back_populates="documentos")
    ponto: Mapped[Optional["PontoMonitoramento"]] = relationship(back_populates="documentos")
    processo: Mapped[Optional["Processo"]] = relationship(back_populates="documentos")
    notificacoes: Mapped[List["NotificacaoWhatsApp"]] = relationship(back_populates="documento")


class NotificacaoWhatsApp(Base):
    __tablename__ = "notificacoes_whatsapp"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    documento_id: Mapped[Optional[int]] = mapped_column(ForeignKey("documentos.id"))
    numero_destino: Mapped[str] = mapped_column(String(20), nullable=False)
    mensagem: Mapped[str] = mapped_column(Text, nullable=False)
    status_envio: Mapped[str] = mapped_column(String(20), nullable=False) 
    data_envio: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    cliente: Mapped["Cliente"] = relationship(back_populates="notificacoes")
    documento: Mapped[Optional["Documento"]] = relationship(back_populates="notificacoes")

# ==========================================
# TABELA DE AUDITORIA (LOGS)
# ==========================================
class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    
    # O que o usuário fez? (Ex: "LOGIN", "DOWNLOAD_DOCUMENTO")
    evento = Column(String, nullable=False) 
    
    # Qual documento ele baixou? (Ex: "documento_id: 15")
    detalhes = Column(String, nullable=True) 
    
    # Rastro Digital
    ip = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    user_agent = Column(String, nullable=True) # Qual navegador/celular ele usou?
    
    # Carimbo de tempo exato (UTC)
    data_hora = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Cria o atalho para acessar os dados do usuário a partir do log
    usuario = relationship("Usuario")    