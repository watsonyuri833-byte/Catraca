import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os
import io

# 1. Configuração da Página
st.set_page_config(
    page_title="actuar.group - Troubleshooting & Analytics",
    page_icon="🛠️",
    layout="wide"
)

# 2. Conexão Supabase
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# 3. Controle de Sessão / Login
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
        if os.path.exists("logo_dark.png"):
            st.image("logo_dark.png", width=90)
        elif os.path.exists("logo.png"):
            st.image("logo.png", width=90)
            
        st.title("actuar.group")
        st.subheader("🔐 Acesso à Central Técnica")
        
        with st.form("login_form"):
            email_input = st.text_input("E-mail:")
            password_input = st.text_input("Senha:", type="password")
            submit_login = st.form_submit_button("Entrar")
            
            if submit_login:
                if email_input and password_input:
                    fazer_login(email_input, password_input)
                else:
                    st.warning("Preencha o e-mail e a senha.")
    st.stop()

# 4. Funções do Banco de Dados (CRUD + Interações)
def buscar_ocorrencias():
    res = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
    return pd.DataFrame(res.data)

def salvar_ocorrencia(sistema, equipamento, problema, motivo, solucao, status, nivel, tempo):
    dados = {
        "sistema": sistema,
        "equipamento": equipamento,
        "problema": problema,
        "motivo": motivo,
        "solucao": solucao,
        "status": status,
        "nivel": nivel,
        "tempo_estimado": tempo,
        "votos_pos": 0,
        "votos_neg": 0
    }
    supabase.table("ocorrencias").insert(dados).execute()

def computar_voto(ocorrencia_id, tipo_voto, valor_atual):
    coluna = "votos_pos" if tipo_voto == "pos" else "votos_neg"
    novo_valor = int(valor_atual) + 1
    supabase.table("ocorrencias").update({coluna: novo_valor}).eq("id", ocorrencia_id).execute()

def buscar_comentarios(ocorrencia_id):
    res = supabase.table("comentarios").select("*").eq("ocorrencia_id", ocorrencia_id).order("id", desc=True).execute()
    return res.data

def salvar_comentario(ocorrencia_id, usuario, texto):
    supabase.table("comentarios").insert({
        "ocorrencia_id": ocorrencia_id,
        "usuario": usuario,
        "comentario": texto
    }).execute()

# 5. Listas de Referência
LISTA_SISTEMA = ["Legado(Acesso)", "The new(Edge)", "Não se aplica / Geral", "Outro Sistema"]
LISTA_HARDWARE = [
    "Catraca litnet1", "Catraca litnet2", "Catraca litnet3", "Catraca Edge",
    "Catraca Topdata", "Catraca Henry", "Catraca Tecnibra", "Catraca serial",
    "Catraca control ID block", "Catraca control ID block Next", "Control ID",
    "Control ID Max", "Webcam", "Facial EVO/Topdata", "Outro Hardware"
]

# --- CABEÇALHO ---
col_logo, col_space, col_user = st.columns([3, 4, 3])
with col_logo:
    if os.path.exists("logo_dark.png"):
        st.image("logo_dark.png", width=70)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=70)
    st.title("actuar.group")

with col_user:
    st.write(f"👤 **{st.session_state.user.email}**")
    if st.button("🚪 Sair"):
        fazer_logout()

st.markdown("---")

# Carregamento do DataFrame
try:
    df_ocorrencias = buscar_ocorrencias()
except Exception as e:
    df_ocorrencias = pd.DataFrame()

# Garantir existência das colunas no DataFrame
for col in ["sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "tempo_estimado", "votos_pos", "votos_neg"]:
    if not df_ocorrencias.empty and col not in df_ocorrencias.columns:
        df_ocorrencias[col] = "N/A"

# --- NAVEGAÇÃO POR ABAS ---
tab_consulta, tab_cadastro, tab_dash, tab_ai, tab_relatorios = st.tabs([
    "📋 Diagnósticos", 
    "➕ Cadastrar Novo", 
    "📊 Dashboard Executivo", 
    "🤖 Assistente IA", 
    "📤 Exportar Relatórios"
])

# ==========================================
# ABA 1: CONSULTA DE DIAGNÓSTICOS + AVALIAÇÃO + COMENTÁRIOS
# ==========================================
with tab_consulta:
    st.subheader("🔍 Base Mapeada de Ocorrências")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    
    with col_f1:
        sist_opt = ["Todos"] + sorted(list(df_ocorrencias["sistema"].unique())) if not df_ocorrencias.empty else ["Todos"]
        f_sist = st.selectbox("Filtrar por Sistema:", sist_opt)
    with col_f2:
        hw_opt = ["Todos"] + sorted(list(df_ocorrencias["equipamento"].unique())) if not df_ocorrencias.empty else ["Todos"]
        f_hw = st.selectbox("Filtrar por Hardware:", hw_opt)
    with col_f3:
        f_busca = st.text_input("Buscar termo ou palavra-chave:", "")

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
        st.info("Nenhuma ocorrência encontrada com os filtros selecionados.")
    else:
        for _, row in df_filtered.iterrows():
            ocor_id = row['id']
            sist = row.get('sistema', 'N/A')
            hw = row.get('equipamento', 'N/A')
            prob = row.get('problema', 'Sem descrição')
            status = row.get('status', '🟢 Solução Definitiva')
            nivel = row.get('nivel', 'N1')
            tempo = row.get('tempo_estimado', '-')
            
            with st.expander(f"[{status}] {sist} + {hw} — {prob}"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**⏱️ Complexidade/Tempo:** {nivel} ({tempo})")
                
                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.success(f"**Solução Recomendada:**\n{row.get('solucao', '-')}")
                
                # Sistema de Avaliação (Votos)
                st.markdown("---")
                v_pos = row.get('votos_pos', 0)
                v_neg = row.get('votos_neg', 0)
                col_v1, col_v2, col_space = st.columns([1, 1, 4])
                
                with col_v1:
                    if st.button(f"👍 Funcionou ({v_pos})", key=f"pos_{ocor_id}"):
                        computar_voto(ocor_id, "pos", v_pos)
                        st.rerun()
                with col_v2:
                    if st.button(f"👎 Não funcionou ({v_neg})", key=f"neg_{ocor_id}"):
                        computar_voto(ocor_id, "neg", v_neg)
                        st.rerun()
                
                # Seção de Comentários / Observações de Campo
                st.markdown("**💬 Anotações / Observações de Campo:**")
                comentarios = buscar_comentarios(ocor_id)
                for c in comentarios:
                    st.caption(f"**{c['usuario']}** em {c['created_at'][:10]}: {c['comentario']}")
                
                with st.form(key=f"form_coment_{ocor_id}"):
                    novo_coment = st.text_input("Adicionar observação rápida:", placeholder="Ex: No Windows 11 necessita rodar como Admin.")
                    if st.form_submit_button("Enviar Comentário"):
                        if novo_coment:
                            salvar_comentario(ocor_id, st.session_state.user.email, novo_coment)
                            st.success("Anotação salva!")
                            st.rerun()

# ==========================================
# ABA 2: CADASTRO COMPLETO
# ==========================================
with tab_cadastro:
    st.subheader("➕ Novo Mapeamento Técnico")
    with st.form("form_novo", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            in_sist = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
            in_status = st.selectbox("📌 Status da Tratativa:", ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"])
            in_nivel = st.selectbox("📊 Nível de Complexidade:", ["N1 - Fácil / Rápido", "N2 - Intermediário", "N3 - Avançado / Laboratório"])
        with col_c2:
            in_hw = st.selectbox("⚙️ Hardware / Equipamento:", LISTA_HARDWARE)
            in_tempo = st.selectbox("⏱️ Tempo Médio de Resolução:", ["15 minutos", "30 minutos", "1 hora", "2+ horas", "Requer troca/envio"])
            
        in_prob = st.text_input("Problema (Sintoma):", placeholder="Ex: Catraca trava comuniação ao autenticar facial")
        in_motivo = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Conflito de IPs na rede do cliente ou porta bloqueada pelo firewall")
        in_solucao = st.text_area("Solução Passo a Passo:", placeholder="Ex: Fixar IP na catraca e liberar a porta 8080 no Windows Defender")
        
        if st.form_submit_button("💾 Salvar Tratativa no Supabase"):
            if in_prob and in_motivo and in_solucao:
                try:
                    salvar_ocorrencia(in_sist, in_hw, in_prob, in_motivo, in_solucao, in_status, in_nivel, in_tempo)
                    st.success("Ocorrência registrada com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar: {e}")
            else:
                st.error("Preencha todos os campos antes de cadastrar.")

# ==========================================
# ABA 3: DASHBOARD EXECUTIVO (MÉTRICAS E GRÁFICOS)
# ==========================================
with tab_dash:
    st.subheader("📊 Indicadores e Métricas de Chamados")
    if df_ocorrencias.empty:
        st.info("Cadastre dados para visualizar o dashboard executivo.")
    else:
        # Métricas em Cartões (KPIs)
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Mapeado", len(df_ocorrencias))
        
        top_hw = df_ocorrencias["equipamento"].mode()[0] if not df_ocorrencias.empty else "N/A"
        kpi2.metric("Hardware + Instável", top_hw)
        
        top_sist = df_ocorrencias["sistema"].mode()[0] if not df_ocorrencias.empty else "N/A"
        kpi3.metric("Sistema + Citado", top_sist)
        
        n1_count = len(df_ocorrencias[df_ocorrencias["nivel"].str.contains("N1", na=False)])
        kpi4.metric("Resolvidos em N1", f"{(n1_count/len(df_ocorrencias))*100:.0f}%" if len(df_ocorrencias) > 0 else "0%")
        
        st.markdown("---")
        
        # Gráficos com Plotly
        g_col1, g_col2 = st.columns(2)
        with g_col1:
            fig_hw = px.bar(
                df_ocorrencias['equipamento'].value_counts().reset_index(),
                x='count', y='equipamento', orientation='h',
                title="<b>Top Equipamentos por Ocorrência</b>",
                labels={'count': 'Qtd Falhas', 'equipamento': 'Hardware'},
                color_discrete_sequence=['#ff4b4b']
            )
            st.plotly_chart(fig_hw, use_container_width=True)
            
        with g_col2:
            fig_sist = px.pie(
                df_ocorrencias, names='sistema', 
                title="<b>Distribuição por Sistema (Software)</b>",
                hole=0.4
            )
            st.plotly_chart(fig_sist, use_container_width=True)

# ==========================================
# ABA 4: ASSISTENTE INTELIGENTE (IA LOCAL)
# ==========================================
with tab_ai:
    st.subheader("🤖 Assistente de Diagnóstico Rápido")
    st.caption("Digite o problema enfrentado para obter o diagnóstico imediato com base na nossa base.")
    
    pergunta_tecnico = st.text_input("Qual é o sintoma ou erro atual?", placeholder="Ex: Catraca não abre e sistema legado perdeu conexão")
    
    if pergunta_tecnico and not df_ocorrencias.empty:
        # Busca simples por termos relevantes
        palavras = pergunta_tecnico.lower().split()
        matches = []
        for _, row in df_ocorrencias.iterrows():
            texto_comp = f"{row['problema']} {row['motivo']} {row['equipamento']} {row['sistema']}".lower()
            score = sum(1 for p in palavras if p in texto_comp)
            if score > 0:
                matches.append((score, row))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        if matches:
            top_match = matches[0][1]
            st.markdown("### 💡 Diagnóstico Sugerido:")
            st.info(f"**Causa provável identificada:** {top_match['motivo']}")
            st.success(f"**Passo a passo recomendado:** {top_match['solucao']}")
        else:
            st.warning("Nenhum diagnóstico exato encontrado. Tente cadastrar este novo cenário na aba 'Cadastrar Novo'.")

# ==========================================
# ABA 5: EXPORTAÇÃO DE RELATÓRIOS
# ==========================================
with tab_relatorios:
    st.subheader("📤 Gerador de Relatórios em Excel")
    st.write("Exporte a base filtrada de tratativas técnicas para enviar a clientes ou gestores.")
    
    if not df_ocorrencias.empty:
        # Gerar arquivo Excel em memória
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df_ocorrencias.to_excel(writer, index=False, sheet_name='Ocorrencias')
        
        st.download_button(
            label="📥 Baixar Base de Ocorrências (.xlsx)",
            data=buffer.getvalue(),
            file_name="relatorio_troubleshooting_actuar.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Nenhum dado disponível para exportação.")