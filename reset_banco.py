import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# 1. SUA URL (Já com o ajuste manual para o motor assíncrono)
# Note o "postgresql+asyncpg://" no início
DATABASE_URL = ""

async def reset():
    # Adicionamos uma configuração extra para evitar problemas de SSL no Render
    engine = create_async_engine(
        DATABASE_URL,
        connect_args={"ssl": "require"} 
    )
    
    async with engine.begin() as conn:
        print("🛠️ Conectado! Apagando tabelas antigas...")
        await conn.execute(text("DROP TABLE IF EXISTS auditoria_registros CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS documentos CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS usuarios CASCADE;"))
        await conn.execute(text("DROP TABLE IF EXISTS clientes CASCADE;"))
        print("✅ Tabelas apagadas com sucesso!")

if __name__ == "__main__":
    asyncio.run(reset())