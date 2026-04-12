# 🌿 Portal Ambiental

Sistema completo para gestão de consultoria ambiental, permitindo o controle de clientes, pontos de monitoramento e disponibilização de laudos técnicos via portal web responsivo.

## 🚀 Arquitetura e Tecnologias

O sistema é dividido em dois motores principais:

* **Backend (API):** Desenvolvido com **FastAPI**, **SQLAlchemy** (Assíncrono) e **PostgreSQL** via Docker. Gerencia a inteligência e os dados.
* **Frontend (Portal):** Desenvolvido com **Streamlit**, focado em oferecer uma interface rápida e responsiva para o cliente final.
* **Banco de Dados:** **PostgreSQL** rodando em container Docker.
* **Migrações:** **Alembic** para versionamento de schemas de banco.

## ✨ Funcionalidades

- [x] Cadastro relacional de Clientes e Pontos de Monitoramento (Poços/Efluentes).
- [x] Upload de laudos (PDF, Excel, Word, Imagens) com validação de segurança.
- [x] Portal do Cliente com filtro dinâmico por empresa.
- [x] Download direto de arquivos via interface web com suporte a caracteres especiais.

## ⚙️ Configuração do Ambiente

### 1. Backend e Banco de Dados
Certifique-se de que o Docker está rodando e inicie o banco:
\`\`\`bash
docker compose up -d
alembic upgrade head
\`\`\`

Instale as dependências do backend e inicie a API:
\`\`\`bash
pip install fastapi pydantic uvicorn sqlalchemy asyncpg alembic python-dotenv python-multipart
uvicorn src.app.main:app --reload
\`\`\`

### 2. Frontend (Portal do Cliente)
Em um novo terminal, instale as dependências visuais e inicie o portal:
\`\`\`bash
pip install streamlit requests pandas
streamlit run frontend/app.py
\`\`\`

## 📖 Documentação da API
Acesse os endpoints e testes via Swagger:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Portal Web:** [http://localhost:8501](http://localhost:8501)