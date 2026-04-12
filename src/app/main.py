from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

# Importando nossa conexão, modelos e schemas
from src.app.database.session import get_db
from src.app.models.models import Cliente
from src.app.schemas import schemas

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