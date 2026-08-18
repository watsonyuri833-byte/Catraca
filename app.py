import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import time
import openai

# ==========================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM (MODERNO DARK DEFINITIVO)
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
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%) !important; 
        color: #c9d1d9 !important;
    }
    
    /* Textos Globais, Rótulos (Labels) e Títulos */
    .stApp p, .stApp label, .stApp span, h1, h2, h3, h4, h5, h6 {
        color: #e6edf3 !important;
    }
    
    /* CORREÇÃO DEFINITIVA DOS CAMPOS DE INPUT, SELECTBOX E TEXTAREA */
    div[data-baseweb="input"],
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] * {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }

    /* Input interno de texto e select */
    .stApp input, 
    .stApp textarea, 
    .stApp select,
    div[role="combobox"] {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border-color: #30363d !important;
    }

    /* Borda e Container das Caixas de Texto */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    
    /* Foco nos Campos de Entrada (Hover / Active) */
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"]:focus-within,
    textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 1px #58a6ff !important;
    }

    /* Cor dos Placeholders (Texto de exemplo) */
    ::placeholder, input::placeholder, textarea::placeholder {
        color: #8b949e !important;
        opacity: 1 !important;
    }

    /* Menus Suspensos / Dropdowns Abertos */
    ul[role="listbox"], ul[role="listbox"] li {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }

    /* Área de Upload de Arquivos (File Uploader) */
    [data-testid="stFileUploader"] {
        background-color: #161b22 !important;
        border: 1px dashed #30363d !important;
        border-radius: 8px !important;
        padding: 10px;
    }
    
    /* Botões Customizados */
    .stButton>button {
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
        background-color: #21262d !important;
        color: #c9d1d9 !important;
        font-weight: 500 !important;
        transition: all 0.2s !important;
    }
    .stButton>button:hover {
        border-color: #58a6ff !important;
        color: #58a6ff !important;
        background-color: #30363d !important;
        box-shadow: 0 0 10px rgba(88, 166, 255, 0.2) !important;
    }
    
    /* Expanders / Acordeões */
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
    }
    
    /* Estilização das Abas */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #30363d;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #161b22 !important;
        border-radius: 8px 8px 0px 0px !important;
        border: 1px solid #30363d !important;
        border-bottom: none !important;
        padding: 8px 16px !important;
        color: #8b949e !important;
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

def extrair_url_publica(res):
    """Função auxiliar robusta para extrair a string da URL pública do Supabase"""
    if not res:
        return None
    if isinstance(res, str):
        return res
    if isinstance(res, dict):
        return res.get("publicUrl") or res.get("data", {}).get("publicUrl") or res.get("signedURL")
    if hasattr(res, "public_url"):
        return res.public_url
    if hasattr(res, "publicUrl"):
        return res.publicUrl
    return str(res)

def upload_anexo(file):
    try:
        ext = file.name.split('.')[-1]
        file_name = f"evidencia_{int(time.time())}.{ext}"
        file_bytes = file.getvalue()
        
        try:
            supabase.storage.create_bucket("anexos_evidencias", {"public": True})
        except Exception:
            pass
            
        try:
            supabase.storage.from_("anexos_evidencias").upload(
                path=file_name,
                file=file_bytes,
                file_options={"content-type": file.type, "upsert": "true"}
            )
        except Exception:
            pass
            
        res = supabase.storage.from_("anexos_evidencias").get_public_url(file_name)
        return extrair_url_publica(res)
    except Exception as e:
        st.error(f"Erro no upload da imagem: {e}")
        return None

EMAILS_GESTORES = ["watson@actuar.group"]

def obter_perfil_usuario(user_id, email):
    if email.lower() in [e.lower() for e in EMAILS_GESTORES]:
        role_atribuida = "Admin"
    else:
        role_atribuida = "Analista"
        
    try:
        res = supabase.table("perfis").select("role").eq("user_id", user_id).execute()
        if res.data:
            if res.data[0]["role"] != role_atribuida and role_atribuida == "Admin":
                supabase.table("perfis").update({"role": "Admin"}).eq("user_id", user_id).execute()
            return role_atribuida
    except Exception:
        pass
    
    try:
        supabase.table("perfis").insert({
            "user_id": user_id, 
            "email": email, 
            "role": role_atribuida
        }).execute()
    except Exception:
        pass
    
    return role_atribuida

def extrair_primeiro_nome(email):
    if not email or "@" not in email:
        return "Usuário"
    nome_base = email.split("@")[0].split(".")[0]
    return nome_base.capitalize()

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
LISTA_SISTEMA = ["Legado(Acesso)", "The new(Edge)", "Não se aplica / Geral", "Outro Sistema", "Só Sistema"]
LISTA_HARDWARE = [
    "Catraca litnet1", "Catraca litnet2", "Catraca litnet3", "Catraca Edge",
    "Catraca Topdata", "Catraca Henry", "Catraca Tecnibra", "Catraca serial",
    "Catraca control ID block", "Catraca control ID block Next", "Control ID",
    "Control ID Max", "Webcam", "Facial EVO/Topdata", "Outro Hardware", "Só Catraca"
]

col_header_left, col_header_right = st.columns([6, 4])

with col_header_left:
    col_img_logo, col_txt_logo = st.columns([1, 4])
    with col_img_logo:
        if os.path.exists("logo_dark.png"):
            st.image("logo_dark.png", width=60)
        elif os.path.exists("logo.png"):
            st.image("logo.png", width=60)
    with col_txt_logo:
        st.markdown("<h1 style='margin:0; padding-top:5px;'>actuar.group</h1>", unsafe_allow_html=True)

with col_header_right:
    role_badge = f"🛡️ **{st.session_state.user_role}**"
    primeiro_nome_logado = extrair_primeiro_nome(st.session_state.user.email)
    
    col_av, col_txt, col_btn = st.columns([1, 2, 1])
    with col_av:
        st.markdown("👤")
    with col_txt:
        st.markdown(f"**{primeiro_nome_logado}**<br>{role_badge}", unsafe_allow_html=True)
    with col_btn:
        if st.button("Sair"):
            fazer_logout()

st.markdown("---")

try:
    df_ocorrencias = buscar_ocorrencias_db()
except Exception:
    df_ocorrencias = pd.DataFrame()

for col in ["sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "tempo_estimado", "votos_pos", "votos_neg", "anexo_url", "autor_email"]:
    if not df_ocorrencias.empty and col not in df_ocorrencias.columns:
        df_ocorrencias[col] = None

abas_navegacao = ["📋 Diagnósticos", "➕ Cadastrar Tratativa"]
if st.session_state.user_role == "Admin":
    abas_navegacao.append("🤖 Assistente IA")
    abas_navegacao.append("📜 Audit Log (Gestão)")

tabs = st.tabs(abas_navegacao)

# ==========================================
# ABA 1: CONSULTA + EDIÇÃO + AVALIAÇÃO + EXCLUSÃO
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
            
            email_autor = row.get('autor_email', None)
            nome_autor = extrair_primeiro_nome(email_autor) if email_autor else "Equipe Técnica"
            
            titulo_card = f"[{status}] {sist} + {hw} — {prob}  |  👤 Relatado por: {nome_autor}"
            
            with st.expander(titulo_card):
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

                if st.session_state.user_role == "Admin":
                    st.markdown("---")
                    
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
                                edit_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE, index=idx_hw, key=f"eh_{ocor_id}")
                                edit_status = st.selectbox("📌 Status:", lista_status, index=idx_status, key=f"est_{ocor_id}")
                                edit_nivel = st.selectbox("📊 Nível:", lista_niveis, index=idx_nivel, key=f"en_{ocor_id}")
                            with edit_col2:
                                edit_sist = st.selectbox("💻 Sistema:", LISTA_SISTEMA, index=idx_sist, key=f"es_{ocor_id}")
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

                    if st.button(f"🗑️ Excluir Tratativa #{ocor_id}", key=f"btn_del_{ocor_id}"):
                        sucesso = deletar_ocorrencia_db(ocor_id, st.session_state.user.email)
                        if sucesso:
                            st.toast(f"Tratativa #{ocor_id} excluída com sucesso!", icon="🗑️")
                            st.rerun()

# ==========================================
# ABA 2: CADASTRO COM ANEXO E AUTOR
# ==========================================
with tabs[1]:
    st.subheader("➕ Novo Mapeamento Técnico")
    with st.form("form_novo", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            in_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE)
            in_status = st.selectbox("📌 Status da Tratativa:", ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"])
            in_nivel = st.selectbox("📊 Nível de Complexidade:", ["N1 - Fácil / Rápido", "N2 - Intermediário", "N3 - Avançado / Laboratório"])
        with col_c2:
            in_sist = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
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
                    "anexo_url": anexo_url,
                    "autor_email": st.session_state.user.email
                }
                salvar_ocorrencia_db(dados, st.session_state.user.email)
                st.toast("Tratativa salva com sucesso!", icon="🎉")
                st.rerun()
            else:
                st.error("Preencha o problema, motivo e solução.")

# ==========================================
# ABA 3: ASSISTENTE IA (EXCLUSIVO ADMIN)
# ==========================================
if st.session_state.user_role == "Admin":
    indice_ia = 2 if "🤖 Assistente IA" in abas_navegacao else 0
    # Como as abas dependem do perfil, ajustamos dinamicamente caso o índice mude
    # Vamos recriar as abas de forma segura checando a lista de abas ativas