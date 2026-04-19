import asyncio
from src.app.database.session import engine
# IMPORTANTE: Importamos todos os modelos explicitamente. 
# Isso garante que o SQLAlchemy registre todas as tabelas no Metadata.
from src.app.models.models import (
    Base, Cliente, Usuario, Auditoria, 
    PontoMonitoramento, Processo, Documento, NotificacaoWhatsApp
)

async def atualizar_banco():
    print("🔌 Conectando ao banco de dados PostgreSQL...")
    
    async with engine.begin() as conn:
        print("🏗️ Analisando modelos e sincronizando estrutura...")
        
        # O create_all só cria o que não existe. 
        # Se o reset_banco.py falhou em apagar a tabela 'auditoria' (por conexões ativas),
        # esta função não vai adicionar a coluna 'cliente_id' sozinha.
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Banco de dados sincronizado com sucesso!")
    print(f"📋 Tabelas detectadas: {', '.join(Base.metadata.tables.keys())}")

if __name__ == "__main__":
    asyncio.run(atualizar_banco())