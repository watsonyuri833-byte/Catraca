# -*- coding: utf-8 -*-
import os
import json
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from supabase import create_client, Client
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# 1. CARREGAR VARIÁVEIS OCULTAS
# ==========================================
# Puxa as informações do seu arquivo .env sem expor no código
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = os.getenv("API_KEY") # PUXA A SUA SENHA DO .ENV

# Validação de segurança
if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, API_KEY]):
    raise ValueError("Faltam variáveis de ambiente! Verifique se o seu arquivo .env está configurado corretamente.")

# Senha segura oculta
MINHA_CHAVE_DE_API = API_KEY 

# Inicializando conexões
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="API Cliente - actuar.group")

# ==========================================
# 2. MODELO DE DADOS
# ==========================================
class PerguntaCliente(BaseModel):
    duvida: str

# ==========================================
# 3. LÓGICA DE BUSCA NO BANCO (BUSCA SEMÂNTICA)
# ==========================================
def buscar_contexto_relevante():
    try:
        # Trazemos até 200 ocorrências do banco para a IA analisar o sentido
        res = supabase.table("ocorrencias").select("problema, motivo, solucao").limit(200).execute()
        return res.data if res.data else []
        
    except Exception as e:
        print(f"Erro ao buscar no banco de dados: {e}")
        return []

# ==========================================
# 4. MOTOR DA IA (Pesquisa por Significado)
# ==========================================
def gerar_resposta_cliente(duvida: str, contexto_ocor: list):
    prompt_sistema = """Você é o Assistente Virtual Técnico para o cliente final (Dono de academia, escola).
Sua missão é ajudar o cliente a resolver problemas com catracas e sistemas de acesso de forma muito simples e direta.

DIRETRIZES DE PESQUISA POR SENTIDO:
1. Abaixo está a nossa Base de Conhecimento completa.
2. Analise a DÚVIDA DO CLIENTE e procure na base um problema que tenha o MESMO SIGNIFICADO ou CONTEXTO, mesmo que as palavras usadas sejam totalmente diferentes (ex: "apitar" = "bip" = "barulho sonoro" = "alarme").

DIRETRIZES DE RESPOSTA:
3. Se encontrar um problema com o mesmo sentido, entregue APENAS a solução em um passo a passo numerado, curto e direto ao ponto.
4. NUNCA explique a causa raiz, evite jargões técnicos.
5. Se o problema DEFINITIVAMENTE não estiver na base (nem por sentido), diga amigavelmente para abrir um chamado no suporte. Não invente soluções.
"""

    contexto_str = f"DÚVIDA DO CLIENTE: {duvida}\n\n=== BASE DE CONHECIMENTO TÉCNICO ===\n"
    if contexto_ocor:
        for o in contexto_ocor:
            passos_limpos = ""
            try:
                passos_json = json.loads(o.get('solucao', '[]'))
                for p in passos_json:
                    passos_limpos += f"{p.get('passo')} - {p.get('texto')}\n"
            except:
                passos_limpos = o.get('solucao', '')

            contexto_str += f"- PROBLEMA REGISTRADO: {o.get('problema')}\n  MOTIVO: {o.get('motivo')}\n  SOLUÇÃO: {passos_limpos}\n\n"
    else:
        contexto_str += "Base de dados vazia.\n"

    try:
        # Usando o modelo 1.5-flash pela sua alta capacidade de memória e contexto
        response = gemini_client.models.generate_content(
            model='gemini-1.5-flash',
            contents=contexto_str,
            config=types.GenerateContentConfig(
                system_instruction=prompt_sistema,
                temperature=0.1,
            )
        )
        return response.text
    except Exception as e:
        return "Ocorreu um erro ao processar sua dúvida. Por favor, contate o suporte."

# ==========================================
# 5. ROTA PRINCIPAL DA API
# ==========================================
@app.post("/api/v1/resolver-problema")
def resolver_problema(
    requisicao: PerguntaCliente, 
    token_acesso: str = Header(None)
):
    # Trava de Segurança
    if token_acesso != f"Bearer {MINHA_CHAVE_DE_API}":
        raise HTTPException(status_code=401, detail="Chave de API inválida. Acesso Negado.")

    # Busca todos os problemas (sem filtrar palavras)
    contexto = buscar_contexto_relevante()
    
    # A IA interpreta o sentido da dúvida comparando com toda a base
    resposta_formatada = gerar_resposta_cliente(requisicao.duvida, contexto)

    return {
        "status": "sucesso",
        "solucao_passo_a_passo": resposta_formatada
    }