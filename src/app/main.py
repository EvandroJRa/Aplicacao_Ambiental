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

# ==========================================
# INICIALIZAÇÃO E CONFIGURAÇÕES DA API
# ==========================================
app = FastAPI(title="API - Portal Ambiental", version="1.0.0")

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
async def criar_cliente(cliente: schemas.ClienteCreate, db: AsyncSession = Depends(get_db)):
    novo_cliente = Cliente(**cliente.model_dump())
    db.add(novo_cliente)
    await db.commit()
    await db.refresh(novo_cliente) 
    return novo_cliente

@app.get("/clientes/", response_model=List[schemas.ClienteResponse])
async def listar_clientes(db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(select(Cliente))
    return resultado.scalars().all()

# ==========================================
# ROTAS DE PONTOS DE MONITORAMENTO
# ==========================================
@app.post("/clientes/{cliente_id}/pontos/", response_model=schemas.PontoMonitoramentoResponse)
async def criar_ponto_monitoramento(
    cliente_id: int, 
    ponto: schemas.PontoMonitoramentoCreate, 
    db: AsyncSession = Depends(get_db)
):
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado no sistema.")

    novo_ponto = PontoMonitoramento(**ponto.model_dump(), cliente_id=cliente_id)
    db.add(novo_ponto)
    await db.commit()
    await db.refresh(novo_ponto)
    
    return novo_ponto

@app.get("/clientes/{cliente_id}/pontos/", response_model=List[schemas.PontoMonitoramentoResponse])
async def listar_pontos_do_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(
        select(PontoMonitoramento).where(PontoMonitoramento.cliente_id == cliente_id)
    )
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
    db: AsyncSession = Depends(get_db)
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
async def listar_documentos_do_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    resultado = await db.execute(
        select(Documento).where(Documento.cliente_id == cliente_id)
    )
    return resultado.scalars().all()