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
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = os.getenv("API_KEY")

if not all([SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY, API_KEY]):
    raise ValueError("Faltam variáveis de ambiente! Verifique se o seu arquivo .env está configurado corretamente.")

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
        res = supabase.table("ocorrencias").select("problema, motivo, solucao").limit(200).execute()
        return res.data if res.data else []
        
    except Exception as e:
        print(f"Erro ao buscar no banco de dados: {e}")
        return []

# ==========================================
# 4. MOTOR DA IA (Lógica Condicional e Didática)
# ==========================================
def gerar_resposta_cliente(duvida: str, contexto_ocor: list):
    prompt_sistema = """Você é o Assistente Virtual Técnico para o cliente final (donos de academias, escolas e gestores).
Sua missão é ajudar o cliente a resolver problemas de forma muito atenciosa, didática e passo a passo condicional.

DIRETRIZ DE CONDICIONALIDADE E LINGUAGEM PARA LEIGOS:
1. Seja educado e amigável. Inicie com uma saudação acolhedora.
2. NUNCA jogue um bloco seco de texto ou liste todos os passos como se fossem tarefas simultâneas. O cliente precisa testar uma coisa de cada vez.
3. Use sempre uma estrutura condicional clara: apresente o primeiro teste e diga explicitamente: "Faça isso e teste. Se não funcionar (ou se continuar com o problema), siga para o próximo passo:".
4. Explique os procedimentos de forma simples, imaginando que o cliente tem muita dificuldade com tecnologia.

DIRETRIZ DE CORTE PARA PROBLEMAS MECÂNICOS / FÍSICOS / ELÉTRICOS:
5. Se o problema envolver questões mecânicas ou elétricas graves (ex: catraca apitando, mole, dura, desligando e ligando sozinha, travamento físico no giro), informe com empatia que é uma ocorrência mecânica/elétrica que necessita de avaliação detalhada e oriente a contatar o suporte.

DIRETRIZES DE RESPOSTA (SISTEMAS E PERIFÉRICOS):
6. Para problemas de aplicativo, rede, webcam, biometria ou firewall, utilize a Base de Conhecimento e construa um roteiro de testes sequencial e condicional.
7. NUNCA utilize jargões técnicos complexos.
8. Se o problema DEFINITIVAMENTE não estiver na base, informe amigavelmente para abrir um chamado no suporte técnico.
9. REGRA OBRIGATÓRIA DE ENCERRAMENTO: No final absoluto de QUALQUER resposta gerada, inclua obrigatoriamente a frase exata: "Caso isso não resolva, contate o suporte técnico."
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
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=contexto_str,
            config=types.GenerateContentConfig(
                system_instruction=prompt_sistema,
                temperature=0.2,
            )
        )
        return response.text
    except Exception as e:
        print(f"\n[ERRO GEMINI]: {str(e)}\n")
        return "Olá! Tivemos uma oscilação temporária. Por favor, tente novamente. Caso isso não resolva, contate o suporte técnico."

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

    contexto = buscar_contexto_relevante()
    resposta_formatada = gerar_resposta_cliente(requisicao.duvida, contexto)

    return {
        "status": "sucesso",
        "solucao_passo_a_passo": resposta_formatada
    }