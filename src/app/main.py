import os
from datetime import date
from typing import List, Optional

# Importações do FastAPI (agora todas organizadas em uma linha só)
from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from fastapi.staticfiles import StaticFiles

# Importações do Banco de Dados
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Importando nossa conexão, modelos, schemas e serviços
from src.app.database.session import get_db
from src.app.models.models import Cliente, PontoMonitoramento, Documento
from src.app.schemas import schemas
from src.app.notificacoes import enviar_aviso_laudo_whatsapp

from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from src.app.seguranca import obter_hash_senha, verificar_senha, criar_token_acesso
from src.app.models.models import Usuario
from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.future import select
from src.app.seguranca import get_current_user

# ==========================================
# INICIALIZAÇÃO E CONFIGURAÇÕES DA API
# ==========================================
app = FastAPI(title="API - Portal Ambiental", version="1.0.0")

# O Guarda-Costas: Define que a rota de login é a "/token" (Deve ficar solto no código, logo após criar o 'app')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Transforma a pasta "storage" em uma URL acessível pelo navegador
os.makedirs("storage", exist_ok=True)
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

@app.get("/")
def raiz():
    return {"mensagem": "O motor da API Ambiental está rodando perfeitamente!"}

# ==========================================
# ROTAS DE CLIENTES
# ==========================================
@app.post("/clientes/", response_model=schemas.ClienteResponse)
async def criar_cliente(
    cliente: schemas.ClienteCreate, 
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme) # <--- O Segurança da porta!
):
    novo_cliente = Cliente(**cliente.model_dump())
    db.add(novo_cliente) 
    await db.commit()
    await db.refresh(novo_cliente) 
    return novo_cliente

@app.get("/clientes/", response_model=List[schemas.ClienteResponse])
async def listar_clientes(
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme) # <--- CADEADO AQUI
):
    resultado = await db.execute(select(Cliente))
    return resultado.scalars().all()

# ==========================================
# ROTAS DE PONTOS DE MONITORAMENTO
# ==========================================
@app.post("/clientes/{cliente_id}/pontos/", response_model=schemas.PontoMonitoramentoResponse)
async def criar_ponto_monitoramento(
    cliente_id: int, 
    ponto: schemas.PontoMonitoramentoCreate, 
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme) # <--- CADEADO AQUI
):
    novo_ponto = PontoMonitoramento(**ponto.model_dump(), cliente_id=cliente_id)
    db.add(novo_ponto)
    await db.commit()
    await db.refresh(novo_ponto)
    return novo_ponto

@app.get("/clientes/{cliente_id}/pontos/", response_model=List[schemas.PontoMonitoramentoResponse])
async def listar_pontos_do_cliente(
    cliente_id: int, 
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme) # <--- CADEADO AQUI
):
    resultado = await db.execute(select(PontoMonitoramento).where(PontoMonitoramento.cliente_id == cliente_id))
    return resultado.scalars().all()

# ==========================================
# ROTAS DE DOCUMENTOS E UPLOAD
# ==========================================
FORMATOS_PERMITIDOS = [
    "application/pdf", 
    "image/jpeg",      
    "image/png",       
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document" 
]

# AQUI ESTÁ A MÁGICA: background_tasks injetado na rota certa!
@app.post("/clientes/{cliente_id}/documentos/", response_model=schemas.DocumentoResponse)
async def upload_documento(
    cliente_id: int,
    background_tasks: BackgroundTasks, 
    tipo_documento: str = Form(...),
    ponto_id: Optional[int] = Form(None),
    competencia: Optional[date] = Form(None),
    arquivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    token: str = Depends(oauth2_scheme) # <--- CADEADO AQUI
    
):
    
    if ponto_id == 0:
        ponto_id = None
        
    # 1. Validação de Segurança
    if arquivo.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato inválido ({arquivo.content_type}). Envie apenas PDF, Imagens (JPG/PNG), Excel ou Word."
        )

    # 2. Verifica se o cliente existe
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # 3. Salva o arquivo fisicamente
    caminho_arquivo = f"storage/{cliente_id}_{arquivo.filename}"
    with open(caminho_arquivo, "wb") as buffer:
        buffer.write(await arquivo.read())

    # 4. Salva o registro no banco de dados
    novo_doc = Documento(
        cliente_id=cliente_id,
        ponto_id=ponto_id,
        tipo_documento=tipo_documento,
        competencia=competencia,
        url_arquivo=caminho_arquivo 
    )
    
    db.add(novo_doc)
    await db.commit()
    await db.refresh(novo_doc)

    # 5. Gatilho da Notificação em Segundo Plano (WhatsApp)
    if cliente and cliente.whatsapp_contato:
        numero_disparo = os.getenv("MEU_NUMERO_TESTE") 
        
        background_tasks.add_task(
            enviar_aviso_laudo_whatsapp,
            numero_destino=numero_disparo,
            nome_cliente=cliente.nome,
            nome_documento=novo_doc.tipo_documento
        )

    # 6. Resposta Imediata
    return novo_doc

@app.get("/clientes/{cliente_id}/documentos/", response_model=List[schemas.DocumentoResponse])
async def listar_documentos_do_cliente(
    cliente_id: int, 
    db: AsyncSession = Depends(get_db),
    # ==================================================
    # É ESTA LINHA AQUI QUE FAZ O BOTÃO APARECER NA TELA:
    token: str = Depends(oauth2_scheme) 
    # ==================================================
):
    resultado = await db.execute(
        select(Documento).where(Documento.cliente_id == cliente_id)
    )
    return resultado.scalars().all()

# ==========================================
# ROTAS DE USUÁRIOS E SEGURANÇA
# ==========================================

@app.post("/usuarios/", response_model=schemas.UsuarioResponse)
async def criar_usuario(usuario: schemas.UsuarioCreate, db: AsyncSession = Depends(get_db)):
    # 1. Verifica se o e-mail já existe no banco
    resultado = await db.execute(select(Usuario).where(Usuario.email == usuario.email))
    usuario_existente = resultado.scalars().first()
    
    if usuario_existente:
        raise HTTPException(status_code=400, detail="Este e-mail já está cadastrado.")

    # 2. Embaralha a senha antes de salvar
    senha_criptografada = obter_hash_senha(usuario.senha)
    
    # 3. Salva no banco de dados
    novo_usuario = Usuario(
        email=usuario.email,
        senha_hash=senha_criptografada,
        cliente_id=usuario.cliente_id
    )
    
    db.add(novo_usuario)
    await db.commit()
    await db.refresh(novo_usuario)
    
    return novo_usuario

@app.get("/usuarios/", response_model=list[schemas.UsuarioResponse])
async def listar_usuarios(
    db: AsyncSession = Depends(get_db),
    current_user: Usuario = Depends(get_current_user) # <-- Protegido pelo cadeado!
):
    # Busca todos os usuários no banco de dados
    resultado = await db.execute(select(Usuario))
    usuarios = resultado.scalars().all()
    return usuarios

@app.post("/token", response_model=schemas.Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    # O OAuth2PasswordRequestForm usa o padrão 'username' e 'password'. 
    # No nosso caso, o 'username' será o e-mail digitado pelo usuário.
    
    # 1. Busca o usuário no banco pelo e-mail
    resultado = await db.execute(select(Usuario).where(Usuario.email == form_data.username))
    usuario = resultado.scalars().first()

    # 2. Verifica se o usuário existe e se a senha bate
    if not usuario or not verificar_senha(form_data.password, usuario.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-mail ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Se deu tudo certo, fabrica o "crachá" (Token JWT)
    # Colocamos o email e o ID do cliente dentro do token para usarmos nas outras rotas depois
    dados_token = {
        "sub": usuario.email, 
        "cliente_id": usuario.cliente_id
    }
    token_gerado = criar_token_acesso(dados=dados_token)
    
    return {"access_token": token_gerado, "token_type": "bearer"}

