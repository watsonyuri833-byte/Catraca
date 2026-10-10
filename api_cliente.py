# -*- coding: utf-8 -*-
import os
import re
import json
import pandas as pd
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel
from supabase import create_client, Client
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# 1. CARREGAR VARIÁVEIS OCULTAS
# ==========================================
# Isso puxa as informações do seu arquivo .env sem expor no código
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = os.getenv("API_KEY") # PUXA A SUA SENHA DO .ENV

# Validação de segurança para garantir que o .env foi lido corretamente
if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, API_KEY]):
    raise ValueError("Faltam variáveis de ambiente! Verifique se o seu arquivo .env está configurado corretamente na pasta.")

# Essa é a senha que VOCÊ passa para o programador do seu chefe (AGORA SEGURA E OCULTA)
MINHA_CHAVE_DE_API = API_KEY 

# Inicializando conexões com as chaves ocultas
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

app = FastAPI(title="API Cliente - actuar.group")

# ==========================================
# 2. MODELO DE DADOS
# ==========================================
class PerguntaCliente(BaseModel):
    duvida: str

# ==========================================
# 3. LÓGICA DE BUSCA NO BANCO
# ==========================================
def buscar_contexto_relevante(query: str):
    try:
        res = supabase.table("ocorrencias").select("problema, motivo, solucao").execute()
        df_ocorrencias = pd.DataFrame(res.data)
        
        if df_ocorrencias.empty:
            return []

        query_lower = query.lower().strip()
        stopwords = {"a", "o", "de", "do", "da", "em", "um", "uma", "para", "com", "que", "os", "as"}
        palavras_query = [p for p in re.findall(r"\w+", query_lower) if p not in stopwords and len(p) > 2]

        resultados_ocor = []
        for _, row in df_ocorrencias.iterrows():
            texto_base = f"{row.get('problema', '')} {row.get('motivo', '')}".lower()
            score = sum(3 if p in str(row.get('problema', '')).lower() else 1 for p in palavras_query if p in texto_base)
            
            if score > 0:
                resultados_ocor.append((score, row.to_dict()))
        
        resultados_ocor.sort(key=lambda x: x[0], reverse=True)
        return [r[1] for r in resultados_ocor[:3]]
        
    except Exception as e:
        print(f"Erro no banco: {e}")
        return []

# ==========================================
# 4. MOTOR DA IA (O "Cérebro" simplificador)
# ==========================================
def gerar_resposta_cliente(duvida: str, contexto_ocor: list):
    prompt_sistema = """Você é o Assistente Virtual Técnico para o cliente final (Dono de academia, escola).
Sua missão é ajudar o cliente a resolver problemas com catracas e sistemas de acesso de forma muito simples e direta.

DIRETRIZES OBRIGATÓRIAS:
1. Baseie-se APENAS nas ocorrências fornecidas abaixo.
2. NUNCA explique a causa raiz, evite jargões técnicos.
3. Entregue APENAS a solução em um passo a passo numerado, curto e direto ao ponto.
4. Se o problema não estiver no contexto, diga amigavelmente para abrir um chamado no suporte.
"""

    contexto_str = f"DÚVIDA DO CLIENTE: {duvida}\n\n=== BASE TÉCNICA ===\n"
    if contexto_ocor:
        for o in contexto_ocor:
            passos_limpos = ""
            try:
                passos_json = json.loads(o.get('solucao', '[]'))
                for p in passos_json:
                    passos_limpos += f"{p.get('passo')} - {p.get('texto')}\n"
            except:
                passos_limpos = o.get('solucao', '')

            contexto_str += f"Problema: {o.get('problema')}\nSolução: {passos_limpos}\n\n"
    else:
        contexto_str += "Nenhum problema similar encontrado. Pedir para acionar o suporte.\n"

    try:
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
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
    if token_acesso != f"Bearer {MINHA_CHAVE_DE_API}":
        raise HTTPException(status_code=401, detail="Chave de API inválida. Acesso Negado.")

    contexto = buscar_contexto_relevante(requisicao.duvida)
    
    # ADICIONE ESTA LINHA PARA VER O RESULTADO NO TERMINAL:
    print(f"\n--- OS 3 PROBLEMAS ENCONTRADOS NO BANCO ---\n{contexto}\n------------------------------------------\n")
    
    resposta_formatada = gerar_resposta_cliente(requisicao.duvida, contexto)

    return {
        "status": "sucesso",
        "solucao_passo_a_passo": resposta_formatada
    }