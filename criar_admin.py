import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
# Importamos explicitamente na ordem de dependência
from src.app.models.models import Base, Cliente, Usuario, Auditoria, Documento
from src.app.seguranca import obter_hash_senha

DATABASE_URL = ""

async def setup_inicial():
    engine = create_async_engine(DATABASE_URL, connect_args={"ssl": "require"})
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        print("🏗️  Sincronizando estrutura do banco...")
        # O Base.metadata contém todas as tabelas importadas acima
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        print("👤 Criando acessos administrativos...")
        try:
            # 1. Cria o Cliente Mestre
            admin_cliente = Cliente(
                nome="Admin",
                cnpj="00000000000000",
                whatsapp_contato="5500000000000",
                email="admin@admin.com.br"
            )
            session.add(admin_cliente)
            await session.flush() 

            # 2. Cria o Usuário Admin
            admin_user = Usuario(
                email="admin@admin.com",
                senha_hash=obter_hash_senha("xxx123"),
                cliente_id=admin_cliente.id
            )
            session.add(admin_user)
            await session.commit()
            print("✅ Sucesso! Tabelas criadas e Admin cadastrado.")
        except Exception as e:
            await session.rollback()
            print(f"❌ Erro ao inserir dados: {e}")

if __name__ == "__main__":
    asyncio.run(setup_inicial())