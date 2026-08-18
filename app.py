import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
import os
import time

# ==========================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM (MODERNO)
# ==========================================
st.set_page_config(
    page_title="actuar.group - Engineering Hub",
    page_icon="🛠️",
    layout="wide"
)

st.markdown("""
<style>
    /* Fundo Principal em Gradiente Escuro */
    .stApp { 
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%); 
        color: #c9d1d9;
    }
    
    /* Cards de Métricas e KPIs com efeito Glassmorphism */
    [data-testid="stMetric"] {
        background: rgba(22, 27, 34, 0.75);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
        backdrop-filter: blur(8px);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    [data-testid="stMetric"]:hover {
        border-color: #58a6ff;
        transform: translateY(-2px);
    }
    
    /* Botões Customizados */
    .stButton>button {
        border-radius: 8px;
        border: 1px solid #30363d;
        background-color: #21262d;
        color: #c9d1d9;
        font-weight: 500;
        transition: all 0.2s;
    }
    .stButton>button:hover {
        border-color: #58a6ff;
        color: #58a6ff;
        background-color: #30363d;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.2);
    }
    
    /* Expanders / Acordeões */
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
    }
    .streamlit-expanderHeader:hover {
        border-color: #58a6ff !important;
    }
    
    /* Estilização das Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22;
        border-radius: 8px 8px 0px 0px;
        border: 1px solid #30363d;
        border-bottom: none;
        padding: 8px 16px;
        color: #8b949e;
    }
    .stTabs [aria-selected="true"] {
        background-color: #21262d !important;
        color: #58a6ff !important;
        border-top: 2px solid #58a6ff !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXÃO E BANCO DE DADOS
# ==========================================
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

def buscar_ocorrencias_db():
    res = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
    return pd.DataFrame(res.data)

def registrar_log(usuario_email, acao, detalhes):
    try:
        supabase.table("audit_logs").insert({
            "usuario_email": usuario_email,
            "acao": acao,
            "detalhes": detalhes
        }).execute()
    except Exception as e:
        print(f"Erro ao registrar log: {e}")

def salvar_ocorrencia_db(dados, usuario_email):
    supabase.table("ocorrencias").insert(dados).execute()
    registrar_log(usuario_email, "CRIOU", f"Criou a ocorrência: {dados.get('problema')}")

def atualizar_ocorrencia_db(ocorrencia_id, dados_atualizados, usuario_email):
    try:
        supabase.table("ocorrencias").update(dados_atualizados).eq("id", ocorrencia_id).execute()
        registrar_log(usuario_email, "EDITOU", f"Editou a ocorrência ID #{ocorrencia_id}")
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar registro: {e}")
        return False

def deletar_ocorrencia_db(ocorrencia_id, usuario_email):
    try:
        supabase.table("comentarios").delete().eq("ocorrencia_id", ocorrencia_id).execute()
        res = supabase.table("ocorrencias").delete().eq("id", ocorrencia_id).execute()
        
        if res.data and len(res.data) > 0:
            registrar_log(usuario_email, "EXCLUIU", f"Excluiu a ocorrência ID #{ocorrencia_id}")
            return True
        else:
            st.error("O banco bloqueou a exclusão. Verifique se o RLS está liberado no Supabase.")
            return False
            
    except Exception as e:
        st.error(f"Erro ao excluir no Supabase: {e}")
        return False

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

def upload_anexo(file):
    try:
        ext = file.name.split('.')[-1]
        file_name = f"evidencia_{int(time.time())}.{ext}"
        file_bytes = file.getvalue()
        
        supabase.storage.from_("anexos_evidencias").upload(
            path=file_name,
            file=file_bytes,
            file_options={"content-type": file.type}
        )
        url_res = supabase.storage.from_("anexos_evidencias").get_public_url(file_name)
        return url_res
    except Exception as e:
        st.error(f"Erro no upload da imagem: {e}")
        return None

EMAILS_GESTORES = ["watson@actuar.group"]

def obter_perfil_usuario(user_id, email):
    if email.lower() in [e.lower() for e in EMAILS_GESTORES]:
        role_atribuida = "Admin"
    else:
        role_atribuida = "Analista"
        
    res = supabase.table("perfis").select("role").eq("user_id", user_id).execute()
    if res.data:
        if res.data[0]["role"] != role_atribuida and role_atribuida == "Admin":
            supabase.table("perfis").update({"role": "Admin"}).eq("user_id", user_id).execute()
        return role_atribuida
    
    supabase.table("perfis").insert({
        "user_id": user_id, 
        "email": email, 
        "role": role_atribuida
    }).execute()
    
    return role_atribuida

# ==========================================
# 3. CONTROLE DE SESSÃO E LOGIN PERSISTENTE
# ==========================================
if "user" not in st.session_state or st.session_state.user is None:
    session = supabase.auth.get_session()
    if session:
        st.session_state.user = session.user
        st.session_state.user_role = obter_perfil_usuario(session.user.id, session.user.email)
    else:
        st.session_state.user = None
        st.session_state.user_role = "Analista"

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
    st.session_state.user_role = "Analista"
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
        st.subheader("🔐 Central Técnica de Suporte")
        
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
# 4. CABEÇALHO E ESTRUTURA DE ABAS
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

try:
    df_ocorrencias = buscar_ocorrencias_db()
except Exception:
    df_ocorrencias = pd.DataFrame()

for col in ["sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "tempo_estimado", "votos_pos", "votos_neg", "anexo_url"]:
    if not df_ocorrencias.empty and col not in df_ocorrencias.columns:
        df_ocorrencias[col] = None

abas_navegacao = ["📋 Diagnósticos", "➕ Cadastrar Tratativa", "📊 Dashboard Executivo", "🤖 Assistente IA"]
if st.session_state.user_role == "Admin":
    abas_navegacao.append("📜 Audit Log (Gestão)")

tabs = st.tabs(abas_navegacao)

# ==========================================
# ABA 1: CONSULTA + EDIÇÃO (ADMIN) + AVALIAÇÃO + EXCLUSÃO
# ==========================================
with tabs[0]:
    st.subheader("🔍 Base Mapeada de Ocorrências")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    
    with col_f1:
        sist_opt = ["Todos"] + sorted(list(df_ocorrencias["sistema"].dropna().unique())) if not df_ocorrencias.empty else ["Todos"]
        f_sist = st.selectbox("Filtrar por Sistema:", sist_opt)
    with col_f2:
        hw_opt = ["Todos"] + sorted(list(df_ocorrencias["equipamento"].dropna().unique())) if not df_ocorrencias.empty else ["Todos"]
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
            ocor_id = int(row['id'])
            sist = row.get('sistema', 'N/A')
            hw = row.get('equipamento', 'N/A')
            prob = row.get('problema', 'Sem descrição')
            status = row.get('status', '🟢 Solução Definitiva')
            nivel = row.get('nivel', 'N1')
            tempo = row.get('tempo_estimado', '-')
            anexo = row.get('anexo_url', None)
            
            with st.expander(f"[{status}] {sist} + {hw} — {prob}"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**⏱️ Complexidade/Tempo:** {nivel} ({tempo})")
                
                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.success(f"**Solução Recomendada:**\n{row.get('solucao', '-')}")
                
                if anexo and pd.notna(anexo) and str(anexo).strip() != "":
                    st.markdown("---")
                    st.markdown("📷 **Evidência Anexada:**")
                    try:
                        st.image(str(anexo), width=500)
                    except Exception:
                        st.warning("Não foi possível carregar a imagem armazenada.")

                st.markdown("---")
                v_pos = row.get('votos_pos', 0) or 0
                v_neg = row.get('votos_neg', 0) or 0
                col_v1, col_v2, col_space = st.columns([1, 1, 4])
                
                with col_v1:
                    if st.button(f"👍 Funcionou ({v_pos})", key=f"pos_{ocor_id}"):
                        computar_voto(ocor_id, "pos", v_pos)
                        st.rerun()
                with col_v2:
                    if st.button(f"👎 Não funcionou ({v_neg})", key=f"neg_{ocor_id}"):
                        computar_voto(ocor_id, "neg", v_neg)
                        st.rerun()

                st.markdown("**💬 Observações dos Analistas:**")
                comentarios = buscar_comentarios(ocor_id)
                for c in comentarios:
                    st.caption(f"**{c['usuario']}**: {c['comentario']}")
                
                with st.form(key=f"form_coment_{ocor_id}"):
                    novo_coment = st.text_input("Adicionar dica de campo:", placeholder="Ex: Funciona apenas em modo Admin")
                    if st.form_submit_button("Enviar Comentário"):
                        if novo_coment:
                            salvar_comentario(ocor_id, st.session_state.user.email, novo_coment)
                            st.toast("Anotação adicionada!", icon="💬")
                            st.rerun()

                # ==========================================
                # BLOCO DE EXCLUSÃO E EDIÇÃO (EXCLUSIVO ADMIN / VOCÊ)
                # ==========================================
                if st.session_state.user_role == "Admin":
                    st.markdown("---")
                    
                    # Formulário Expansível de Edição
                    with st.expander(f"✏️ Editar Relato Finalizado #{ocor_id}"):
                        with st.form(key=f"form_edit_{ocor_id}"):
                            edit_col1, edit_col2 = st.columns(2)
                            
                            idx_sist = LISTA_SISTEMA.index(sist) if sist in LISTA_SISTEMA else 0
                            idx_hw = LISTA_HARDWARE.index(hw) if hw in LISTA_HARDWARE else 0
                            
                            lista_status = ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"]
                            idx_status = lista_status.index(status) if status in lista_status else 0
                            
                            lista_niveis = ["N1 - Fácil / Rápido", "N2 - Intermediário", "N3 - Avançado / Laboratório"]
                            idx_nivel = [i for i, n in enumerate(lista_niveis) if n.startswith(str(nivel)[:2])]
                            idx_nivel = idx_nivel[0] if idx_nivel else 0
                            
                            lista_tempos = ["15 minutos", "30 minutos", "1 hora", "2+ horas", "Requer troca/envio"]
                            idx_tempo = lista_tempos.index(tempo) if tempo in lista_tempos else 0

                            with edit_col1:
                                edit_sist = st.selectbox("💻 Sistema:", LISTA_SISTEMA, index=idx_sist, key=f"es_{ocor_id}")
                                edit_status = st.selectbox("📌 Status:", lista_status, index=idx_status, key=f"est_{ocor_id}")
                                edit_nivel = st.selectbox("📊 Nível:", lista_niveis, index=idx_nivel, key=f"en_{ocor_id}")
                            with edit_col2:
                                edit_hw = st.selectbox("⚙️ Hardware:", LISTA_HARDWARE, index=idx_hw, key=f"eh_{ocor_id}")
                                edit_tempo = st.selectbox("⏱️ Tempo Estimado:", lista_tempos, index=idx_tempo, key=f"et_{ocor_id}")
                                edit_anexo = st.file_uploader("📷 Substituir Foto/Anexo (Opcional):", type=["png", "jpg", "jpeg"], key=f"ea_{ocor_id}")

                            edit_prob = st.text_input("Problema (Sintoma):", value=prob, key=f"ep_{ocor_id}")
                            edit_motivo = st.text_area("Motivo (Causa Raiz):", value=row.get('motivo', ''), key=f"em_{ocor_id}")
                            edit_solucao = st.text_area("Solução Passo a Passo:", value=row.get('solucao', ''), key=f"eso_{ocor_id}")

                            if st.form_submit_button("💾 Salvar Alterações"):
                                nova_url_anexo = upload_anexo(edit_anexo) if edit_anexo else anexo
                                
                                dados_novos = {
                                    "sistema": edit_sist,
                                    "equipamento": edit_hw,
                                    "problema": edit_prob,
                                    "motivo": edit_motivo,
                                    "solucao": edit_solucao,
                                    "status": edit_status,
                                    "nivel": edit_nivel,
                                    "tempo_estimado": edit_tempo,
                                    "anexo_url": nova_url_anexo
                                }
                                
                                if atualizar_ocorrencia_db(ocor_id, dados_novos, st.session_state.user.email):
                                    st.toast(f"Tratativa #{ocor_id} atualizada com sucesso!", icon="✅")
                                    st.rerun()

                    # Botão de Exclusão
                    if st.button(f"🗑️ Excluir Tratativa #{ocor_id}", key=f"btn_del_{ocor_id}"):
                        sucesso = deletar_ocorrencia_db(ocor_id, st.session_state.user.email)
                        if sucesso:
                            st.toast(f"Tratativa #{ocor_id} excluída com sucesso!", icon="🗑️")
                            st.rerun()

# ==========================================
# ABA 2: CADASTRO COM ANEXO
# ==========================================
with tabs[1]:
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
            in_anexo = st.file_uploader("📷 Anexar Foto do Erro / Screenshot (Opcional):", type=["png", "jpg", "jpeg"])

        in_prob = st.text_input("Problema (Sintoma):", placeholder="Ex: Catraca trava comunicação ao autenticar facial")
        in_motivo = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Conflito de IPs na rede do cliente ou porta bloqueada")
        in_solucao = st.text_area("Solução Passo a Passo:", placeholder="Ex: Fixar IP na catraca e liberar a porta 8080")
        
        if st.form_submit_button("💾 Salvar Mapeamento no Banco"):
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
                salvar_ocorrencia_db(dados, st.session_state.user.email)
                st.toast("Tratativa salva com sucesso!", icon="🎉")
                st.rerun()
            else:
                st.error("Preencha o problema, motivo e solução.")

# ==========================================
# ABA 3: DASHBOARD EXEC (DESIGN TRANSPARENTE E COLORIDO)
# ==========================================
with tabs[2]:
    st.subheader("📊 Indicadores da Central Técnica")
    if df_ocorrencias.empty:
        st.info("Cadastre dados para gerar os gráficos.")
    else:
        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        kpi1.metric("Total Mapeado", len(df_ocorrencias))
        kpi2.metric("Hardware + Instável", df_ocorrencias["equipamento"].mode()[0] if not df_ocorrencias.empty else "N/A")
        kpi3.metric("Sistema + Citado", df_ocorrencias["sistema"].mode()[0] if not df_ocorrencias.empty else "N/A")
        
        n1_count = len(df_ocorrencias[df_ocorrencias["nivel"].str.contains("N1", na=False)])
        kpi4.metric("Resolvidos em N1", f"{(n1_count/len(df_ocorrencias))*100:.0f}%" if len(df_ocorrencias) > 0 else "0%")
        
        st.markdown("---")
        g1, g2 = st.columns(2)
        with g1:
            df_hw = df_ocorrencias['equipamento'].value_counts().reset_index()
            fig_hw = px.bar(
                df_hw,
                x='count', 
                y='equipamento', 
                color='equipamento',
                orientation='h',
                title="<b>Top Equipamentos com Falhas</b>",
                labels={'count': 'Ocorrências', 'equipamento': 'Hardware'},
                color_discrete_sequence=px.colors.qualitative.Bold
            )
            fig_hw.update_layout(
                showlegend=False,
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#c9d1d9'
            )
            st.plotly_chart(fig_hw, use_container_width=True)
            
        with g2:
            fig_sist = px.pie(
                df_ocorrencias, 
                names='sistema', 
                title="<b>Distribuição por Sistema (Software)</b>",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Safe
            )
            fig_sist.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='#c9d1d9'
            )
            st.plotly_chart(fig_sist, use_container_width=True)

# ==========================================
# ABA 4: ASSISTENTE IA
# ==========================================
with tabs[3]:
    st.subheader("🤖 Assistente Virtual de Diagnóstico")
    pergunta_tecnico = st.text_input("Descreva o problema enfrentado:", placeholder="Ex: Catraca não abre e perdeu conexão na porta serial")
    
    if pergunta_tecnico and not df_ocorrencias.empty:
        palavras = pergunta_tecnico.lower().split()
        matches = []
        for _, row in df_ocorrencias.iterrows():
            texto = f"{row['problema']} {row['motivo']} {row['equipamento']} {row['sistema']}".lower()
            score = sum(1 for p in palavras if p in texto)
            if score > 0:
                matches.append((score, row))
        
        matches.sort(key=lambda x: x[0], reverse=True)
        if matches:
            top_match = matches[0][1]
            st.markdown("### 💡 Diagnóstico Sugerido:")
            st.info(f"**Causa Provável:** {top_match['motivo']}")
            st.success(f"**Procedimento Recomendado:** {top_match['solucao']}")
        else:
            st.warning("Nenhum procedimento exato encontrado para essa busca.")

# ==========================================
# ABA 5: AUDIT LOG
# ==========================================
if st.session_state.user_role == "Admin" and len(tabs) > 4:
    with tabs[4]:
        st.subheader("📜 Histórico de Auditoria (Audit Log)")
        st.caption("Acompanhe todas as interações e alterações realizadas na plataforma.")
        
        try:
            res_logs = supabase.table("audit_logs").select("*").order("id", desc=True).limit(100).execute()
            df_logs = pd.DataFrame(res_logs.data)
            if not df_logs.empty:
                st.dataframe(
                    df_logs[["created_at", "usuario_email", "acao", "detalhes"]],
                    column_config={
                        "created_at": "Data/Hora",
                        "usuario_email": "Usuário",
                        "acao": "Ação",
                        "detalhes": "Detalhamento"
                    },
                    use_container_width=True
                )
            else:
                st.info("Nenhum histórico registrado no momento.")
        except Exception as e:
            st.error(f"Erro ao carregar log: {e}")