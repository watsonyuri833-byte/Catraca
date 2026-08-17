import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Configuração da página
st.set_page_config(
    page_title="actuar.group - Troubleshooting",
    page_icon="🛠️",
    layout="wide"
)

# Estilização CSS para visual Dark
st.markdown("""
<style>
    div.stButton > button {
        border-radius: 8px;
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
    }
    div.stButton > button:hover {
        background-color: #334155;
        border-color: #6366F1;
    }
</style>
""", unsafe_allow_html=True)

# Inicialização do Cliente Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Funções de Leitura e Escrita
def buscar_ocorrencias():
    resposta = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
    return pd.DataFrame(resposta.data)

def salvar_ocorrencia(equipamento, problema, motivo, solucao):
    dados = {
        "equipamento": equipamento,
        "problema": problema,
        "motivo": motivo,
        "solucao": solucao
    }
    supabase.table("ocorrencias").insert(dados).execute()

# Topo
col_logo, col_space, col_user = st.columns([3, 5, 2])
with col_logo:
    st.title("actuar.group")
with col_user:
    st.write("🌙 **Modo Escuro** | 👤 Analyst")

st.markdown("---")

st.subheader("🔍 Base de Erros e Soluções (Catracas & Periféricos)")
st.caption("Consulte ou cadastre diagnósticos técnicos e tratativas recomendadas.")

# --- SEÇÃO DE CADASTRO DE OCORRÊNCIAS ---
with st.expander("➕ Cadastrar Novo Problema / Solução", expanded=False):
    st.markdown("##### Preencha os campos abaixo para adicionar à base:")
    with st.form("form_novo_problema", clear_on_submit=True):
        f_col1, f_col2 = st.columns([1, 2])
        
        with f_col1:
            eq_input = st.selectbox("Equipamento:", ["Catraca", "Control iD", "Face Webcam", "Outro"])
        with f_col2:
            prob_input = st.text_input("Problema (Sintoma):", placeholder="Ex: Catraca reiniciando ao acionar solenoide")
            
        motivo_input = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Fonte de alimentação subdimensionada")
        solucao_input = st.text_area("Solução:", placeholder="Ex: Substituir fonte por uma de 12.8V / 3A")
        
        submit_btn = st.form_submit_button("💾 Salvar no Supabase")
        
        if submit_btn:
            if prob_input and motivo_input and solucao_input:
                try:
                    salvar_ocorrencia(eq_input, prob_input, motivo_input, solucao_input)
                    st.success("Ocorrência cadastrada com sucesso no banco de dados!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar no Supabase: {e}")
            else:
                st.error("Por favor, preencha todos os campos antes de salvar.")

st.markdown("---")

# --- CARREGAR DADOS DO SUPABASE ---
try:
    df_ocorrencias = buscar_ocorrencias()
except Exception as e:
    st.error(f"Erro ao conectar com o Supabase: {e}")
    df_ocorrencias = pd.DataFrame(columns=["equipamento", "problema", "motivo", "solucao"])

# --- FILTROS DE CONSULTA ---
col_f1, col_f2 = st.columns([1, 2])
with col_f1:
    opcoes_eq = ["Todos"] + list(df_ocorrencias["equipamento"].unique()) if not df_ocorrencias.empty else ["Todos"]
    filtro_eq = st.selectbox("Filtrar por Equipamento:", opcoes_eq)
with col_f2:
    busca_txt = st.text_input("Buscar problema ou palavra-chave:", "")

# Filtragem dos dados
df_exibicao = df_ocorrencias.copy()

if not df_exibicao.empty:
    if filtro_eq != "Todos":
        df_exibicao = df_exibicao[df_exibicao["equipamento"] == filtro_eq]

    if busca_txt:
        df_exibicao = df_exibicao[
            df_exibicao["problema"].str.contains(busca_txt, case=False, na=False) |
            df_exibicao["motivo"].str.contains(busca_txt, case=False, na=False) |
            df_exibicao["solucao"].str.contains(busca_txt, case=False, na=False)
        ]

# --- MAPEAMENTO DE OCORRÊNCIAS ---
st.markdown("### 📋 Mapeamento de Ocorrências")

if df_exibicao.empty:
    st.info("Nenhuma ocorrência registrada ainda. Utilize o formulário acima para cadastrar a primeira solução.")
else:
    for idx, row in df_exibicao.iterrows():
        with st.expander(f"🔴 [{row['equipamento']}] {row['problema']}"):
            st.markdown(f"**Motivo (Causa Raiz):** {row['motivo']}")
            st.success(f"**Solução:** {row['solucao']}")