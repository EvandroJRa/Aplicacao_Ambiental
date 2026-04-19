from datetime import datetime, timezone, date
from typing import List, Optional
from sqlalchemy import Column, String, Text, Boolean, Numeric, Date, DateTime, ForeignKey, func, Integer, Float
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# ==========================================
# 1. CLASSE BASE
# ==========================================
class Base(DeclarativeBase):
    pass

# ==========================================
# 2. MODELOS DO BANCO DE DADOS
# ==========================================

class Cliente(Base):
    __tablename__ = "clientes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # Novo campo para o código da sua consultoria (ex: CLI-001)
    codigo_identificador: Mapped[Optional[str]] = mapped_column(String(50), unique=True, index=True)
    
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    cnpj: Mapped[str] = mapped_column(String(18), unique=True, nullable=False)
    whatsapp_contato: Mapped[str] = mapped_column(String(20), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    criado_em: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relacionamentos
    usuarios: Mapped[List["Usuario"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    pontos: Mapped[List["PontoMonitoramento"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    processos: Mapped[List["Processo"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    documentos: Mapped[List["Documento"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")
    notificacoes: Mapped[List["NotificacaoWhatsApp"]] = relationship(back_populates="cliente", cascade="all, delete-orphan")


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    cliente_id: Mapped[int] = mapped_column(ForeignKey("clientes.id"), nullable=False)
    is_admin = Column(Boolean, default=False)
    
    # Campo de Status Online (Padronizado)
    ultima_atividade: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc), 
        onupdate=lambda: datetime.now(timezone.utc)
    )

    cliente: Mapped["Cliente"] = relationship(back_populates="usuarios")
    exigir_troca_senha: Mapped[bool] = mapped_column(Boolean, default=True)
    ultima_atividade: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Auditoria(Base):
    __tablename__ = "auditoria_registros"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    
    # Snapshot dos dados
    email_usuario: Mapped[Optional[str]] = mapped_column(String(255))
    nome_empresa: Mapped[Optional[str]] = mapped_column(String(255))
    cnpj_empresa: Mapped[Optional[str]] = mapped_column(String(18))
    telefone_empresa: Mapped[Optional[str]] = mapped_column(String(20))
    
    evento: Mapped[str] = mapped_column(String(100), nullable=False) 
    detalhes: Mapped[Optional[str]] = mapped_column(Text) 
    
    ip: Mapped[Optional[str]] = mapped_column(String(50))
    latitude: Mapped[Optional[float]] = mapped_column(Float)
    longitude: Mapped[Optional[float]] = mapped_column(Float)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500)) 
    
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario: Mapped["Usuario"] = relationship()

    data_hora: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    


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

