# 🌿 Portal Ambiental

Sistema completo para gestão de consultoria ambiental, com controle de clientes, pontos de monitoramento, disponibilização de laudos técnicos e auditoria eletrônica de acessos.

---

## 🚀 Arquitetura e Tecnologias

| Camada | Tecnologia |
|---|---|
| Backend (API) | FastAPI + SQLAlchemy Assíncrono |
| Banco de Dados | PostgreSQL (Docker local / Render em produção) |
| Migrações | Alembic |
| Frontend | Streamlit |
| Segurança | JWT (OAuth2) + Passlib bcrypt |
| Infra | Docker Compose (local) / Render (produção) |

---

## ✨ Funcionalidades

- [x] Cadastro relacional de Clientes com usuário vinculado
- [x] Pontos de Monitoramento por cliente (Poços, Efluentes, etc.)
- [x] Upload de laudos com validação de formato (PDF, Excel, Word, Imagens)
- [x] Nomes de arquivo sanitizados com UUID para evitar colisões e path traversal
- [x] Portal do Cliente — visualização e download de laudos
- [x] Painel Administrativo — backoffice da equipe interna
- [x] Auditoria eletrônica com IP, geolocalização e timestamp
- [x] Heartbeat de sessão (última atividade do usuário em tempo real)
- [x] Notificação via WhatsApp ao fazer upload de novo documento

---

## 🖥️ Interfaces

### Portal do Cliente (`portal.py`)
Acesso exclusivo para clientes da consultoria. Permite visualizar e baixar laudos técnicos com registro de auditoria a cada download.

```bash
streamlit run portal.py
```

### Painel Administrativo (`admin.py`)
Backoffice restrito para a equipe interna. Permite cadastrar empresas, fazer upload de documentos e acompanhar logs de auditoria.

```bash
streamlit run admin.py --server.port 8502
```

---

## ⚙️ Configuração do Ambiente

### 1. Variáveis de Ambiente
Crie um arquivo `.env` na raiz do projeto:

```env
SECRET_KEY=sua_chave_secreta_aqui
DATABASE_URL=postgresql+asyncpg://usuario:senha@localhost:5432/ambiental
MEU_NUMERO_TESTE=5500000000000
```

### 2. Backend e Banco de Dados

```bash
# Sobe o banco via Docker
docker compose up -d

# Aplica as migrações
alembic upgrade head

# Instala dependências
pip install fastapi pydantic uvicorn sqlalchemy asyncpg alembic \
            python-dotenv python-multipart passlib[bcrypt] python-jose

# Inicia a API
uvicorn src.app.main:app --reload
```

### 3. Frontend

```bash
pip install streamlit requests streamlit-js-eval \
            streamlit-autorefresh streamlit-javascript

# Portal do cliente
streamlit run portal.py

# Painel admin (porta separada)
streamlit run admin.py --server.port 8502
```

---

## 📖 Documentação da API

| Interface | URL |
|---|---|
| Swagger UI | http://localhost:8000/docs |
| Portal do Cliente | http://localhost:8501 |
| Painel Admin | http://localhost:8502 |

---

## 🔒 Segurança e Autenticação

A API usa OAuth2 com tokens JWT. As rotas são divididas em três níveis de acesso:

| Nível | Rotas |
|---|---|
| Público | `POST /token` |
| Autenticado (cliente) | `GET /clientes/{id}/documentos/`, `GET /clientes/{id}/pontos/`, `POST /auditoria/`, `POST /usuarios/ping` |
| Admin only | `POST /clientes/`, `GET /clientes/`, `POST /usuarios/`, `GET /usuarios/`, `GET /auditoria/` |

### Como autenticar via Swagger:
1. Acesse `/docs`
2. Clique em **Authorize**
3. Insira e-mail (campo `username`) e senha
4. Todas as rotas com 🔒 ficam liberadas

---

## 🛡️ Camada de Auditoria

Cada download de documento registra automaticamente:

| Campo | Descrição |
|---|---|
| `data_hora` | Timestamp UTC do evento |
| `email_usuario` | Usuário autenticado |
| `nome_empresa` | Empresa vinculada ao usuário |
| `evento` | Tipo de ação (ex: `DOWNLOAD_DOCUMENTO`) |
| `ip` | IP real capturado via JS (fallback: header do proxy) |
| `latitude` / `longitude` | Coordenadas GPS do dispositivo (quando permitido) |

---

## 📋 Roadmap

- [x] Infraestrutura — Login, Upload, Download Seguro
- [x] Auditoria eletrônica com IP e geolocalização
- [x] Separação de permissões admin vs. cliente
- [ ] Fluxo de troca de senha obrigatória no primeiro acesso
- [ ] Painel de auditoria no admin com filtros e exportação
- [ ] Dashboard de telemetria (usuários online, downloads por período)
