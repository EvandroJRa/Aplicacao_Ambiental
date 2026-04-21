import os
import sys
import uuid
import hashlib
import logging
from datetime import date, datetime, timezone
from typing import List, Optional

from fastapi import (
    FastAPI, Depends, HTTPException, status,
    UploadFile, File, Form, BackgroundTasks, Request
)
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.app.database.session import get_db
from src.app.models.models import Cliente, PontoMonitoramento, Documento, Usuario, Auditoria
from src.app.schemas import schemas
from src.app.notificacoes import notificar_documento_disponivel
from src.app.seguranca import (
    obter_hash_senha, verificar_senha,
    criar_token_acesso, get_current_user
)

# ==========================================
# LOGGING CENTRALIZADO
# ==========================================
logging.basicConfig(stream=sys.stderr, level=logging.INFO)
logger = logging.getLogger(__name__)

# ==========================================
# INICIALIZAÇÃO
# ==========================================
app = FastAPI(title="API - Portal Ambiental", version="1.0.0")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

os.makedirs("storage", exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

# ==========================================
# FORMATOS PERMITIDOS
# ==========================================
FORMATOS_PERMITIDOS = [
    "application/pdf",
    "image/jpeg",
    "image/png",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

# ==========================================
# HELPERS DE AUTORIZAÇÃO
# ==========================================
def exigir_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administradores."
        )
    return current_user


def exigir_acesso_cliente(
    cliente_id: int,
    current_user: Usuario = Depends(get_current_user)
) -> Usuario:
    if not current_user.is_admin and current_user.cliente_id != cliente_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não tem permissão para acessar dados deste cliente."
        )
    return current_user


# ==========================================
# ROTA RAIZ
# ==========================================
@app.get("/")
def raiz():
    return {"mensagem": "O motor da API Ambiental está rodando perfeitamente!"}


# ==========================================
# ROTAS DE CLIENTES
# ==========================================
@app.post("/clientes/")
async def criar_cliente_completo(
    dados: schemas.ClienteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(exigir_admin)
):
    query_conflito = await db.execute(
        select(Cliente).where(
            (Cliente.email == dados.email) |
            (Cliente.cnpj == dados.cnpj) |
            (Cliente.whatsapp_contato == dados.whatsapp_contato)
        )
    )
    conflito = query_conflito.scalars().first()

    if conflito:
        if conflito.email == dados.email:
            campo = "E-mail"
        elif conflito.cnpj == dados.cnpj:
            campo = "CNPJ"
        else:
            campo = "WhatsApp"
        raise HTTPException(
            status_code=400,
            detail=f"Bloqueio de Integridade: {campo} já está em uso por outra empresa."
        )

    try:
        novo_cliente = Cliente(
            nome=dados.nome,
            cnpj=dados.cnpj,
            whatsapp_contato=dados.whatsapp_contato,
            email=dados.email,
            codigo_identificador=dados.codigo_cliente
        )
        db.add(novo_cliente)
        await db.flush()

        novo_usuario = Usuario(
            email=dados.email,
            senha_hash=obter_hash_senha(dados.senha_provisoria),
            cliente_id=novo_cliente.id,
            exigir_troca_senha=True  # TODO: implementar fluxo antes do deploy em produção
        )
        db.add(novo_usuario)

        novo_log = Auditoria(
            usuario_id=current_user.id,
            email_usuario=current_user.email,
            evento="CADASTRO_CLIENTE_FULL",
            detalhes=f"Novo cliente: {dados.nome} | CNPJ: {dados.cnpj}",
            data_hora=datetime.now(timezone.utc)
        )
        db.add(novo_log)

        await db.commit()
        return {"status": "sucesso", "id": novo_cliente.id, "mensagem": "Cliente e usuário criados corretamente."}

    except Exception as e:
        await db.rollback()
        logger.exception("Erro ao criar cliente")
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")


@app.get("/clientes/")
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(exigir_admin)
):
    result = await db.execute(select(Cliente))
    clientes = result.scalars().all()
    return [
        {
            "id": c.id,
            "nome": c.nome,
            "cnpj": c.cnpj,
            "email": c.email,
            "whatsapp_contato": c.whatsapp_contato,
            "codigo_identificador": c.codigo_identificador
        }
        for c in clientes
    ]


# ==========================================
# ROTAS DE PONTOS DE MONITORAMENTO
# ==========================================
@app.post("/clientes/{cliente_id}/pontos/", response_model=schemas.PontoMonitoramentoResponse)
async def criar_ponto_monitoramento(
    cliente_id: int,
    ponto: schemas.PontoMonitoramentoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    exigir_acesso_cliente(cliente_id, current_user)
    novo_ponto = PontoMonitoramento(**ponto.model_dump(), cliente_id=cliente_id)
    db.add(novo_ponto)
    await db.commit()
    await db.refresh(novo_ponto)
    return novo_ponto


@app.get("/clientes/{cliente_id}/pontos/", response_model=List[schemas.PontoMonitoramentoResponse])
async def listar_pontos_do_cliente(
    cliente_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    exigir_acesso_cliente(cliente_id, current_user)
    resultado = await db.execute(
        select(PontoMonitoramento).where(PontoMonitoramento.cliente_id == cliente_id)
    )
    return resultado.scalars().all()


# ==========================================
# ROTAS DE DOCUMENTOS
# ==========================================
@app.post("/clientes/{cliente_id}/documentos/", response_model=schemas.DocumentoResponse)
async def upload_documento(
    cliente_id: int,
    background_tasks: BackgroundTasks,
    tipo_documento: str = Form(...),
    ponto_id: Optional[int] = Form(None),
    processo_id: Optional[int] = Form(None),
    competencia: Optional[date] = Form(None),
    arquivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    exigir_acesso_cliente(cliente_id, current_user)

    if ponto_id == 0:
        ponto_id = None

    if arquivo.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Formato inválido ({arquivo.content_type}). Envie apenas PDF, JPG, PNG, Excel ou Word."
        )

    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # Sanitiza nome e garante unicidade
    nome_seguro = os.path.basename(arquivo.filename or "arquivo")
    nome_unico = f"{cliente_id}_{uuid.uuid4().hex}_{nome_seguro}"
    caminho_arquivo = os.path.join("storage", nome_unico)

    # Lê o conteúdo uma única vez
    conteudo = await arquivo.read()

    # Calcula hash SHA-256 — prova de integridade do documento
    hash_sha256 = hashlib.sha256(conteudo).hexdigest()

    # Persiste no banco ANTES de salvar em disco
    novo_doc = Documento(
        cliente_id=cliente_id,
        ponto_id=ponto_id,
        processo_id=processo_id,
        tipo_documento=tipo_documento,
        competencia=competencia,
        url_arquivo=caminho_arquivo,
        hash_arquivo=hash_sha256
    )
    db.add(novo_doc)

    try:
        await db.commit()
        await db.refresh(novo_doc)
    except Exception as e:
        await db.rollback()
        logger.exception("Erro ao salvar documento no banco")
        raise HTTPException(status_code=500, detail=f"Erro ao registrar documento: {str(e)}")

    # Salva o arquivo em disco apenas após commit bem-sucedido
    with open(caminho_arquivo, "wb") as buffer:
        buffer.write(conteudo)

    # Dispara WhatsApp + E-mail em segundo plano
    if cliente.whatsapp_contato and cliente.email:
        numero_disparo = os.getenv("MEU_NUMERO_TESTE", cliente.whatsapp_contato)
        background_tasks.add_task(
            notificar_documento_disponivel,
            email_destino=cliente.email,
            numero_whatsapp=numero_disparo,
            nome_cliente=cliente.nome,
            nome_documento=novo_doc.tipo_documento,
            hash_arquivo=hash_sha256
        )

    logger.info(f"[UPLOAD] '{tipo_documento}' | Cliente {cliente_id} | Hash: {hash_sha256}")
    return novo_doc


@app.get("/clientes/{cliente_id}/documentos/", response_model=List[schemas.DocumentoResponse])
async def listar_documentos_do_cliente(
    cliente_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    exigir_acesso_cliente(cliente_id, current_user)
    resultado = await db.execute(
        select(Documento).where(Documento.cliente_id == cliente_id)
    )
    return resultado.scalars().all()


# ==========================================
# ROTAS DE USUÁRIOS
# ==========================================
@app.post("/usuarios/", response_model=schemas.UsuarioResponse)
async def criar_usuario(
    usuario: schemas.UsuarioCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(exigir_admin)
):
    resultado = await db.execute(select(Usuario).where(Usuario.email == usuario.email))
    if resultado.scalars().first():
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    novo_usuario = Usuario(
        email=usuario.email,
        senha_hash=obter_hash_senha(usuario.senha),
        cliente_id=usuario.cliente_id
    )
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)
    return novo_usuario


@app.get("/usuarios/", response_model=List[schemas.UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(exigir_admin)
):
    resultado = await db.execute(select(Usuario))
    return resultado.scalars().all()


# ==========================================
# ROTA DE LOGIN — com registro de auditoria
# ==========================================
@app.post("/token", response_model=schemas.Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    resultado = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    usuario = resultado.scalars().first()

    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Captura IP e user agent do login
    ip_proxy = request.headers.get("x-forwarded-for")
    ip_login = ip_proxy.split(",")[0].strip() if ip_proxy else (
        request.client.host if request.client else "desconhecido"
    )
    user_agent_login = request.headers.get("user-agent")

    # Busca nome da empresa
    nome_empresa = "Admin/Apoio"
    if usuario.cliente_id:
        cliente_db = await db.get(Cliente, usuario.cliente_id)
        if cliente_db:
            nome_empresa = cliente_db.nome

    # Registra LOGIN na auditoria
    log_login = Auditoria(
        usuario_id=usuario.id,
        cliente_id=usuario.cliente_id,
        email_usuario=usuario.email,
        nome_empresa=nome_empresa,
        evento="LOGIN",
        detalhes="Login realizado com sucesso.",
        ip=ip_login,
        user_agent=user_agent_login,
        data_hora=datetime.now(timezone.utc)
    )
    db.add(log_login)
    await db.commit()

    dados_token = {
        "sub": usuario.email,
        "cliente_id": usuario.cliente_id,
        "is_admin": usuario.is_admin,
    }
    token_gerado = criar_token_acesso(dados=dados_token)

    return {
        "access_token": token_gerado,
        "token_type": "bearer",
        "is_admin": usuario.is_admin,
    }


# ==========================================
# ROTA DE PING (HEARTBEAT)
# ==========================================
@app.post("/usuarios/ping")
async def usuario_ping(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    current_user.ultima_atividade = datetime.now(timezone.utc)
    await db.commit()
    return {"status": "online", "timestamp": current_user.ultima_atividade}


# ==========================================
# ROTAS DE AUDITORIA
# ==========================================
@app.post("/auditoria/", status_code=201)
async def registrar_auditoria(
    item: schemas.AuditoriaCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    logger.info(f"[AUDITORIA] {item.evento} | {current_user.email} | IP: {item.ip}")

    # Resolve IP
    valores_invalidos = {"", "None", "null", "Não capturado", "Aguardando JS..."}
    ip_final = item.ip if item.ip and item.ip not in valores_invalidos else None

    if not ip_final:
        ip_proxy = request.headers.get("x-forwarded-for")
        ip_final = ip_proxy.split(",")[0].strip() if ip_proxy else (
            request.client.host if request.client else "desconhecido"
        )

    # Resolve user agent — prioriza o que o portal enviou
    user_agent_final = item.user_agent or request.headers.get("user-agent")

    nome_empresa = "Admin/Apoio"
    if current_user.cliente_id:
        cliente_db = await db.get(Cliente, current_user.cliente_id)
        if cliente_db:
            nome_empresa = cliente_db.nome

    novo_log = Auditoria(
        usuario_id=current_user.id,
        cliente_id=current_user.cliente_id,
        email_usuario=current_user.email,
        nome_empresa=nome_empresa,
        evento=item.evento,
        detalhes=item.detalhes,
        ip=ip_final,
        latitude=item.latitude,
        longitude=item.longitude,
        user_agent=user_agent_final,
        data_hora=datetime.now(timezone.utc)
    )

    db.add(novo_log)
    await db.commit()

    return {"status": "registrado", "evento": item.evento, "ip_rastreado": ip_final}


@app.get("/auditoria/")
async def listar_auditoria(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(exigir_admin)
):
    result = await db.execute(select(Auditoria).order_by(Auditoria.data_hora.desc()))
    return result.scalars().all()


# ==========================================
# ROTA DE TESTE DE UPLOAD
# ==========================================
@app.post("/testar-upload/")
async def testar_upload(
    arquivo: UploadFile = File(...),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        conteudo = await arquivo.read()
        return {
            "status": "sucesso",
            "arquivo_recebido": arquivo.filename,
            "tamanho_bytes": len(conteudo),
            "mensagem": "A API recebeu o arquivo corretamente!"
        }
    except Exception as e:
        logger.exception("Erro no teste de upload")
        raise HTTPException(status_code=500, detail=f"Erro no teste de upload: {str(e)}")
