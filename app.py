import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os

# ==========================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM (CSS CUSTOM)
# ==========================================
st.set_page_config(
    page_title="actuar.group - Engineering Hub",
    page_icon="🛠️",
    layout="wide"
)

# Custom CSS para UI/UX de nível SaaS
st.markdown("""
<style>
    /* Estilização Geral e Cores da Marcas */
    .stApp {
        background-color: #0e1117;
    }
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #30363d;
        background-color: #21262d;
        color: #c9d1d9;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        border-color: #58a6ff;
        color: #58a6ff;
    }
    
    /* Customization dos Expander Cards */
    .streamlit-expanderHeader {
        background-color: #161b22;
        border-radius: 8px;
        border: 1px solid #30363d;
    }
    
    /* Badges de Status e Complexidade */
    .badge-n1 { background-color: #238636; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
    .badge-n2 { background-color: #d29922; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
    .badge-n3 { background-color: #da3633; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8em; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CACHE E BANCO DE DADOS (DATABASE SERVICES)
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

@st.cache_data(ttl=30)
def buscar_ocorrencias_cached():
    res = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
    return pd.DataFrame(res.data)

def salvar_ocorrencia_db(dados):
    supabase.table("ocorrencias").insert(dados).execute()
    st.cache_data.clear()

def deletar_ocorrencia_db(ocorrencia_id):
    supabase.table("ocorrencias").delete().eq("id", ocorrencia_id).execute()
    st.cache_data.clear()

def upload_anexo(file):
    try:
        path = f"evidencias/{file.name}"
        file_bytes = file.getvalue()
        supabase.storage.from_("anexos_evidencias").upload(path, file_bytes, {"content-type": file.type})
        return supabase.storage.from_("anexos_evidencias").get_public_url(path)
    except Exception as e:
        st.error(f"Erro no upload da imagem: {e}")
        return None

def obter_perfil_usuario(user_id, email):
    res = supabase.table("perfis").select("role").eq("user_id", user_id).execute()
    if res.data:
        return res.data[0]["role"]
    # Perfil padrão inicial
    role_padrao = "Admin" if "admin" in email.lower() else "Analista"
    supabase.table("perfis").insert({"user_id": user_id, "email": email, "role": role_padrao}).execute()
    return role_padrao

# ==========================================
# 3. AUTENTICAÇÃO E SESSÃO
# ==========================================
if "user" not in st.session_state:
    st.session_state.user = None
if "user_role" not in st.session_state:
    st.session_state.user_role = "Tecnico"

def fazer_login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.session_state.user_role = obter_perfil_usuario(response.user.id, response.user.email)
        st.toast("Login realizado com sucesso!", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Falha na autenticação: {e}")

def fazer_logout():
    supabase.auth.sign_out()
    st.session_state.user = None
    st.session_state.user_role = "Tecnico"
    st.cache_data.clear()
    st.rerun()

# --- TELA DE LOGIN ---
if st.session_state.user is None:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if os.path.exists("logo_dark.png"):
            st.image("logo_dark.png", width=90)
        elif os.path.exists("logo.png"):
            st.image("logo.png", width=90)
            
        st.title("actuar.group")
        st.subheader("🔐 Acesso à Central Técnica")
        
        with st.form("login_form"):
            email_input = st.text_input("E-mail:")
            password_input = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar no Sistema"):
                if email_input and password_input:
                    fazer_login(email_input, password_input)
                else:
                    st.warning("Preencha e-mail e senha.")
    st.stop()

# ==========================================
# 4. LISTAS E HEADER DA APLICAÇÃO
# ==========================================
LISTA_SISTEMA = ["Legado(Acesso)", "The new(Edge)", "Não se aplica / Geral", "Outro Sistema"]
LISTA_HARDWARE = [
    "Catraca litnet1", "Catraca litnet2", "Catraca litnet3", "Catraca Edge",
    "Catraca Topdata", "Catraca Henry", "Catraca Tecnibra", "Catraca serial",
    "Catraca control ID block", "Catraca control ID block Next", "Control ID",
    "Control ID Max", "Webcam", "Facial EVO/Topdata", "Outro Hardware"
]

col_logo, col_space, col_user = st.columns([3, 4, 3])
with col_logo:
    if os.path.exists("logo_dark.png"):
        st.image("logo_dark.png", width=70)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=70)
    st.title("actuar.group")

with col_user:
    role_badge = f"🛡️ **{st.session_state.user_role}**"
    st.write(f"👤 {st.session_state.user.email} | {role_badge}")
    if st.button("🚪 Sair"):
        fazer_logout()

st.markdown("---")

# Carregar DataFrame Cached
try:
    df_ocorrencias = buscar_ocorrencias_cached()
except Exception as e:
    df_ocorrencias = pd.DataFrame()

# Garantir Colunas
for col in ["sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "tempo_estimado", "votos_pos", "votos_neg", "anexo_url"]:
    if not df_ocorrencias.empty and col not in df_ocorrencias.columns:
        df_ocorrencias[col] = None

# ==========================================
# 5. ESTRUTURA DE ABAS (SEM EXPORTAÇÃO)
# ==========================================
tab_consulta, tab_cadastro, tab_dash, tab_ai = st.tabs([
    "📋 Diagnósticos & Evidências", 
    "➕ Cadastrar Tratativa", 
    "📊 Dashboard Executivo", 
    "🤖 Assistente IA"
])

# ------------------------------------------
# ABA 1: DIAGNÓSTICOS, AVALIAÇÕES E DELETAR (RBAC)
# ------------------------------------------
with tab_consulta:
    st.subheader("🔍 Base Mapeada de Ocorrências")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    
    with col_f1:
        sist_opt = ["Todos"] + sorted(list(df_ocorrencias["sistema"].dropna().unique())) if not df_ocorrencias.empty else ["Todos"]
        f_sist = st.selectbox("Filtrar por Sistema:", sist_opt)
    with col_f2:
        hw_opt = ["Todos"] + sorted(list(df_ocorrencias["equipamento"].dropna().unique())) if not df_ocorrencias.empty else ["Todos"]
        f_hw = st.selectbox("Filtrar por Hardware:", hw_opt)
    with col_f3:
        f_busca = st.text_input("Buscar termo ou sintoma:", "")

    df_filtered = df_ocorrencias.copy()
    if not df_filtered.empty:
        if f_sist != "Todos":
            df_filtered = df_filtered[df_filtered["sistema"] == f_sist]
        if f_hw != "Todos":
            df_filtered = df_filtered[df_filtered["equipamento"] == f_hw]
        if f_busca:
            df_filtered = df_filtered[
                df_filtered["problema"].astype(str).str.contains(f_busca, case=False, na=False) |
                df_filtered["motivo"].astype(str).str.contains(f_busca, case=False, na=False) |
                df_filtered["solucao"].astype(str).str.contains(f_busca, case=False, na=False)
            ]

    if df_filtered.empty:
        st.info("Nenhuma ocorrência encontrada.")
    else:
        for _, row in df_filtered.iterrows():
            ocor_id = row['id']
            sist = row.get('sistema', 'N/A')
            hw = row.get('equipamento', 'N/A')
            prob = row.get('problema', 'Sem descrição')
            status = row.get('status', '🟢 Solução Definitiva')
            nivel = row.get('nivel', 'N1')
            anexo = row.get('anexo_url', None)
            
            with st.expander(f"[{status}] {sist} + {hw} — {prob}"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**⏱️ Nível:** `{nivel}`")
                
                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.success(f"**Solução Recomendada:**\n{row.get('solucao', '-')}")
                
                if anexo:
                    st.markdown(f"📷 **Evidência / Imagem Anexada:**")
                    st.image(anexo, width=350)

                # Controle RBAC: Somente Admin pode deletar registros
                if st.session_state.user_role == "Admin":
                    st.markdown("---")
                    if st.button(f"🗑️ Excluir Ocorrência #{ocor_id}", key=f"del_{ocor_id}"):
                        deletar_ocorrencia_db(ocor_id)
                        st.toast(f"Ocorrência #{ocor_id} removida!", icon="🗑️")
                        st.rerun()

# ------------------------------------------
# ABA 2: CADASTRO COM ANEXOS (IMAGENS/LOGS)
# ------------------------------------------
with tab_cadastro:
    st.subheader("➕ Novo Mapeamento Técnico")
    
    if st.session_state.user_role in ["Admin", "Analista"]:
        with st.form("form_novo_avancado", clear_on_submit=True):
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                in_sist = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
                in_status = st.selectbox("📌 Status:", ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"])
                in_nivel = st.selectbox("📊 Complexidade:", ["N1 - Fácil", "N2 - Intermediário", "N3 - Avançado"])
            with col_c2:
                in_hw = st.selectbox("⚙️ Hardware / Equipamento:", LISTA_HARDWARE)
                in_tempo = st.selectbox("⏱️ Tempo de Resolução:", ["15 minutos", "30 minutos", "1 hora", "2+ horas"])
                in_anexo = st.file_uploader("📷 Anexar Foto do Erro ou Log (Opcional):", type=["png", "jpg", "jpeg"])
                
            in_prob = st.text_input("Problema (Sintoma):")
            in_motivo = st.text_area("Motivo (Causa Raiz):")
            in_solucao = st.text_area("Solução Passo a Passo:")
            
            if st.form_submit_button("💾 Salvar Tratativa"):
                if in_prob and in_motivo and in_solucao:
                    anexo_url = upload_anexo(in_anexo) if in_anexo else None
                    dados = {
                        "sistema": in_sist,
                        "equipamento": in_hw,
                        "problema": in_prob,
                        "motivo": in_motivo,
                        "solucao": in_solucao,
                        "status": in_status,
                        "nivel": in_nivel,
                        "tempo_estimado": in_tempo,
                        "anexo_url": anexo_url
                    }
                    salvar_ocorrencia_db(dados)
                    st.toast("Nova ocorrência salva com sucesso!", icon="🎉")
                    st.rerun()
                else:
                    st.error("Preencha os campos obrigatórios.")
    else:
        st.warning("⚠️ Seu perfil (Técnico) tem acesso apenas para consulta. Solicite perfil de Analista ou Admin para cadastrar.")

# ------------------------------------------
# ABA 3: DASHBOARD EXEC
# ------------------------------------------
with tab_dash:
    st.subheader("📊 Indicadores de Atendimento")
    if df_ocorrencias.empty:
        st.info("Sem dados suficientes para gráficos.")
    else:
        k1, k2, k3 = st.columns(3)
        k1.metric("Total de Falhas Mapeadas", len(df_ocorrencias))
        k2.metric("Equipamento com Mais Falhas", df_ocorrencias["equipamento"].mode()[0] if not df_ocorrencias.empty else "N/A")
        k3.metric("Sistema Mais Demandado", df_ocorrencias["sistema"].mode()[0] if not df_ocorrencias.empty else "N/A")
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            fig_hw = px.bar(
                df_ocorrencias['equipamento'].value_counts().reset_index(),
                x='count', y='equipamento', orientation='h',
                title="<b>Volume de Erros por Hardware</b>",
                color_discrete_sequence=['#58a6ff']
            )
            st.plotly_chart(fig_hw, use_container_width=True)
            
        with g2:
            fig_sist = px.pie(
                df_ocorrencias, names='sistema', 
                title="<b>Distribuição por Software</b>", hole=0.4
            )
            st.plotly_chart(fig_sist, use_container_width=True)

# ------------------------------------------
# ABA 4: ASSISTENTE IA
# ------------------------------------------
with tab_ai:
    st.subheader("🤖 Assistente de Diagnóstico")
    pergunta = st.text_input("Qual o sintoma atual do cliente?", placeholder="Ex: Catraca não faz giro com leitor de facial")
    
    if pergunta and not df_ocorrencias.empty:
        palavras = pergunta.lower().split()
        matches = []
        for _, row in df_ocorrencias.iterrows():
            texto = f"{row['problema']} {row['motivo']} {row['equipamento']} {row['sistema']}".lower()
            score = sum(1 for p in palavras if p in texto)
            if score > 0:
                matches.append((score, row))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        if matches:
            top = matches[0][1]
            st.markdown("### 💡 Solução Encontrada:")
            st.info(f"**Causa Raiz:** {top['motivo']}")
            st.success(f"**Procedimento:** {top['solucao']}")
        else:
            st.warning("Nenhum diagnóstico direto encontrado.")