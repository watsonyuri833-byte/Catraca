import streamlit as st
import pandas as pd
from datetime import datetime
from supabase import create_client, Client
from google import genai

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Sistema de Diagnósticos e Copilot IA",
    page_icon="🤖",
    layout="wide"
)

# --- CONFIGURAÇÃO DO SUPABASE ---
# Tenta carregar dos secrets do Streamlit ou usa variáveis de exemplo
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = "SUA_SUPABASE_URL_AQUI"
    SUPABASE_KEY = "SUA_SUPABASE_KEY_AQUI"

@st.cache_resource
def init_supabase():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        return None

supabase = init_supabase()

# --- BARRA LATERAL (CONFIGURAÇÕES & NAVEGAÇÃO) ---
st.sidebar.title("⚙️ Painel de Controle")

# 1. Configuração da Chave de API do Gemini
st.sidebar.subheader("🔑 Configuração da IA")
gemini_api_key = st.sidebar.text_input(
    "Chave de API do Gemini", 
    type="password", 
    value="",
    help="Insira sua chave da API do Google Gemini para ativar o Copilot IA."
)

st.sidebar.markdown("---")
st.sidebar.subheader("📌 Navegação")
menu = st.sidebar.radio(
    "Ir para:",
    ["📊 Dashboard", "📝 Cadastrar Ocorrência", "🔍 Consultar / Editar", "🤖 Copilot IA"]
)

# --- FUNÇÕES DE BANCO DE DADOS ---
def listar_ocorrencias():
    if not supabase:
        # Fallback caso o Supabase não esteja conectado para teste visual
        return pd.DataFrame(columns=["id", "titulo", "descricao", "categoria", "solucao", "status", "created_at"])
    try:
        response = supabase.table("ocorrencias").select("*").execute()
        data = response.data
        if data:
            return pd.DataFrame(data)
        return pd.DataFrame(columns=["id", "titulo", "descricao", "categoria", "solucao", "status", "created_at"])
    except Exception as e:
        st.error(f"Erro ao carregar dados do Supabase: {e}")
        return pd.DataFrame(columns=["id", "titulo", "descricao", "categoria", "solucao", "status", "created_at"])

def salvar_ocorrencia(dados):
    if not supabase:
        st.warning("Supabase não configurado. Dados não salvos no banco.")
        return False
    try:
        supabase.table("ocorrencias").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False

def atualizar_ocorrencia(id_ocorrencia, dados):
    if not supabase:
        return False
    try:
        supabase.table("ocorrencias").update(dados).eq("id", id_ocorrencia).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar registro: {e}")
        return False

def deletar_ocorrencia(id_ocorrencia):
    if not supabase:
        return False
    try:
        supabase.table("ocorrencias").delete().eq("id", id_ocorrencia).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao excluir registro: {e}")
        return False

# --- TELA 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.title("📊 Dashboard de Ocorrências e Diagnósticos")
    st.markdown("Visão geral dos registros armazenados no banco de dados.")
    
    df = listar_ocorrencias()
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        col1.metric("Total de Ocorrências", len(df))
        if "status" in df.columns:
            resolvidas = len(df[df["status"].str.lower() == "resolvido"])
            col2.metric("Ocorrências Resolvidas", resolvidas)
            col3.metric("Pendentes", len(df) - resolvidas)
        
        st.markdown("---")
        st.subheader("📋 Últimos Registros")
        st.dataframe(df, use_container_width=True)
    else:
        st.info("Nenhuma ocorrência cadastrada no banco de dados no momento.")

# --- TELA 2: CADASTRAR OCORRÊNCIA ---
elif menu == "📝 Cadastrar Ocorrência":
    st.title("📝 Cadastro de Nova Ocorrência / Diagnóstico")
    
    with st.form("form_cadastro"):
        titulo = st.text_input("Título do Problema / Diagnóstico")
        categoria = st.selectbox("Categoria", ["Técnico", "Infraestrutura", "Software", "Manutenção", "Outros"])
        descricao = st.text_area("Descrição Detalhada do Problema")
        solucao = st.text_area("Solução Aplicada / Recomendada")
        status = st.selectbox("Status", ["Pendente", "Em Análise", "Resolvido"])
        
        submitted = st.form_submit_button("Salvar Ocorrência")
        if submitted:
            if titulo and descricao:
                novo_registro = {
                    "titulo": titulo,
                    "categoria": categoria,
                    "descricao": descricao,
                    "solucao": solucao,
                    "status": status,
                    "created_at": datetime.now().isoformat()
                }
                if salvar_ocorrencia(novo_registro):
                    st.success("Ocorrência cadastrada com sucesso!")
            else:
                st.warning("Por favor, preencha pelo menos o Título e a Descrição.")

# --- TELA 3: CONSULTAR / EDITAR ---
elif menu == "🔍 Consultar / Editar":
    st.title("🔍 Consulta e Edição de Ocorrências")
    
    df = listar_ocorrencias()
    
    if not df.empty:
        pesquisa = st.text_input("Pesquisar por termo (título ou descrição):")
        if pesquisa:
            df = df[df['titulo'].str.contains(pesquisa, case=False, na=False) | df['descricao'].str.contains(pesquisa, case=False, na=False)]
        
        st.dataframe(df, use_container_width=True)
        
        st.markdown("---")
        st.subheader("✏️ Editar ou Excluir Registro")
        
        if "id" in df.columns:
            ids_disponiveis = df["id"].tolist()
            id_selecionado = st.selectbox("Selecione o ID da ocorrência para gerenciar:", ids_disponiveis)
            
            if id_selecionado:
                registro_atual = df[df["id"] == id_selecionado].iloc[0]
                
                with st.form("form_edicao"):
                    novo_titulo = st.text_input("Título", value=str(registro_atual.get("titulo", "")))
                    nova_desc = st.text_area("Descrição", value=str(registro_atual.get("descricao", "")))
                    nova_solucao = st.text_area("Solução", value=str(registro_atual.get("solucao", "")))
                    novo_status = st.selectbox("Status", ["Pendente", "Em Análise", "Resolvido"], index=0)
                    
                    col_b1, col_b2 = st.columns(2)
                    atualizar_btn = col_b1.form_submit_button("Atualizar Ocorrência")
                    excluir_btn = col_b2.form_submit_button("Excluir Ocorrência")
                    
                    if atualizar_btn:
                        dados_atualizados = {
                            "titulo": novo_titulo,
                            "descricao": nova_desc,
                            "solucao": nova_solucao,
                            "status": novo_status
                        }
                        if atualizar_ocorrencia(id_selecionado, dados_atualizados):
                            st.success("Ocorrência atualizada com sucesso! Recarregue a página para ver as alterações.")
                    
                    if excluir_btn:
                        if deletar_ocorrencia(id_selecionado):
                            st.success("Ocorrência excluída com sucesso! Recarregue a página.")
    else:
        st.info("Nenhum dado disponível para consulta.")

# --- TELA 4: COPILOT IA ---
elif menu == "🤖 Copilot IA":
    st.title("🤖 Copilot de Inteligência Artificial")
    st.markdown("Faça perguntas sobre problemas técnicos. O Copilot cruzará sua consulta com o banco de dados de ocorrências e usará a IA do Gemini para gerar a melhor diretriz de ação.")
    
    if not gemini_api_key:
        st.warning("⚠️ Insira sua **Chave de API do Gemini** na barra lateral à esquerda para habilitar o assistente.")
    else:
        pergunta_usuario = st.text_area("Descreva o problema ou faça sua consulta técnica:", placeholder="Ex: O equipamento X apresentou falha na porta Y, qual procedimento devo seguir?")
        
        if st.button("🧠 Consultar Copilot IA", type="primary"):
            if not pergunta_usuario.strip():
                st.warning("Por favor, digite uma pergunta ou descrição do problema.")
            else:
                with st.spinner("Analisando banco de dados e gerando resposta com Gemini..."):
                    try:
                        # Carrega todo o contexto do banco de dados
                        df_db = listar_ocorrencias()
                        contexto_banco = df_db.to_string(index=False) if not df_db.empty else "Nenhuma ocorrência registrada."
                        
                        # Inicializa cliente Gemini com a chave fornecida
                        client = genai.Client(api_key=gemini_api_key)
                        
                        prompt_sistema = f"""
Você é um Copilot especialista em diagnósticos técnicos, suporte e resolução de problemas corporativos.
Abaixo está o histórico completo do banco de dados de ocorrências da empresa:

=== HISTÓRICO DO BANCO DE DADOS ===
{contexto_banco}
=== FIM DO HISTÓRICO ===

Consulta atual do operador:
"{pergunta_usuario}"

Instruções para a resposta:
1. Analise se há padrões ou ocorrências similares no histórico do banco de dados fornecido.
2. Combine o histórico com sua inteligência técnica avançada para formular um plano de ação claro, estruturado, passo a passo e profissional.
3. Utilize formatação em Markdown (negritos, listas e tópicos) para facilitar a leitura rápida.
"""
                        # Chamada ao modelo Gemini (utilizando gemini-2.5-flash)
                        response = client.models.generate_content(
                            model='gemini-2.5-flash',
                            contents=prompt_sistema
                        )
                        
                        st.markdown("### 💡 Resposta do Copilot IA:")
                        st.markdown(response.text)
                        
                    except Exception as e:
                        st.error(f"❌ Ocorreu um erro ao comunicar com a API do Gemini: {e}")