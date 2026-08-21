# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os
import time
import json

# ==========================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM (MODERNO DARK DEFINITIVO)
# ==========================================
st.set_page_config(
    page_title="actuar.group - Engineering Hub",
    page_icon="favicon.png",
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

def limpar_dados_para_json(dados):
    return {k: (None if pd.isna(v) else v) for k, v in dados.items()}

def salvar_ocorrencia_db(dados, usuario_email):
    try:
        dados_limpos = limpar_dados_para_json(dados)
        supabase.table("ocorrencias").insert(dados_limpos).execute()
        registrar_log(usuario_email, "CRIOU", f"Cadastrou a ocorrência: {dados.get('problema')}")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar no Supabase: {e}")
        return False

def processar_importacao_txt(file_bytes, usuario_email):
    try:
        try:
            texto = file_bytes.decode("utf-8")
        except Exception:
            texto = file_bytes.decode("latin-1")
            
        blocos = texto.split("Erro:")
        importadas = 0
        
        for bloco in blocos:
            if not bloco.strip():
                continue
            
            linhas = bloco.strip().split("\n")
            problema = linhas[0].strip()
            
            sistema = "Não se aplica / Geral"
            motivo_partes = []
            solucao_texto = ""
            
            for linha in linhas[1:]:
                l = linha.strip()
                if not l:
                    continue
                
                if l.startswith("Sistema:"):
                    l_lower = l.lower()
                    if "[x] ambos" in l_lower:
                        sistema = "Outro Sistema"
                    elif "[x] legado" in l_lower:
                        sistema = "Legado(Acesso)"
                    elif "[x] the new" in l_lower or "[x] edge" in l_lower:
                        sistema = "The new(Edge)"
                elif l.startswith("Onde ocorre:") or l.startswith("Como ocorre:") or l.startswith("Causa"):
                    motivo_partes.append(l)
                elif l.startswith("Solução:"):
                    s_limpa = l.replace("Solução:", "").strip()
                    if s_limpa.startswith("[") and s_limpa.endswith("]"):
                        s_limpa = s_limpa[1:-1].strip()
                    solucao_texto = s_limpa
                elif not l.startswith("Possíveis Causas"):
                    motivo_partes.append(l)
                    
            if problema:
                motivo_final = " | ".join(motivo_partes) if motivo_partes else "Não informado"
                passos_padrao = [{"passo": 1, "texto": solucao_texto if solucao_texto else "Não informada", "anexo": None}]
                
                dados = {
                    "sistema": sistema if sistema in LISTA_SISTEMA else "Outro Sistema",
                    "equipamento": "Indiferente",
                    "problema": problema,
                    "motivo": motivo_final,
                    "solucao": json.dumps(passos_padrao),
                    "status": "🟢 Solução Definitiva",
                    "nivel": "N1 - Fácil / Rápido",
                    "anexo_url": None
                }
                
                dados_limpos = limpar_dados_para_json(dados)
                supabase.table("ocorrencias").insert(dados_limpos).execute()
                importadas += 1
                
        if importadas > 0:
            registrar_log(usuario_email, "IMPORTOU", f"Importou {importadas} ocorrências via arquivo TXT.")
        return importadas
    except Exception as e:
        st.error(f"Erro ao processar importação do arquivo TXT: {e}")
        return 0

def atualizar_ocorrencia_db(ocorrencia_id, dados_atualizados, usuario_email):
    try:
        dados_atualizados.pop("origem", None)
        dados_limpos = limpar_dados_para_json(dados_atualizados)
        supabase.table("ocorrencias").update(dados_limpos).eq("id", ocorrencia_id).execute()
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

def gerenciar_voto(ocorrencia_id, tipo_voto, usuario_email):
    try:
        res_comentarios = supabase.table("comentarios").select("*").eq("ocorrencia_id", ocorrencia_id).eq("usuario", usuario_email).execute()
        comentarios_usuario = res_comentarios.data if res_comentarios.data else []
        
        voto_anterior = None
        comentario_voto_id = None
        for c in comentarios_usuario:
            if c["comentario"] == "[VOTO_POS]":
                voto_anterior = "pos"
                comentario_voto_id = c["id"]
                break
            elif c["comentario"] == "[VOTO_NEG]":
                voto_anterior = "neg"
                comentario_voto_id = c["id"]
                break
                
        res_ocor = supabase.table("ocorrencias").select("votos_pos, votos_neg").eq("id", ocorrencia_id).execute()
        if not res_ocor.data:
            return
        v_pos = res_ocor.data[0].get("votos_pos", 0) or 0
        v_neg = res_ocor.data[0].get("votos_neg", 0) or 0
        
        if voto_anterior is None:
            supabase.table("comentarios").insert({
                "ocorrencia_id": ocorrencia_id,
                "usuario": usuario_email,
                "comentario": f"[VOTO_{tipo_voto.upper()}]"
            }).execute()
            if tipo_voto == "pos":
                v_pos += 1
            else:
                v_neg += 1
        elif voto_anterior == tipo_voto:
            if comentario_voto_id:
                supabase.table("comentarios").delete().eq("id", comentario_voto_id).execute()
            if tipo_voto == "pos":
                v_pos = max(0, v_pos - 1)
            else:
                v_neg = max(0, v_neg - 1)
        else:
            if comentario_voto_id:
                supabase.table("comentarios").delete().eq("id", comentario_voto_id).execute()
            supabase.table("comentarios").insert({
                "ocorrencia_id": ocorrencia_id,
                "usuario": usuario_email,
                "comentario": f"[VOTO_{tipo_voto.upper()}]"
            }).execute()
            if tipo_voto == "pos":
                v_pos += 1
                v_neg = max(0, v_neg - 1)
            else:
                v_neg += 1
                v_pos = max(0, v_pos - 1)
                
        supabase.table("ocorrencias").update({"votos_pos": v_pos, "votos_neg": v_neg}).eq("id", ocorrencia_id).execute()
    except Exception as e:
        st.error(f"Erro ao gerenciar voto: {e}")

def buscar_comentarios(ocorrencia_id):
    res = supabase.table("comentarios").select("*").eq("ocorrencia_id", ocorrencia_id).order("id", desc=True).execute()
    return res.data

def salvar_comentario(ocorrencia_id, usuario, texto):
    supabase.table("comentarios").insert({
        "ocorrencia_id": ocorrencia_id,
        "usuario": usuario,
        "comentario": texto
    }).execute()

def upload_arquivo_unico(file):
    if not file:
        return None
    try:
        file_name = f"evidencia_{int(time.time())}_{file.name}"
        file_bytes = file.getvalue()
        
        try:
            supabase.storage.from_("anexos_evidencias").upload(
                path=file_name,
                file=file_bytes,
                file_options={"content-type": file.type}
            )
        except Exception:
            pass
            
        url_res = supabase.storage.get_public_url("anexos_evidencias", file_name) if hasattr(supabase.storage, "get_public_url") else supabase.storage.from_("anexos_evidencias").get_public_url(file_name)
        
        if isinstance(url_res, dict):
            u = url_res.get("publicUrl") or url_res.get("public_url") or str(url_res)
        else:
            u = str(url_res) if url_res else None
        return u
    except Exception as e:
        st.error(f"Erro no upload do arquivo {file.name}: {e}")
        return None

def upload_multiplos_arquivos(files):
    if not files:
        return None
    urls = []
    for f in files:
        u = upload_arquivo_unico(f)
        if u:
            urls.append(u)
    urls = list(dict.fromkeys(urls))
    return ",".join(urls) if urls else None

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
        return "Visitante"
    nome_base = email.split("@")[0].split(".")[0]
    return nome_base.capitalize()

# ==========================================
# 3. CONTROLE DE SESSÃO E LOGIN
# ==========================================
if "user" not in st.session_state:
    session = supabase.auth.get_session()
    if session:
        st.session_state.user = session.user
        st.session_state.user_role = obter_perfil_usuario(session.user.id, session.user.email)
    else:
        st.session_state.user = None
        st.session_state.user_role = "Visitante"

if "favoritos" not in st.session_state:
    st.session_state.favoritos = []

def fazer_login(email, password):
    try:
        response = supabase.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.session_state.user_role = obter_perfil_usuario(response.user.id, response.user.email)
        st.session_state.favoritos = []
        st.toast("Login realizado com sucesso!", icon="✅")
        st.rerun()
    except Exception as e:
        st.error(f"Falha na autenticação: {e}")

def fazer_logout():
    try:
        supabase.auth.sign_out()
    except Exception:
        pass
    st.session_state.user = None
    st.session_state.user_role = "Visitante"
    st.session_state.favoritos = []
    st.rerun()

with st.sidebar:
    if os.path.exists("logo_dark.png"):
        st.image("logo_dark.png", width=70)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=70)
        
    st.markdown("### 🔐 Área Administrativa")
    
    if st.session_state.user is None:
        st.info("Acesso público liberado. Faça login abaixo apenas se for Administrador.")
        with st.form("login_sidebar_form"):
            email_input = st.text_input("E-mail:")
            password_input = st.text_input("Senha:", type="password")
            if st.form_submit_button("Entrar como Admin"):
                if email_input and password_input:
                    fazer_login(email_input, password_input)
                else:
                    st.warning("Preencha e-mail e senha.")
    else:
        st.success(f"Logado como:\n**{st.session_state.user.email}**")
        if st.button("Sair da Conta (Logout)"):
            fazer_logout()

# ==========================================
# 4. CABEÇALHO E ESTRUTURA DE ABAS
# ==========================================
LISTA_SISTEMA = ["Legado(Acesso)", "The new(Edge)", "Edizz", "AcDesk", "Não se aplica / Geral", "Outro Sistema", "Indiferente"]
LISTA_HARDWARE = [
    "Catraca litnet1", "Catraca litnet2", "Catraca litnet3", "Catraca Edge",
    "Catraca Topdata", "Catraca Henry", "Catraca Tecnibra", "Catraca serial",
    "Catraca control ID block", "Catraca control ID block Next", "Control ID",
    "Control ID Max", "Webcam", "Facial EVO/Topdata", "Outro Hardware", "Indiferente"
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
    if st.session_state.user:
        role_badge = f"🛡️ **{st.session_state.user_role}**"
        primeiro_nome_logado = extrair_primeiro_nome(st.session_state.user.email)
        st.markdown(f"👤 **{primeiro_nome_logado}**<br>{role_badge}", unsafe_allow_html=True)
    else:
        st.markdown("🌐 **Modo Público (Visitante)**<br>Visualização livre sem restrições", unsafe_allow_html=True)

st.markdown("---")

try:
    df_ocorrencias = buscar_ocorrencias_db()
except Exception:
    df_ocorrencias = pd.DataFrame()

for col in ["sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "votos_pos", "votos_neg", "anexo_url"]:
    if not df_ocorrencias.empty and col not in df_ocorrencias.columns:
        df_ocorrencias[col] = None

# CRIAÇÃO DAS ABAS
abas_navegacao = ["📋 Diagnósticos", "⭐ Meus Favoritos", "➕ Cadastrar Tratativa"]
if st.session_state.user_role == "Admin":
    abas_navegacao.append("📥 Importar & Exportar (TXT)")
    abas_navegacao.append("📜 Audit Log (Gestão)")

tabs = st.tabs(abas_navegacao)

def renderizar_solucao_estruturada(solucao_data, anexo_global=None):
    if anexo_global and pd.notna(anexo_global) and str(anexo_global).strip() != "":
        st.markdown("📎 **Evidências do Problema (Sintoma):**")
        urls_problema = [u.strip() for u in str(anexo_global).split(",") if u.strip()]
        urls_problema = list(dict.fromkeys(urls_problema))
        
        for idx_prob, url_file in enumerate(urls_problema):
            nome_arquivo = url_file.split("/")[-1].split("?")[0]
            if "_" in nome_arquivo:
                partes_nome = nome_arquivo.split("_", 2)
                nome_exibicao = partes_nome[-1] if len(partes_nome) > 2 else nome_arquivo
            else:
                nome_exibicao = nome_arquivo
                
            extensoes_imagem = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
            if url_file.lower().endswith(extensoes_imagem):
                try:
                    st.image(url_file, width=450, caption=f"Imagem do Problema {idx_prob + 1}: {nome_exibicao}")
                except Exception:
                    st.markdown(f"📥 Baixar Arquivo {idx_prob + 1}: [**{nome_exibicao}**]({url_file})")
            else:
                st.markdown(f"📄 Arquivo {idx_prob + 1}: [**{nome_exibicao}**]({url_file})")
        st.markdown("---")

    passos = []
    try:
        if solucao_data and str(solucao_data).strip().startswith("["):
            passos = json.loads(str(solucao_data))
    except Exception:
        passos = []

    if passos and isinstance(passos, list):
        st.markdown("**Solução Recomendada em Etapas:**")
        for idx, item in enumerate(passos):
            num_passo = item.get("passo", idx + 1)
            texto_passo = item.get("texto", "")
            url_passo = item.get("anexo", None)
            
            st.markdown(f"**{num_passo}º** {texto_passo}")
            
            if url_passo and pd.notna(url_passo) and str(url_passo).strip() != "":
                urls_passo = [u.strip() for u in str(url_passo).split(",") if u.strip()]
                urls_passo = list(dict.fromkeys(urls_passo))
                
                for idx_f, url_file in enumerate(urls_passo):
                    nome_arquivo = url_file.split("/")[-1].split("?")[0]
                    if "_" in nome_arquivo:
                        partes_nome = nome_arquivo.split("_", 2)
                        nome_exibicao = partes_nome[-1] if len(partes_nome) > 2 else nome_arquivo
                    else:
                        nome_exibicao = nome_arquivo
                        
                    extensoes_imagem = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
                    if url_file.lower().endswith(extensoes_imagem):
                        try:
                            st.image(url_file, width=450, caption=f"Evidência {idx_f + 1} do Passo {num_passo}: {nome_exibicao}")
                        except Exception:
                            st.markdown(f"📥 Baixar Arquivo {idx_f + 1} do Passo {num_passo}: [**{nome_exibicao}**]({url_file})")
                    else:
                        st.markdown(f"📄 Arquivo {idx_f + 1} do Passo {num_passo}: [**{nome_exibicao}**]({url_file})")
            st.markdown("")
    else:
        st.success(f"**Solução Recomendada:**\n{solucao_data}")

# ==========================================
# ABA 1: CONSULTA COM TABELA INTERATIVA (SELEÇÃO POR CLIQUE)
# ==========================================
with tabs[0]:
    st.subheader("🔍 Base Mapeada de Ocorrências")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    
    with col_f1:
        sist_base = set(LISTA_SISTEMA)
        if not df_ocorrencias.empty and "sistema" in df_ocorrencias.columns:
            sist_base.update(df_ocorrencias["sistema"].dropna().unique())
        sist_opt = ["Todos"] + sorted(list(sist_base))
        f_sist = st.selectbox("Filtrar por Sistema:", sist_opt, key="f_sist_tab0")
    with col_f2:
        hw_base = set(LISTA_HARDWARE)
        if not df_ocorrencias.empty and "equipamento" in df_ocorrencias.columns:
            hw_base.update(df_ocorrencias["equipamento"].dropna().unique())
        hw_opt = ["Todos"] + sorted(list(hw_base))
        f_hw = st.selectbox("Filtrar por Hardware:", hw_opt, key="f_hw_tab0")
    with col_f3:
        f_busca = st.text_input("🔍 Buscar termo ou palavra-chave:", "", key="f_busca_tab0", placeholder="Ex: DLL, facial, timeout, IP...")

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
        st.markdown(f"### 📊 Resultados Filtrados ({len(df_filtered)} registros)")
        st.caption("💡 **Como usar:** Digite acima para refinar a busca e **clique diretamente na linha** da tabela abaixo para carregar os detalhes completos.")
        
        df_display = df_filtered[["id", "sistema", "equipamento", "problema", "status", "nivel"]].copy()
        
        # TABELA INTERATIVA COM SELEÇÃO POR CLIQUE DIRETO NA LINHA
        evento_tabela = st.dataframe(
            df_display,
            column_config={
                "id": "ID",
                "sistema": "Sistema",
                "equipamento": "Hardware",
                "problema": "Problema (Sintoma)",
                "status": "Status",
                "nivel": "Nível"
            },
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row"
        )
        
        # Identifica se o usuário clicou em alguma linha da tabela de forma segura
        ocor_id_selecionado = None
        selected_rows = []
        if isinstance(evento_tabela, dict) and "selection" in evento_tabela:
            selected_rows = evento_tabela["selection"].get("rows", [])
        elif hasattr(evento_tabela, "selection") and hasattr(evento_tabela.selection, "rows"):
            selected_rows = evento_tabela.selection.rows
            
        if selected_rows:
            idx_tabela = selected_rows[0]
            ocor_id_selecionado = int(df_display.iloc[idx_tabela]["id"])
        
        if ocor_id_selecionado:
            row = df_filtered[df_filtered["id"] == ocor_id_selecionado].iloc[0]
            ocor_id = int(row['id'])
            sist = row.get('sistema', 'N/A')
            hw = row.get('equipamento', 'N/A')
            prob = row.get('problema', 'Sem descrição')
            status = row.get('status', '🟢 Solução Definitiva')
            nivel = row.get('nivel', 'N1')
            anexo = row.get('anexo_url', None)
            solucao_val = row.get('solucao', '')
            
            is_fav = ocor_id in st.session_state.favoritos
            texto_botao_fav = "⭐ Remover dos Favoritos" if is_fav else "☆ Favoritar Chamado"
            
            st.markdown("---")
            with st.container(border=True):
                col_det_title, col_det_fav = st.columns([4, 1])
                with col_det_title:
                    st.markdown(f"### 🚨 [ID #{ocor_id}] {prob}")
                with col_det_fav:
                    if st.button(texto_botao_fav, key=f"fav_btn_{ocor_id}"):
                        if is_fav:
                            st.session_state.favoritos = [i for i in st.session_state.favoritos if i != ocor_id]
                            st.toast("Removido dos favoritos!", icon="🗑️")
                        else:
                            if ocor_id not in st.session_state.favoritos:
                                st.session_state.favoritos.append(ocor_id)
                            st.toast("Adicionado aos favoritos com sucesso!", icon="⭐")
                        st.rerun()
                
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**📌 Status:** {status}  \n**📊 Nível:** {nivel}")
                
                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.markdown("---")
                
                renderizar_solucao_estruturada(solucao_val, anexo)

                st.markdown("---")
                v_pos = row.get('votos_pos', 0) or 0
                v_neg = row.get('votos_neg', 0) or 0
                
                comentarios = buscar_comentarios(ocor_id)
                user_email_atual = st.session_state.user.email if st.session_state.user else "visitante@actuar.group"
                
                user_voto = None
                for c in comentarios:
                    if c["usuario"].lower() == user_email_atual.lower():
                        if c["comentario"] == "[VOTO_POS]":
                            user_voto = "pos"
                            break
                        elif c["comentario"] == "[VOTO_NEG]":
                            user_voto = "neg"
                            break

                texto_pos = f"👍 Funcionou ({v_pos})" + (" ✅" if user_voto == "pos" else "")
                texto_neg = f"👎 Não funcionou ({v_neg})" + (" ✅" if user_voto == "neg" else "")

                col_v1, col_v2, col_space = st.columns([1, 1, 4])
                with col_v1:
                    if st.button(texto_pos, key=f"pos_{ocor_id}"):
                        gerenciar_voto(ocor_id, "pos", user_email_atual)
                        st.rerun()
                with col_v2:
                    if st.button(texto_neg, key=f"neg_{ocor_id}"):
                        gerenciar_voto(ocor_id, "neg", user_email_atual)
                        st.rerun()

                st.markdown("**💬 Observações dos Analistas:**")
                comentarios_reais = [c for c in comentarios if not c['comentario'].startswith("[VOTO_")]
                for c in comentarios_reais:
                    st.caption(f"**{c['usuario']}**: {c['comentario']}")
                
                with st.form(key=f"form_coment_{ocor_id}"):
                    novo_coment = st.text_input("Adicionar dica de campo:", placeholder="Ex: Funciona apenas em modo Admin")
                    if st.form_submit_button("Enviar Comentário"):
                        if novo_coment:
                            salvar_comentario(ocor_id, user_email_atual, novo_coment)
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

                            with edit_col1:
                                edit_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE, index=idx_hw, key=f"eh_{ocor_id}")
                                edit_status = st.selectbox("📌 Status:", lista_status, index=idx_status, key=f"est_{ocor_id}")
                            with edit_col2:
                                edit_sist = st.selectbox("💻 Sistema:", LISTA_SISTEMA, index=idx_sist, key=f"es_{ocor_id}")
                                edit_nivel = st.selectbox("📊 Nível:", lista_niveis, index=idx_nivel, key=f"en_{ocor_id}")

                            edit_prob = st.text_input("Problema (Sintoma):", value=prob, key=f"ep_{ocor_id}")
                            
                            st.markdown("📎 **Editar / Adicionar Arquivos do Problema (Sintoma):**")
                            urls_prob_existentes = [u.strip() for u in str(anexo).split(",") if u.strip()] if anexo and pd.notna(anexo) else []
                            urls_prob_existentes = list(dict.fromkeys(urls_prob_existentes))
                            
                            urls_prob_para_manter = []
                            if urls_prob_existentes:
                                for idx_pi, url_pi in enumerate(urls_prob_existentes):
                                    nome_arq_pi = url_pi.split("/")[-1].split("?")[0]
                                    cp1, cp2 = st.columns([3, 1])
                                    with cp1:
                                        if url_pi.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                            try:
                                                st.image(url_pi, width=150)
                                            except Exception:
                                                st.markdown(f"📄 {nome_arq_pi}")
                                        else:
                                            st.markdown(f"📄 {nome_arq_pi}")
                                    with cp2:
                                        if st.checkbox("Manter", value=True, key=f"manter_prob_{ocor_id}_{idx_pi}"):
                                            urls_prob_para_manter.append(url_pi)

                            edit_files_prob = st.file_uploader("Adicionar novos arquivos ao Problema:", type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "xlsx", "csv", "zip"], accept_multiple_files=True, key=f"edit_prob_files_{ocor_id}")
                            
                            edit_motivo = st.text_area("Motivo (Causa Raiz):", value=row.get('motivo', ''), key=f"em_{ocor_id}")
                            
                            st.markdown("### 🛠️ Editar Passos da Solução")
                            
                            passos_atuais = []
                            try:
                                if solucao_val and str(solucao_val).strip().startswith("["):
                                    passos_atuais = json.loads(str(solucao_val))
                            except Exception:
                                pass
                            
                            if not passos_atuais:
                                passos_atuais = [{"passo": 1, "texto": str(solucao_val), "anexo": None}]

                            edit_passos_dados = []
                            for p_num in range(1, 4):
                                p_obj = next((x for x in passos_atuais if x.get("passo") == p_num), {"texto": "", "anexo": None})
                                st.markdown(f"**Passo {p_num}**")
                                e_txt = st.text_area(f"Texto do Passo {p_num}:", value=p_obj.get("texto", ""), key=f"edit_p_txt_{ocor_id}_{p_num}")
                                
                                anexo_atual_passo = p_obj.get("anexo")
                                urls_existentes = [u.strip() for u in str(anexo_atual_passo).split(",") if u.strip()] if anexo_atual_passo and pd.notna(anexo_atual_passo) else []
                                urls_existentes = list(dict.fromkeys(urls_existentes))
                                
                                urls_para_manter = []
                                if urls_existentes:
                                    st.markdown("📷 *Imagens atuais (desmarque para excluir):*")
                                    for idx_img, url_img in enumerate(urls_existentes):
                                        nome_arq = url_img.split("/")[-1].split("?")[0]
                                        col_prev, col_chk = st.columns([3, 1])
                                        with col_prev:
                                            if url_img.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                                                try:
                                                    st.image(url_img, width=150)
                                                except Exception:
                                                    st.markdown(f"📄 {nome_arq}")
                                            else:
                                                st.markdown(f"📄 {nome_arq}")
                                        with col_chk:
                                            if st.checkbox("Manter", value=True, key=f"manter_{ocor_id}_{p_num}_{idx_img}"):
                                                urls_para_manter.append(url_img)

                                e_files = st.file_uploader(f"Adicionar novas fotos ao Passo {p_num}:", type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "xlsx", "csv", "zip"], accept_multiple_files=True, key=f"edit_p_file_{ocor_id}_{p_num}")
                                
                                if e_txt.strip() or urls_para_manter or e_files:
                                    novas_urls = upload_multiplos_arquivos(e_files) if e_files else None
                                    lista_final_urls = list(urls_para_manter)
                                    if novas_urls:
                                        lista_final_urls.extend([u.strip() for u in novas_urls.split(",") if u.strip()])
                                    lista_final_urls = list(dict.fromkeys(lista_final_urls))
                                    url_final_passo = ",".join(lista_final_urls) if lista_final_urls else None
                                            
                                    edit_passos_dados.append({
                                        "passo": p_num,
                                        "texto": e_txt.strip(),
                                        "anexo": url_final_passo
                                    })

                            if st.form_submit_button("💾 Salvar Alterações"):
                                json_solucao_final = json.dumps(edit_passos_dados) if edit_passos_dados else ""
                                
                                novas_urls_prob = upload_multiplos_arquivos(edit_files_prob) if edit_files_prob else None
                                lista_final_prob = list(urls_prob_para_manter)
                                if novas_urls_prob:
                                    lista_final_prob.extend([u.strip() for u in novas_urls_prob.split(",") if u.strip()])
                                lista_final_prob = list(dict.fromkeys(lista_final_prob))
                                anexo_url_final = ",".join(lista_final_prob) if lista_final_prob else None
                                
                                dados_novos = {
                                    "sistema": edit_sist,
                                    "equipamento": edit_hw,
                                    "problema": edit_prob,
                                    "motivo": edit_motivo,
                                    "solucao": json_solucao_final,
                                    "status": edit_status,
                                    "nivel": edit_nivel,
                                    "anexo_url": anexo_url_final
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
# ABA 2: MEUS FAVORITOS
# ==========================================
with tabs[1]:
    st.subheader("⭐ Meus Chamados Frequentes & Favoritos")
    st.caption("Acesse rapidamente os problemas que você mais resolve.")
    
    if not st.session_state.favoritos or df_ocorrencias.empty:
        st.info("Você ainda não favoritou nenhuma ocorrência.")
    else:
        df_fav = df_ocorrencias[df_ocorrencias["id"].isin(st.session_state.favoritos)]
        
        for _, row in df_fav.iterrows():
            ocor_id = int(row['id'])
            sist = row.get('sistema', 'N/A')
            hw = row.get('equipamento', 'N/A')
            prob = row.get('problema', 'Sem descrição')
            status = row.get('status', '🟢 Solução Definitiva')
            nivel = row.get('nivel', 'N1')
            anexo = row.get('anexo_url', None)
            solucao_val = row.get('solucao', '')
            
            titulo_card_fav = f"⭐ [FAVORITO] {prob}  |  📂 [{sist} • {hw}]  —  {status}"
            
            with st.expander(titulo_card_fav):
                if st.button("❌ Remover dos Favoritos", key=f"rm_fav_tab_{ocor_id}"):
                    st.session_state.favoritos = [i for i in st.session_state.favoritos if i != ocor_id]
                    st.toast("Removido dos favoritos!", icon="🗑️")
                    st.rerun()
                
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**📌 Status:** {status}  \n**📊 Nível:** {nivel}")
                
                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.markdown("---")
                renderizar_solucao_estruturada(solucao_val, anexo)

# ==========================================
# ABA 3: CADASTRO COM ANEXOS NO PROBLEMA E PASSOS
# ==========================================
indice_cad = abas_navegacao.index("➕ Cadastrar Tratativa")
with tabs[indice_cad]:
    st.subheader("➕ Novo Mapeamento Técnico")
    with st.form("form_novo", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            in_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE)
            in_status = st.selectbox("📌 Status da Tratativa:", ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"])
        with col_c2:
            in_sist = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
            in_nivel = st.selectbox("📊 Nível de Complexidade:", ["N1 - Fácil / Rápido", "N2 - Intermediário", "N3 - Avançado / Laboratório"])

        in_prob = st.text_input("Problema (Sintoma):", placeholder="Ex: Catraca trava comunicação ao autenticar facial")
        in_files_prob = st.file_uploader("📎 Imagens ou Arquivos do Problema (Sintoma):", type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "xlsx", "csv", "zip"], accept_multiple_files=True, key="cad_prob_files")
        
        in_motivo = st.text_area("Motivo (Causa Raiz):", placeholder="Ex: Conflito de IPs na rede do cliente ou porta bloqueada")
        
        st.markdown("---")
        st.markdown("### 🛠️ Passos da Solução")
        st.caption("Adicione os procedimentos necessários para resolver o problema.")
        
        passos_novos_lista = []
        for p_idx in range(1, 4):
            st.markdown(f"**Passo {p_idx}**")
            col_p_txt, col_p_file = st.columns([2, 1])
            with col_p_txt:
                txt_p = st.text_area(f"Descrição do Passo {p_idx}:", placeholder=f"Ex: {p_idx}° Faça tal procedimento...", key=f"cad_p_txt_{p_idx}")
            with col_p_file:
                files_p = st.file_uploader(f"Anexos Passo {p_idx}", type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "xlsx", "csv", "zip"], accept_multiple_files=True, key=f"cad_p_file_{p_idx}")
            
            if txt_p.strip():
                url_anexo_p = upload_multiplos_arquivos(files_p) if files_p else None
                passos_novos_lista.append({
                    "passo": p_idx,
                    "texto": txt_p.strip(),
                    "anexo": url_anexo_p
                })
        
        if st.form_submit_button("💾 Salvar Mapeamento no Banco"):
            if in_prob and in_motivo and passos_novos_lista:
                json_solucao = json.dumps(passos_novos_lista)
                url_anexo_prob = upload_multiplos_arquivos(in_files_prob) if in_files_prob else None
                autor_reg = st.session_state.user.email if st.session_state.user else "visitante@actuar.group"
                
                dados = {
                    "sistema": in_sist,
                    "equipamento": in_hw,
                    "problema": in_prob,
                    "motivo": in_motivo,
                    "solucao": json_solucao,
                    "status": in_status,
                    "nivel": in_nivel,
                    "anexo_url": url_anexo_prob
                }
                if salvar_ocorrencia_db(dados, autor_reg):
                    st.toast("Tratativa salva com sucesso!", icon="🎉")
                    st.rerun()
            else:
                st.error("Preencha o problema, o motivo e ao menos o Passo 1 da solução.")

# ==========================================
# ABA 4: IMPORTAR & EXPORTAR BANCO EM TXT
# ==========================================
if st.session_state.user_role == "Admin" and "📥 Importar & Exportar (TXT)" in abas_navegacao:
    indice_export = abas_navegacao.index("📥 Importar & Exportar (TXT)")
    with tabs[indice_export]:
        st.subheader("📥 Importar & Exportar Base de Conhecimento (.TXT)")
        st.caption("Importe ocorrências em lote através de um arquivo `.TXT` estruturado ou baixe todo o histórico.")
        
        st.markdown("### 📤 Importar Ocorrências em Lote")
        with st.form("form_import_txt"):
            arquivo_txt = st.file_uploader("Selecione o arquivo .TXT estruturado:", type=["txt"])
            submitted_import = st.form_submit_button("🚀 Processar e Importar Ocorrências")
            if submitted_import:
                if arquivo_txt is not None:
                    qtd = processar_importacao_txt(arquivo_txt.getvalue(), st.session_state.user.email)
                    if qtd > 0:
                        st.success(f"{qtd} ocorrências foram importadas com sucesso!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.warning("Nenhuma ocorrência válida encontrada.")
                else:
                    st.warning("Envie um arquivo .TXT válido.")
        
        st.markdown("---")
        st.markdown("### 📥 Exportar Base Completa")
        if df_ocorrencias.empty:
            st.info("O banco de dados está vazio.")
        else:
            conteudo_txt = ""
            for _, row in df_ocorrencias.iterrows():
                conteudo_txt += f"Erro: {row.get('problema', 'N/A')}\n"
                conteudo_txt += f"Sistema: {row.get('sistema', 'N/A')}\n"
                conteudo_txt += f"Motivo: {row.get('motivo', 'N/A')}\n"
                conteudo_txt += f"Solução: {row.get('solucao', 'N/A')}\n"
                conteudo_txt += "-" * 50 + "\n\n"
                
            st.download_button(
                label="📥 Baixar Banco de Dados Completo em TXT",
                data=conteudo_txt,
                file_name="base_conhecimento_actuar.txt",
                mime="text/plain"
            )

# ==========================================
# ABA 5: AUDIT LOG
# ==========================================
if st.session_state.user_role == "Admin" and "📜 Audit Log (Gestão)" in abas_navegacao:
    indice_audit = abas_navegacao.index("📜 Audit Log (Gestão)")
    with tabs[indice_audit]:
        st.subheader("📜 Histórico de Auditoria (Audit Log)")
        st.caption("Acompanhe todas as interações e alterações realizadas.")
        
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