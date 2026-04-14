import os
from datetime import datetime, timedelta, timezone # <-- Adicionamos o timezone aqui
from typing import Optional
from jose import jwt
from passlib.context import CryptContext
from dotenv import load_dotenv

# Carrega as variáveis de ambiente
load_dotenv()

# O "carimbo" oficial da sua empresa.
SECRET_KEY = os.getenv("SECRET_KEY", "chave_provisoria_mude_em_producao")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # O crachá vale por 24 horas

# Configuração do triturador de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def obter_hash_senha(senha: str) -> str:
    """Transforma a senha em hash e previne o erro de 72 bytes do bcrypt"""
    
    # Converte para bytes para contar o tamanho real (caracteres especiais valem mais)
    senha_bytes = senha.encode('utf-8')
    
    # Se a senha for maior que 72 bytes, nós a cortamos (truncamos) silenciosamente
    # Isso impede o crash e ainda mantém a senha segura
    if len(senha_bytes) > 50:
        senha = senha_bytes[:50].decode('utf-8', 'ignore')
        
    return pwd_context.hash(senha)

def verificar_senha(senha_texto_puro: str, senha_hash: str) -> bool:
    """Verifica se a senha digitada no login bate com o hash salvo no banco"""
    return pwd_context.verify(senha_texto_puro, senha_hash)

def criar_token_acesso(dados: dict, tempo_expiracao: Optional[timedelta] = None) -> str:
    """Cria o crachá digital (JWT) com as informações do usuário e o tempo de validade"""
    dados_copia = dados.copy()
    
    # ATUALIZAÇÃO: Pegando a hora atual com o fuso horário UTC embutido
    agora = datetime.now(timezone.utc)
    
    if tempo_expiracao:
        expira = agora + tempo_expiracao
    else:
        expira = agora + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
    dados_copia.update({"exp": expira})
    
    # Fabrica e assina o token com a nossa chave secreta
    token_codificado = jwt.encode(dados_copia, SECRET_KEY, algorithm=ALGORITHM)
    return token_codificado