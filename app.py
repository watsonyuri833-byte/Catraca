import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Configuração inicial da página
st.set_page_config(
    page_title="actuar.group - Troubleshooting",
    page_icon="🛠️",
    layout="wide"
)

# Conexão com Supabase sem cache para garantir leitura dos Secrets
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# Funções CRUD
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

# Cabeçalho da Interface
col_logo, col_space, col_user = st.columns([3, 5, 2])
with col_logo:
    st.title("actuar.group")
with col_user:
    st.write("🌙 **Modo Escuro** | 👤 Analyst")

st.markdown("---")

st.subheader("🔍 Base de Erros e Soluções (Catracas, Periféricos & Sistemas)")
st.caption("Consulte ou cadastre diagnósticos técnicos e tratativas recomendadas.")

# Lista de Equipamentos e Sistemas fornecida
LISTA_EQUIPAMENTOS = [
    # Catracas e Hardware
    "Catraca litnet1",
    "Catraca litnet2",
    "Catraca litnet3",
    "Catraca Edge",
    "Catraca Topdata",
    "Catraca Henry",
    "Catraca Tecnibra",
    "Catraca serial",
    "Catraca control ID block",
    "Catraca control ID block Next",
    "Control ID",
    "Control ID Max",
    "Webcam",
    "Facial EVO/Topdata",
    # Sistemas / Acesso
    "Legado(Acesso)",
    "The new(Edge)",
    "Outro"
]

# Form de Cadastro
with st.expander("➕ Cadastrar Novo Problema / Solução", expanded=False):
    with st.form("form_novo_problema", clear_on_submit=True):
        f_col1, f_col2 = st.columns([1, 2])
        
        with f_col1:
            eq_input = st.selectbox("Equipamento / Sistema:", LISTA_EQUIPAMENTOS)
        with f_col2:
            prob_input = st.text_input("Problema (Sintoma):", placeholder="Ex: Erro de comunicação com o banco de dados do Acesso")
            
        motivo_input = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Porta de conexão bloqueada ou serviço do sistema parado")
        solucao_input = st.text_area("Solução:", placeholder="Ex: Reiniciar o serviço de comunicação e liberar a porta no firewall")
        
        submit_btn = st.form_submit_button("💾 Salvar no Supabase")
        
        if submit_btn:
            if prob_input and motivo_input and solucao_input:
                try:
                    salvar_ocorrencia(eq_input, prob_input, motivo_input, solucao_input)
                    st.success("Ocorrência registrada no Supabase com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.error("Preencha todos os campos antes de salvar.")

st.markdown("---")

# Carregar Dados
try:
    df_ocorrencias = buscar_ocorrencias()
except Exception as e:
    st.error(f"Erro ao conectar com o Supabase: {e}")
    df_ocorrencias = pd.DataFrame(columns=["equipamento", "problema", "motivo", "solucao"])

# Filtros
col_f1, col_f2 = st.columns([1, 2])
with col_f1:
    if not df_ocorrencias.empty and "equipamento" in df_ocorrencias.columns:
        opcoes_eq = ["Todos"] + sorted(list(df_ocorrencias["equipamento"].unique()))
    else:
        opcoes_eq = ["Todos"]
    filtro_eq = st.selectbox("Filtrar por Equipamento / Sistema:", opcoes_eq)

with col_f2:
    busca_txt = st.text_input("Buscar problema ou palavra-chave:", "")

# Filtragem de busca
df_exibicao = df_ocorrencias.copy()

if not df_exibicao.empty and "equipamento" in df_exibicao.columns:
    if filtro_eq != "Todos":
        df_exibicao = df_exibicao[df_exibicao["equipamento"] == filtro_eq]

    if busca_txt:
        df_exibicao = df_exibicao[
            df_exibicao["problema"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["motivo"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["solucao"].astype(str).str.contains(busca_txt, case=False, na=False)
        ]

# Exibição dos itens em accordion/expander
st.markdown("### 📋 Mapeamento de Ocorrências")

if df_exibicao.empty:
    st.info("Nenhuma ocorrência registrada ainda. Utilize o formulário acima para cadastrar a primeira solução.")
else:
    for idx, row in df_exibicao.iterrows():
        with st.expander(f"🔴 [{row.get('equipamento', 'N/A')}] {row.get('problema', 'Sem descrição')}"):
            st.markdown(f"**Motivo (Causa Raiz):** {row.get('motivo', '-')}")
            st.success(f"**Solução:** {row.get('solucao', '-')}")