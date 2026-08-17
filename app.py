import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Configuração inicial da página
st.set_page_config(
    page_title="actuar.group - Troubleshooting",
    page_icon="🛠️",
    layout="wide"
)

# Conexão com Supabase
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- GERENCIAMENTO DE SESSÃO / LOGIN ---
if "user" not in st.session_state:
    st.session_state.user = None

def fazer_login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.success("Login realizado com sucesso!")
        st.rerun()
    except Exception as e:
        st.error(f"Falha no login: {e}")

def fazer_logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.rerun()

# --- TELA DE LOGIN ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("actuar.group")
        st.subheader("🔐 Acesso ao Sistema")
        
        with st.form("login_form"):
            email_input = st.text_input("E-mail:")
            password_input = st.text_input("Senha:", type="password")
            submit_login = st.form_submit_button("Entrar")
            
            if submit_login:
                if email_input and password_input:
                    fazer_login(email_input, password_input)
                else:
                    st.warning("Por favor, preencha o e-mail e a senha.")
    st.stop()

# --- DASHBOARD DE SUCESSO APÓS LOGIN ---

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
col_logo, col_space, col_user = st.columns([3, 4, 3])
with col_logo:
    st.title("actuar.group")
with col_user:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("🚪 Sair (Logout)"):
        fazer_logout()

st.markdown("---")

st.subheader("🔍 Base de Diagnósticos Técnicos e Soluções")
st.caption("Consulte ou cadastre tratativas de hardware e sistemas de acesso.")

# Listas independentes
LISTA_CATRACAS = [
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
    "Outro Hardware"
]

LISTA_SISTEMAS = [
    "Legado(Acesso)",
    "The new(Edge)",
    "Outro Sistema"
]

LISTA_GERAL = LISTA_CATRACAS + LISTA_SISTEMAS

# Form de Cadastro
with st.expander("➕ Cadastrar Novo Problema / Solução", expanded=False):
    with st.form("form_novo_problema", clear_on_submit=True):
        f_col1, f_col2 = st.columns([1, 2])
        
        with f_col1:
            eq_input = st.selectbox("Categoria (Hardware ou Sistema):", LISTA_GERAL)
        with f_col2:
            prob_input = st.text_input("Problema (Sintoma):", placeholder="Ex: Erro de conexão de banco no módulo Acesso")
            
        motivo_input = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Serviço parado ou falha de rede")
        solucao_input = st.text_area("Solução:", placeholder="Ex: Reiniciar o serviço e validar a porta 5432")
        
        submit_btn = st.form_submit_button("💾 Salvar no Supabase")
        
        if submit_btn:
            if prob_input and motivo_input and solucao_input:
                try:
                    salvar_ocorrencia(eq_input, prob_input, motivo_input, solucao_input)
                    st.success("Ocorrência registrada com sucesso!")
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

# Divisão por Abas (Hardware vs Sistema)
tab_catracas, tab_sistemas = st.tabs(["⚙️ Catracas & Periféricos", "💻 Sistemas & Acesso"])

def renderizar_painel(df_dados, itens_permitidos):
    if df_dados.empty or "equipamento" not in df_dados.columns:
        st.info("Nenhuma ocorrência registrada.")
        return

    # Filtrar os dados referentes apenas aos itens daquela aba
    df_filtrado_aba = df_dados[df_dados["equipamento"].isin(itens_permitidos)]

    col_f1, col_f2 = st.columns([1, 2])
    with col_f1:
        opcoes = ["Todos"] + sorted(list(df_filtrado_aba["equipamento"].unique()))
        filtro_item = st.selectbox("Filtrar por tipo:", opcoes, key=f"filter_{itens_permitidos[0]}")
    with col_f2:
        busca_txt = st.text_input("Buscar palavra-chave:", "", key=f"search_{itens_permitidos[0]}")

    df_exibicao = df_filtrado_aba.copy()

    if filtro_item != "Todos":
        df_exibicao = df_exibicao[df_exibicao["equipamento"] == filtro_item]

    if busca_txt:
        df_exibicao = df_exibicao[
            df_exibicao["problema"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["motivo"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["solucao"].astype(str).str.contains(busca_txt, case=False, na=False)
        ]

    st.markdown("### 📋 Ocorrências Encontradas")

    if df_exibicao.empty:
        st.info("Nenhum registro localizado para este filtro.")
    else:
        for idx, row in df_exibicao.iterrows():
            with st.expander(f"🔴 [{row.get('equipamento', 'N/A')}] {row.get('problema', 'Sem descrição')}"):
                st.markdown(f"**Motivo (Causa Raiz):** {row.get('motivo', '-')}")
                st.success(f"**Solução:** {row.get('solucao', '-')}")

with tab_catracas:
    renderizar_painel(df_ocorrencias, LISTA_CATRACAS)

with tab_sistemas:
    renderizar_painel(df_ocorrencias, LISTA_SISTEMAS)