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

# --- DASHBOARD ---

# Funções CRUD
def buscar_ocorrencias():
    resposta = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
    return pd.DataFrame(resposta.data)

def salvar_ocorrencia(sistema, equipamento, problema, motivo, solucao):
    # Salvamos tanto o sistema quanto o equipamento
    dados = {
        "sistema": sistema,
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
st.caption("Consulte ou cadastre tratativas associando Sistema e Hardware.")

# Listas de Opções
LISTA_SISTEMA = [
    "Legado(Acesso)",
    "The new(Edge)",
    "Não se aplica / Geral",
    "Outro Sistema"
]

LISTA_HARDWARE = [
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
    "Não se aplica / Software Puro",
    "Outro Hardware"
]

# Form de Cadastro Unificado (Sistema + Hardware)
with st.expander("➕ Cadastrar Novo Problema / Solução", expanded=False):
    with st.form("form_novo_problema", clear_on_submit=True):
        col_sist, col_hw = st.columns(2)
        
        with col_sist:
            sistema_input = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
        with col_hw:
            hw_input = st.selectbox("⚙️ Hardware / Equipamento:", LISTA_HARDWARE)
            
        prob_input = st.text_input("Problema (Sintoma):", placeholder="Ex: Catraca não valida giro após comando do sistema")
        motivo_input = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Incompatibilidade de DLL no sistema Legado com placa Litnet")
        solucao_input = st.text_area("Solução:", placeholder="Ex: Atualizar biblioteca de comunicação e reiniciar serviço")
        
        submit_btn = st.form_submit_button("💾 Salvar no Supabase")
        
        if submit_btn:
            if prob_input and motivo_input and solucao_input:
                try:
                    salvar_ocorrencia(sistema_input, hw_input, prob_input, motivo_input, solucao_input)
                    st.success("Ocorrência registrada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}. Verifique se a coluna 'sistema' existe na tabela 'ocorrencias'.")
            else:
                st.error("Preencha todos os campos obrigatórios antes de salvar.")

st.markdown("---")

# Carregar Dados
try:
    df_ocorrencias = buscar_ocorrencias()
except Exception as e:
    st.error(f"Erro ao conectar com o Supabase: {e}")
    df_ocorrencias = pd.DataFrame(columns=["sistema", "equipamento", "problema", "motivo", "solucao"])

# Certificar que a coluna sistema existe no dataframe carregado
if "sistema" not in df_ocorrencias.columns:
    df_ocorrencias["sistema"] = "N/A"

# Painel Principal com Filtros
st.markdown("### 📋 Consulta de Ocorrências Mapeadas")

col_f1, col_f2, col_f3 = st.columns([1, 1, 2])

with col_f1:
    sistemas_unicos = ["Todos"] + sorted(list(df_ocorrencias["sistema"].dropna().unique())) if not df_ocorrencias.empty else ["Todos"]
    filtro_sistema = st.selectbox("Filtrar por Sistema:", sistemas_unicos)

with col_f2:
    hws_unicos = ["Todos"] + sorted(list(df_ocorrencias["equipamento"].dropna().unique())) if not df_ocorrencias.empty else ["Todos"]
    filtro_hw = st.selectbox("Filtrar por Hardware:", hws_unicos)

with col_f3:
    busca_txt = st.text_input("Buscar por palavra-chave:", "")

# Filtragem de dados
df_exibicao = df_ocorrencias.copy()

if not df_exibicao.empty:
    if filtro_sistema != "Todos":
        df_exibicao = df_exibicao[df_exibicao["sistema"] == filtro_sistema]
        
    if filtro_hw != "Todos":
        df_exibicao = df_exibicao[df_exibicao["equipamento"] == filtro_hw]

    if busca_txt:
        df_exibicao = df_exibicao[
            df_exibicao["problema"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["motivo"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["solucao"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["sistema"].astype(str).str.contains(busca_txt, case=False, na=False) |
            df_exibicao["equipamento"].astype(str).str.contains(busca_txt, case=False, na-False)
        ]

# Exibição dos cards
if df_exibicao.empty:
    st.info("Nenhuma ocorrência encontrada com os filtros selecionados.")
else:
    for idx, row in df_exibicao.iterrows():
        sist = row.get('sistema', 'Geral')
        hw = row.get('equipamento', 'Geral')
        prob = row.get('problema', 'Sem descrição')
        
        with st.expander(f"🔴 [{sist} + {hw}] {prob}"):
            st.markdown(f"**💻 Sistema:** {sist} | **⚙️ Hardware:** {hw}")
            st.markdown(f"**Motivo (Causa Raiz):** {row.get('motivo', '-')}")
            st.success(f"**Solução:** {row.get('solucao', '-')}")