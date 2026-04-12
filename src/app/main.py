from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import os
from datetime import date
from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form

# Importando nossa conexão, modelos e schemas
from src.app.database.session import get_db
from src.app.models.models import Cliente
from src.app.schemas import schemas
from src.app.models.models import Cliente, PontoMonitoramento
from src.app.models.models import Cliente, PontoMonitoramento, Documento


# Inicializa o FastAPI
app = FastAPI(title="API - Portal Ambiental", version="1.0.0")

@app.get("/")
def raiz():
    return {"mensagem": "O motor da API Ambiental está rodando perfeitamente!"}

# Rota para CADASTRAR um cliente
@app.post("/clientes/", response_model=schemas.ClienteResponse)
async def criar_cliente(cliente: schemas.ClienteCreate, db: AsyncSession = Depends(get_db)):
    # 1. Prepara os dados
    novo_cliente = Cliente(**cliente.model_dump())
    
    # 2. Adiciona e salva no banco
    db.add(novo_cliente)
    await db.commit()
    await db.refresh(novo_cliente) # Atualiza para pegar o ID que o banco gerou
    
    return novo_cliente

# Rota para LISTAR todos os clientes
@app.get("/clientes/", response_model=List[schemas.ClienteResponse])
async def listar_clientes(db: AsyncSession = Depends(get_db)):
    # Faz um SELECT * FROM clientes de forma assíncrona
    resultado = await db.execute(select(Cliente))
    clientes = resultado.scalars().all()
    return clientes

# Rota para CADASTRAR um Ponto de Monitoramento para um Cliente específico
@app.post("/clientes/{cliente_id}/pontos/", response_model=schemas.PontoMonitoramentoResponse)
async def criar_ponto_monitoramento(
    cliente_id: int, 
    ponto: schemas.PontoMonitoramentoCreate, 
    db: AsyncSession = Depends(get_db)
):
    # 1. Verifica se o cliente existe antes de criar o poço
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado no sistema.")

    # 2. Cria o ponto vinculando automaticamente ao ID do cliente da URL
    novo_ponto = PontoMonitoramento(**ponto.model_dump(), cliente_id=cliente_id)
    db.add(novo_ponto)
    await db.commit()
    await db.refresh(novo_ponto)
    
    return novo_ponto

# Rota para LISTAR todos os Pontos de um Cliente específico
@app.get("/clientes/{cliente_id}/pontos/", response_model=List[schemas.PontoMonitoramentoResponse])
async def listar_pontos_do_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    # Faz um SELECT * FROM pontos_monitoramento WHERE cliente_id = X
    resultado = await db.execute(
        select(PontoMonitoramento).where(PontoMonitoramento.cliente_id == cliente_id)
    )
    return resultado.scalars().all()

# Rota de Upload de Documento para um Ponto de Monitoramento específico

os.makedirs("storage", exist_ok=True)

# --- LISTA VIP DE FORMATOS (Pode adicionar outros no futuro) ---
FORMATOS_PERMITIDOS = [
    "application/pdf", # PDFs (Laudos e Ofícios)
    "image/jpeg",      # Fotos de campo
    "image/png",       # Fotos de campo
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # Planilhas Excel (.xlsx)
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document" # Word (.docx)
]

@app.post("/clientes/{cliente_id}/documentos/", response_model=schemas.DocumentoResponse)
async def upload_documento(
    cliente_id: int,
    tipo_documento: str = Form(...),
    ponto_id: Optional[int] = Form(None),
    competencia: Optional[date] = Form(None),
    arquivo: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # 1. VALIDAÇÃO DE SEGURANÇA (O Escudo anti-estagiário)
    if arquivo.content_type not in FORMATOS_PERMITIDOS:
        raise HTTPException(
            status_code=400, 
            detail=f"Formato inválido ({arquivo.content_type}). Envie apenas PDF, Imagens (JPG/PNG), Excel ou Word."
        )

    # 2. Verifica se o cliente existe
    cliente = await db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # 3. Salva o arquivo fisicamente na pasta 'storage'
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
    
    return novo_doc

# TRANSFORMA A PASTA "STORAGE" EM UMA URL ACESSÍVEL PELO NAVEGADOR
app.mount("/storage", StaticFiles(directory="storage"), name="storage")

@app.get("/clientes/{cliente_id}/documentos/", response_model=List[schemas.DocumentoResponse])
async def listar_documentos_do_cliente(cliente_id: int, db: AsyncSession = Depends(get_db)):
    # Faz um SELECT * FROM documentos WHERE cliente_id = X
    resultado = await db.execute(
        select(Documento).where(Documento.cliente_id == cliente_id)
    )
    return resultado.scalars().all()