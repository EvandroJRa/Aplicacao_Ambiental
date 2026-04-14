import asyncio
from src.app.database.session import engine
from src.app.models.models import Base

async def atualizar_banco():
    print("🔌 Conectando ao banco de dados PostgreSQL...")
    async with engine.begin() as conn:
        print("🏗️ Analisando modelos e criando tabelas faltantes...")
        # O SQLAlchemy é inteligente: ele só cria o que não existe. 
        # Ele NÃO vai apagar seus clientes e documentos antigos.
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Banco de dados atualizado com sucesso! A tabela 'usuarios' agora existe.")

if __name__ == "__main__":
    asyncio.run(atualizar_banco())