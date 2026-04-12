# 🌿 Portal Ambiental - API

API desenvolvida para o gerenciamento de relatórios de monitoramento de efluentes, poços, ofícios e processos de consultoria ambiental. Focada em automação e integração futura via WhatsApp.

## 🚀 Tecnologias Utilizadas

* **Linguagem:** Python 3.12+
* **Framework Web:** FastAPI
* **Banco de Dados:** PostgreSQL (via Docker)
* **ORM:** SQLAlchemy 2.0 (Assíncrono)
* **Migrações:** Alembic
* **Validação de Dados:** Pydantic

## ⚙️ Pré-requisitos

Para rodar este projeto, você precisará ter instalado em sua máquina:
* [Docker e Docker Compose V2](https://docs.docker.com/engine/install/)
* [Python 3.12+](https://www.python.org/downloads/)

## 🛠️ Configuração do Ambiente Local

**1. Clone ou acesse a pasta do projeto:**
\`\`\`bash
cd Aplicacao_Ambiental
\`\`\`

**2. Crie o arquivo de variáveis de ambiente:**
Crie um arquivo \`.env\` na raiz do projeto (este arquivo é ignorado pelo Git por segurança) e adicione a string de conexão:
\`\`\`text
DATABASE_URL=postgresql+asyncpg://usuario:senha@localhost:5432/nome_do_banco
\`\`\`

**3. Inicie o Banco de Dados com Docker:**
\`\`\`bash
sudo docker compose up -d
\`\`\`

**4. Crie as tabelas no banco de dados:**
\`\`\`bash
alembic upgrade head
\`\`\`

**5. Instale as dependências e inicie o servidor:**
\`\`\`bash
pip install fastapi pydantic uvicorn sqlalchemy asyncpg alembic python-dotenv
uvicorn src.app.main:app --reload
\`\`\`

## 📖 Documentação da API

Com o servidor rodando, acesse a documentação interativa gerada automaticamente pelo Swagger:
* **Acesso:** [http://localhost:8000/docs](http://localhost:8000/docs)