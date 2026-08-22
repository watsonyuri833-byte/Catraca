# -*- coding: utf-8 -*-
import json
import os
import re
import time
import pandas as pd
import streamlit as st
from supabase import Client, create_client
from google import genai
from google.genai import types

# ==========================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM
# ==========================================
st.set_page_config(
    page_title="actuar.group - Engineering Hub",
    page_icon="favicon.png",
    layout="wide",
)

st.markdown(
    """
<style>
    .stApp { 
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%) !important; 
        color: #c9d1d9 !important;
    }
    .stApp p, .stApp label, .stApp span, h1, h2, h3, h4, h5, h6 {
        color: #e6edf3 !important;
    }
    div[data-baseweb="input"],
    div[data-baseweb="input"] > div,
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] * {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }
    .stApp input, 
    .stApp textarea, 
    .stApp select,
    div[role="combobox"] {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
        border-color: #30363d !important;
    }
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    div[data-baseweb="input"]:focus-within,
    div[data-baseweb="select"]:focus-within,
    textarea:focus {
        border-color: #58a6ff !important;
        box-shadow: 0 0 0 1px #58a6ff !important;
    }
    ::placeholder, input::placeholder, textarea::placeholder {
        color: #8b949e !important;
        opacity: 1 !important;
    }
    ul[role="listbox"], ul[role="listbox"] li {
        background-color: #161b22 !important;
        color: #f0f6fc !important;
    }
    [data-testid="stFileUploader"] {
        background-color: #161b22 !important;
        border: 1px dashed #30363d !important;
        border-radius: 8px !important;
        padding: 10px;
    }
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
    .streamlit-expanderHeader {
        background-color: #161b22 !important;
        border-radius: 8px !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
    }
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
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. CONEXÃO SUPABASE & GEMINI IA
# ==========================================
INIT_URL = st.secrets.get("SUPABASE_URL", "https://agrvmqsspfqhfyxketia.supabase.co")
INIT_KEY = st.secrets.get("SUPABASE_KEY", "")
INIT_GEMINI = st.secrets.get("GEMINI_API_KEY", "")

if "active_url" not in st.session_state:
    st.session_state.active_url = INIT_URL
if "active_key" not in st.session_state:
    st.session_state.active_key = INIT_KEY
if "active_gemini_key" not in st.session_state:
    st.session_state.active_gemini_key = INIT_GEMINI

@st.cache_resource
def init_supabase(url: str, key: str) -> Client:
    return create_client(url, key)

try:
    if st.session_state.active_key:
        supabase = init_supabase(st.session_state.active_url, st.session_state.active_key)
    else:
        supabase = None
except Exception as e:
    st.error(f"Erro ao inicializar cliente Supabase: {e}")
    supabase = None

@st.cache_resource
def init_gemini(api_key: str):
    if api_key:
        return genai.Client(api_key=api_key)
    return None

gemini_client = init_gemini(st.session_state.active_gemini_key)

# ==========================================
# 3. MÉTODOS DE BANCO DE DADOS
# ==========================================
def buscar_ocorrencias_db():
    if not supabase or not st.session_state.active_key:
        st.warning("⚠️ Chave de API do Supabase ausente nas configurações internas.")
        return pd.DataFrame()
    try:
        res = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        colunas_obrigatorias = ["id", "sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "votos_pos", "votos_neg", "anexo_url"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = None
        return df
    except Exception as e:
        err_msg = str(e)
        if "401" in err_msg or "Unauthorized" in err_msg or "JWT" in err_msg:
            st.error("🚨 **Erro 401 (Autenticação Negada):** A chave de acesso ao Supabase expirou ou é inválida.")
        else:
            st.error(f"Erro ao buscar ocorrências no banco: {e}")
        return pd.DataFrame()

def buscar_manuais_db():
    if not supabase or not st.session_state.active_key:
        return pd.DataFrame()
    try:
        res = supabase.table("manuais_produto").select("*").order("id", desc=True).execute()
        return pd.DataFrame(res.data)
    except Exception:
        return pd.DataFrame()

def registrar_log(usuario_email, acao, detalhes):
    if not supabase:
        return
    try:
        supabase.table("audit_logs").insert({
            "usuario_email": usuario_email,
            "acao": acao,
            "detalhes": detalhes,
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

def salvar_manual_db(dados, usuario_email):
    try:
        dados_limpos = limpar_dados_para_json(dados)
        supabase.table("manuais_produto").insert(dados_limpos).execute()
        registrar_log(usuario_email, "MANUAL_CRIADO", f"Cadastrou manual técnico: {dados.get('titulo')}")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar manual: {e}")
        return False

def deletar_manual_db(manual_id, usuario_email):
    try:
        supabase.table("manuais_produto").delete().eq("id", manual_id).execute()
        registrar_log(usuario_email, "MANUAL_EXCLUIDO", f"Excluiu o manual ID #{manual_id}")
        return True
    except Exception as e:
        st.error(f"Erro ao excluir manual: {e}")
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
                elif (
                    l.startswith("Onde ocorre:")
                    or l.startswith("Como ocorre:")
                    or l.startswith("Causa")
                ):
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
                passos_padrao = [{
                    "passo": 1,
                    "texto": solucao_texto if solucao_texto else "Não informada",
                    "anexo": None,
                }]

                dados = {
                    "sistema": sistema if sistema in LISTA_SISTEMA else "Outro Sistema",
                    "equipamento": "Indiferente",
                    "problema": problema,
                    "motivo": motivo_final,
                    "solucao": json.dumps(passos_padrao),
                    "status": "🟢 Solução Definitiva",
                    "nivel": "N1 - Fácil / Rápido",
                    "anexo_url": None,
                }

                dados_limpos = limpar_dados_para_json(dados)
                supabase.table("ocorrencias").insert(dados_limpos).execute()
                importadas += 1

        if importadas > 0:
            registrar_log(usuario_email, "IMPORTOU", f"Importou {importadas} ocorrências via TXT.")
        return importadas
    except Exception as e:
        st.error(f"Erro ao processar importação do arquivo TXT: {e}")
        return 0

def upload_arquivo_unico(file):
    if not file:
        return None
    try:
        file_name = f"evidencia_{int(time.time())}_{file.name}"
        file_bytes = file.getvalue()

        try:
            supabase.storage.from_("anexos_evidencias").upload(
                path=file_name, file=file_bytes, file_options={"content-type": file.type}
            )
        except Exception:
            pass

        url_res = (
            supabase.storage.get_public_url("anexos_evidencias", file_name)
            if hasattr(supabase.storage, "get_public_url")
            else supabase.storage.from_("anexos_evidencias").get_public_url(file_name)
        )

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

# ==========================================
# 4. MOTOR IA GEMINI + RAG HÍBRIDO (BANCO -> FEEDBACK -> IA GENERALISTA)
# ==========================================
def buscar_contexto_relevante(query, df_ocorrencias, df_manuais):
    if not query:
        return [], []

    query_lower = query.lower().strip()
    stopwords = {"a", "o", "de", "do", "da", "em", "um", "uma", "para", "com", "que", "os", "as", "dos", "das", "por", "mais", "como", "mas", "foi", "ao", "ou", "no", "na"}
    palavras_query = [p.lower() for p in re.findall(r"\w+", query_lower) if p.lower() not in stopwords and len(p) > 1]

    if not palavras_query:
        palavras_query = re.findall(r"\w+", query_lower)

    resultados_ocor = []
    if not df_ocorrencias.empty:
        for _, row in df_ocorrencias.iterrows():
            texto = f"{row.get('problema', '')} {row.get('motivo', '')} {row.get('equipamento', '')} {row.get('sistema', '')} {row.get('solucao', '')}".lower()
            score = sum(3 if p in str(row.get('problema', '')).lower() else 1 for p in palavras_query if p in texto)
            if score > 0:
                resultados_ocor.append((score, row.to_dict()))
        resultados_ocor.sort(key=lambda x: x[0], reverse=True)

    resultados_man = []
    if not df_manuais.empty:
        for _, row in df_manuais.iterrows():
            texto = f"{row.get('titulo', '')} {row.get('sistema_produto', '')} {row.get('conteudo', '')}".lower()
            score = sum(4 if p in str(row.get('titulo', '')).lower() else 1 for p in palavras_query if p in texto)
            if score > 0:
                resultados_man.append((score, row.to_dict()))
        resultados_man.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in resultados_ocor[:4]], [r[1] for r in resultados_man[:4]]

def processar_resposta_gemini(query, contexto_ocor, contexto_man, historico_tentativa=None):
    if not gemini_client:
        return "⚠️ Chave de API do Gemini não configurada no sistema. Por favor, contate o administrador."

    has_db_context = bool(contexto_ocor or contexto_man)

    prompt_sistema = """Você é o Assistente Especialista em Suporte Técnico da actuar.group.
Sua missão é responder dúvidas dos técnicos sobre sistemas de controle de acesso (Legado/Acesso, The New/Edge), catracas e leitores de identificação facial (Control ID).

Diretrizes de Atuação:
1. Se houver dados da BASE TÉCNICA (Manuais ou Ocorrências), use-os prioritariamente.
2. Se o técnico indicar que a solução anterior NÃO FUNCIONOU ou se a base de dados for insuficiente, acione seu Conhecimento Técnico Geral de IA especialista em redes, hardware, protocolo TCP/IP, comunicação serial e software de controle de acesso para dar uma solução alternativa avançada.
3. Seja direto, técnico e especifique procedimentos claros em etapas numeradas.
4. Ao usar conhecimento geral (fora da base oficial), explicite brevemente que se trata de um diagnóstico avançado via IA.
"""

    contexto_str = ""
    
    if historico_tentativa:
        contexto_str += "--- HISTÓRICO DE TENTATIVA ANTERIOR (NÃO FUNCIONOU) ---\n"
        contexto_str += f"Pergunta Anterior: {historico_tentativa.get('pergunta_orig')}\n"
        contexto_str += f"Resposta Anterior Fornecida: {historico_tentativa.get('resposta_orig')}\n"
        contexto_str += f"Feedback do Técnico: {query}\n\n"
        contexto_str += "INSTRUÇÃO ADICIONAL: O procedimento anterior falhou. Analise a falha e traga um novo diagnóstico aprofundado.\n\n"
    else:
        contexto_str += f"PERGUNTA DO TÉCNICO: {query}\n\n"

    if has_db_context:
        contexto_str += "--- DADOS ENCONTRADOS NA BASE DE CONHECIMENTO INTERNA ---\n"
        if contexto_man:
            for m in contexto_man:
                contexto_str += f"[MANUAL] Título: {m.get('titulo')} | HW: {m.get('hardware')}\nConteúdo: {m.get('conteudo')}\n\n"
        if contexto_ocor:
            for o in contexto_ocor:
                contexto_str += f"[OCORRÊNCIA] Problema: {o.get('problema')} | Causa: {o.get('motivo')}\nSolução: {o.get('solucao')}\n\n"
    else:
        contexto_str += "--- ATENÇÃO: NENHUM REGISTRO EXATO ENCONTRADO NA BASE DE DADOS. USE A INTELIGÊNCIA GERAL DE IA TÉCNICA ---\n\n"

    try:
        response = gemini_client.models.generate_content(
            model='gemini-3.6-flash',
            contents=contexto_str,
            config=types.GenerateContentConfig(
                system_instruction=prompt_sistema,
                temperature=0.2,
            )
        )
        return response.text
    except Exception as e:
        return f"Erro ao processar consulta com o Gemini: {e}"

# ==========================================
# 5. SIDEBAR LIMPA
# ==========================================
if "favoritos" not in st.session_state:
    st.session_state.favoritos = []

with st.sidebar:
    if os.path.exists("logo_dark.png"):
        st.image("logo_dark.png", width=70)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=70)

    st.markdown("### actuar.group")
    st.caption("Engineering Hub & Support Center")
    st.markdown("---")

    if os.path.exists("catraca.png"):
        st.image("catraca.png", use_container_width=True)
        st.caption(
            "<div style='text-align: center; color: #8b949e; font-size: 11px;'>"
            "Hardware Oficial<br><b>actuar.group</b></div>",
            unsafe_allow_html=True,
        )

# ==========================================
# 6. CABEÇALHO E NAVEGAÇÃO PRINCIPAL
# ==========================================
LISTA_SISTEMA = [
    "Legado(Acesso)",
    "The new(Edge)",
    "Edizz",
    "AcDesk",
    "Não se aplica / Geral",
    "Outro Sistema",
    "Indiferente",
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
    "Outro Hardware",
    "Indiferente",
]

col_header_left, _ = st.columns([6, 4])
with col_header_left:
    col_img_logo, col_txt_logo = st.columns([1, 4])
    with col_img_logo:
        if os.path.exists("logo_dark.png"):
            st.image("logo_dark.png", width=60)
        elif os.path.exists("logo.png"):
            st.image("logo.png", width=60)
    with col_txt_logo:
        st.markdown(
            "<h1 style='margin:0; padding-top:5px;'>actuar.group</h1>",
            unsafe_allow_html=True,
        )

st.markdown("---")

df_ocorrencias = buscar_ocorrencias_db()
df_manuais = buscar_manuais_db()

abas_navegacao = [
    "📋 Diagnósticos",
    "🤖 Gemini IA Copilot",
    "📚 Manuais & Produtos",
    "📺 Modo TV",
    "⭐ Meus Favoritos",
    "➕ Cadastrar Tratativa",
    "📥 Importar & Exportar (TXT)",
    "📜 Audit Log (Gestão)",
]

tabs = st.tabs(abas_navegacao)

def renderizar_solucao_estruturada(solucao_data, anexo_global=None):
    if anexo_global and pd.notna(anexo_global) and str(anexo_global).strip() != "":
        urls_problema = [u.strip() for u in str(anexo_global).split(",") if u.strip()]
        urls_problema = list(dict.fromkeys(urls_problema))

        if urls_problema:
            with st.expander(f"📎 Ver Evidências do Problema ({len(urls_problema)} arquivo(s))", expanded=False):
                for idx_prob, url_file in enumerate(urls_problema):
                    nome_arquivo = url_file.split("/")[-1].split("?")[0]
                    nome_exibicao = nome_arquivo.split("_", 2)[-1] if "_" in nome_arquivo else nome_arquivo
                    if url_file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                        try:
                            st.image(url_file, width=450, caption=f"Imagem {idx_prob + 1}: {nome_exibicao}")
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
                if urls_passo:
                    with st.expander(f"📷 Anexos do Passo {num_passo}", expanded=False):
                        for idx_f, url_file in enumerate(urls_passo):
                            nome_arquivo = url_file.split("/")[-1].split("?")[0]
                            nome_exibicao = nome_arquivo.split("_", 2)[-1] if "_" in nome_arquivo else nome_arquivo
                            if url_file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                                try:
                                    st.image(url_file, width=450, caption=f"Passo {num_passo}: {nome_exibicao}")
                                except Exception:
                                    st.markdown(f"📥 Baixar: [**{nome_exibicao}**]({url_file})")
                            else:
                                st.markdown(f"📄 Arquivo: [**{nome_exibicao}**]({url_file})")
            st.markdown("")
    else:
        st.success(f"**Solução Recomendada:**\n{solucao_data}")

# ==========================================
# ABA 1: DIAGNÓSTICOS
# ==========================================
indice_diag = abas_navegacao.index("📋 Diagnósticos")
with tabs[indice_diag]:
    st.subheader("🔍 Base Mapeada de Ocorrências")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])

    with col_f1:
        sist_base = set(LISTA_SISTEMA)
        if not df_ocorrencias.empty and "sistema" in df_ocorrencias.columns:
            sist_base.update(df_ocorrencias["sistema"].dropna().unique())
        f_sist = st.selectbox("Filtrar por Sistema:", ["Todos"] + sorted(list(sist_base)), key="f_sist_tab0")
    with col_f2:
        hw_base = set(LISTA_HARDWARE)
        if not df_ocorrencias.empty and "equipamento" in df_ocorrencias.columns:
            hw_base.update(df_ocorrencias["equipamento"].dropna().unique())
        f_hw = st.selectbox("Filtrar por Hardware:", ["Todos"] + sorted(list(hw_base)), key="f_hw_tab0")
    with col_f3:
        f_busca = st.text_input("🔍 Buscar termo ou palavra-chave:", "", key="f_busca_tab0", placeholder="Ex: Facial, stream, catraca, IP...")

    df_filtered = df_ocorrencias.copy()
    if not df_filtered.empty:
        if f_sist != "Todos":
            df_filtered = df_filtered[df_filtered["sistema"] == f_sist]
        if f_hw != "Todos":
            df_filtered = df_filtered[df_filtered["equipamento"] == f_hw]
        if f_busca:
            palavras = [p.strip() for p in f_busca.split() if p.strip()]
            if palavras:
                regex_pattern = "|".join([re.escape(p) for p in palavras])
                df_filtered = df_filtered[
                    df_filtered["problema"].astype(str).str.contains(regex_pattern, case=False, na=False, regex=True)
                    | df_filtered["motivo"].astype(str).str.contains(regex_pattern, case=False, na=False, regex=True)
                    | df_filtered["solucao"].astype(str).str.contains(regex_pattern, case=False, na=False, regex=True)
                ]

    if df_filtered.empty:
        st.info("Nenhuma ocorrência encontrada. Verifique os filtros ou as credenciais do banco de dados.")
    else:
        st.markdown(f"### 📊 Resultados Filtrados ({len(df_filtered)} registros)")
        df_display = df_filtered[["sistema", "equipamento", "problema", "status", "nivel"]].copy().reset_index(drop=True)

        evento_tabela = st.dataframe(
            df_display,
            column_config={
                "sistema": "Sistema",
                "equipamento": "Hardware",
                "problema": "Problema (Sintoma)",
                "status": "Status",
                "nivel": "Nível",
            },
            hide_index=True,
            use_container_width=True,
            on_select="rerun",
            selection_mode="single-row",
        )

        ocor_id_selecionado = None
        selected_rows = []
        if isinstance(evento_tabela, dict) and "selection" in evento_tabela:
            selected_rows = evento_tabela["selection"].get("rows", [])
        elif hasattr(evento_tabela, "selection") and hasattr(evento_tabela.selection, "rows"):
            selected_rows = evento_tabela.selection.rows

        if selected_rows:
            idx_tabela = selected_rows[0]
            df_filtered_reset = df_filtered.reset_index(drop=True)
            ocor_id_selecionado = int(df_filtered_reset.iloc[idx_tabela]["id"])

        if ocor_id_selecionado:
            row = df_filtered[df_filtered["id"] == ocor_id_selecionado].iloc[0]
            ocor_id = int(row["id"])
            sist = row.get("sistema", "N/A")
            hw = row.get("equipamento", "N/A")
            prob = row.get("problema", "Sem descrição")
            status = row.get("status", "🟢 Solução Definitiva")
            nivel = row.get("nivel", "N1")
            anexo = row.get("anexo_url", None)
            solucao_val = row.get("solucao", "")

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
                            st.toast("Adicionado aos favoritos!", icon="⭐")
                        st.rerun()

                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**📌 Status:** {status}  \n**📊 Nível:** {nivel}")

                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.markdown("---")

                renderizar_solucao_estruturada(solucao_val, anexo)

# ==========================================
# ABA 2: GEMINI IA COPILOT (MÓDULO INTERATIVO EM TÓPICO ÚNICO)
# ==========================================
indice_copilot = abas_navegacao.index("🤖 Gemini IA Copilot")
with tabs[indice_copilot]:
    st.subheader("🤖 Assistente IA de Diagnóstico Avançado")
    st.caption("O Copilot inicia buscando no banco de dados. Caso a instrução não resolva, comente no mesmo campo informando o erro para acionar a inteligência geral de IA.")

    # Estados para o ciclo de pergunta/resposta
    if "ultima_pergunta" not in st.session_state:
        st.session_state.ultima_pergunta = None
    if "ultima_resposta" not in st.session_state:
        st.session_state.ultima_resposta = None
    if "feedback_tentativa" not in st.session_state:
        st.session_state.feedback_tentativa = None

    col_cp_top, col_cp_reset = st.columns([5, 1])
    with col_cp_reset:
        if st.button("🔄 Nova Dúvida"):
            st.session_state.ultima_pergunta = None
            st.session_state.ultima_resposta = None
            st.session_state.feedback_tentativa = None
            st.rerun()

    user_query = st.chat_input("Descreva a dúvida ou informe se a solução anterior não deu certo...")

    if user_query:
        with st.spinner("Analisando e processando diagnóstico..."):
            # Se já existia uma pergunta/resposta prévia, entende-se que o novo input é um FEEDBACK do técnico na mesma dúvida
            if st.session_state.ultima_pergunta and st.session_state.ultima_resposta:
                st.session_state.feedback_tentativa = {
                    "pergunta_orig": st.session_state.ultima_pergunta,
                    "resposta_orig": st.session_state.ultima_resposta
                }
                
                # Busca novamente banco com a soma do contexto ou vai direto para refinamento
                query_combinada = f"{st.session_state.ultima_pergunta} {user_query}"
                match_ocor, match_man = buscar_contexto_relevante(query_combinada, df_ocorrencias, df_manuais)
                
                resposta_ia = processar_resposta_gemini(
                    query=user_query,
                    contexto_ocor=match_ocor,
                    contexto_man=match_man,
                    historico_tentativa=st.session_state.feedback_tentativa
                )
                
                st.session_state.ultima_pergunta = f"**Dúvida Inicial:** {st.session_state.ultima_pergunta}\n\n**Retorno do Técnico:** {user_query}"
                st.session_state.ultima_resposta = resposta_ia

            else:
                # Pergunta inicial: Prioridade Banco de Dados
                match_ocor, match_man = buscar_contexto_relevante(user_query, df_ocorrencias, df_manuais)
                resposta_ia = processar_resposta_gemini(
                    query=user_query,
                    contexto_ocor=match_ocor,
                    contexto_man=match_man,
                    historico_tentativa=None
                )
                
                st.session_state.ultima_pergunta = user_query
                st.session_state.ultima_resposta = resposta_ia

    # Exibição limpa (Apenas 1 bloco ativo por vez na tela)
    if st.session_state.ultima_pergunta and st.session_state.ultima_resposta:
        with st.chat_message("user"):
            st.markdown(st.session_state.ultima_pergunta)

        with st.chat_message("assistant"):
            st.markdown(st.session_state.ultima_resposta)
            st.info("💡 *Se a solução acima não resolver, digite abaixo exatamente o que ocorreu (ex: 'Não funcionou, deu o erro X') para o Copilot gerar um diagnóstico de IA mais profundo.*")
    else:
        with st.chat_message("assistant"):
            st.markdown("Olá! Sou o Copilot com IA do **actuar.group**. Digite o problema técnico para buscar a solução na base de dados.")

# ==========================================
# ABA 3: MANUAIS & PRODUTOS
# ==========================================
indice_manuais = abas_navegacao.index("📚 Manuais & Produtos")
with tabs[indice_manuais]:
    st.subheader("📚 Base de Conhecimento de Produtos e Manuais Técnicos")

    with st.form("form_novo_manual", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_sistema = st.selectbox("💻 Sistema / Módulo Afetado:", LISTA_SISTEMA, key="manual_sistema")
            m_titulo = st.text_input("Título do Manual / Especificação:", placeholder="Ex: Manual do Modo Stream Control ID")
        with col_m2:
            m_hardware = st.selectbox("⚙️ Hardware Relacionado:", LISTA_HARDWARE, key="manual_hw")

        m_conteudo = st.text_area("📄 Conteúdo Completo e Instruções do Produto:", placeholder="Escreva aqui todas as instruções...", height=200)

        if st.form_submit_button("💾 Salvar Manual na Base de Conhecimento"):
            if m_titulo and m_conteudo:
                dados_manual = {
                    "sistema_produto": m_sistema,
                    "hardware": m_hardware,
                    "titulo": m_titulo,
                    "conteudo": m_conteudo,
                }
                if salvar_manual_db(dados_manual, "tecnico@actuar.group"):
                    st.toast("Manual cadastrado com sucesso!", icon="🎉")
                    st.rerun()
            else:
                st.error("Preencha o título e o conteúdo antes de salvar.")

    st.markdown("---")
    if not df_manuais.empty:
        for _, row in df_manuais.iterrows():
            m_id = row["id"]
            with st.expander(f"📖 [ID #{m_id}] {row.get('titulo')} ({row.get('sistema_produto')} / {row.get('hardware')})"):
                st.markdown(f"**Conteúdo Registrado:**\n{row.get('conteudo')}")
                if st.button(f"🗑️ Excluir Manual #{m_id}", key=f"del_manual_{m_id}"):
                    if deletar_manual_db(m_id, "tecnico@actuar.group"):
                        st.toast("Manual excluído!", icon="🗑️")
                        st.rerun()

# ==========================================
# ABA 4: MODO TV
# ==========================================
indice_tv = abas_navegacao.index("📺 Modo TV")
with tabs[indice_tv]:
    st.subheader("📺 Painel TV - Monitoramento em Tempo Real")
    if not df_ocorrencias.empty:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total de Ocorrências", len(df_ocorrencias))
        m2.metric("Soluções Definitivas", len(df_ocorrencias[df_ocorrencias["status"].str.contains("Definitiva", case=False, na=False)]))
        m3.metric("Contornos / Paliativos", len(df_ocorrencias[df_ocorrencias["status"].str.contains("Contorno", case=False, na=False)]))
        m4.metric("Bugs / Em Análise", len(df_ocorrencias[df_ocorrencias["status"].str.contains("Bug", case=False, na=False)]))

        st.markdown("---")
        st.dataframe(df_ocorrencias[["sistema", "equipamento", "problema", "status", "nivel"]].head(12), use_container_width=True)

# ==========================================
# ABA 5: FAVORITOS
# ==========================================
indice_fav = abas_navegacao.index("⭐ Meus Favoritos")
with tabs[indice_fav]:
    st.subheader("⭐ Meus Chamados Frequentes & Favoritos")
    if st.session_state.favoritos and not df_ocorrencias.empty:
        df_fav = df_ocorrencias[df_ocorrencias["id"].isin(st.session_state.favoritos)]
        for _, row in df_fav.iterrows():
            ocor_id = int(row["id"])
            with st.expander(f"⭐ [FAVORITO #{ocor_id}] {row.get('problema')}"):
                renderizar_solucao_estruturada(row.get("solucao"), row.get("anexo_url"))

# ==========================================
# ABA 6: CADASTRAR TRATATIVA
# ==========================================
indice_cad = abas_navegacao.index("➕ Cadastrar Tratativa")
with tabs[indice_cad]:
    st.subheader("➕ Novo Mapeamento Técnico")
    with st.form("form_novo", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            in_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE)
            in_status = st.selectbox("📌 Status:", ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"])
        with col_c2:
            in_sist = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
            in_nivel = st.selectbox("📊 Nível:", ["N1 - Fácil / Rápido", "N2 - Intermediário", "N3 - Avançado / Laboratório"])

        in_prob = st.text_input("Problema (Sintoma):")
        in_files_prob = st.file_uploader("📎 Arquivos do Problema:", accept_multiple_files=True, key="cad_prob_files")
        in_motivo = st.text_area("Motivo (Causa Raiz):")

        st.markdown("### 🛠️ Passos da Solução")
        passos_novos_lista = []
        for p_idx in range(1, 4):
            col_p_txt, col_p_file = st.columns([2, 1])
            with col_p_txt:
                txt_p = st.text_area(f"Descrição do Passo {p_idx}:", key=f"cad_p_txt_{p_idx}")
            with col_p_file:
                files_p = st.file_uploader(f"Anexos Passo {p_idx}", accept_multiple_files=True, key=f"cad_p_file_{p_idx}")

            if txt_p.strip():
                url_anexo_p = upload_multiplos_arquivos(files_p) if files_p else None
                passos_novos_lista.append({"passo": p_idx, "texto": txt_p.strip(), "anexo": url_anexo_p})

        if st.form_submit_button("💾 Salvar Mapeamento no Banco"):
            if in_prob and in_motivo and passos_novos_lista:
                json_solucao = json.dumps(passos_novos_lista)
                url_anexo_prob = upload_multiplos_arquivos(in_files_prob) if in_files_prob else None

                dados = {
                    "sistema": in_sist,
                    "equipamento": in_hw,
                    "problema": in_prob,
                    "motivo": in_motivo,
                    "solucao": json_solucao,
                    "status": in_status,
                    "nivel": in_nivel,
                    "anexo_url": url_anexo_prob,
                }
                if salvar_ocorrencia_db(dados, "tecnico@actuar.group"):
                    st.toast("Tratativa salva com sucesso!", icon="🎉")
                    st.rerun()
            else:
                st.error("Preencha o problema, motivo e ao menos 1 passo da solução.")

# ==========================================
# ABA 7: IMPORTAR & EXPORTAR TXT
# ==========================================
indice_export = abas_navegacao.index("📥 Importar & Exportar (TXT)")
with tabs[indice_export]:
    st.subheader("📥 Importar & Exportar Base Completa em .TXT")

    with st.form("form_import_txt"):
        arquivo_txt = st.file_uploader("Selecione o arquivo .TXT:", type=["txt"])
        if st.form_submit_button("🚀 Processar Importação"):
            if arquivo_txt is not None:
                qtd = processar_importacao_txt(arquivo_txt.getvalue(), "tecnico@actuar.group")
                if qtd > 0:
                    st.success(f"{qtd} ocorrências foram importadas com sucesso!")
                    time.sleep(1)
                    st.rerun()

    st.markdown("---")
    conteudo_txt = "=" * 70 + "\nACTUAR.GROUP - EXPORTAÇÃO DA BASE DE CONHECIMENTO\n" + "=" * 70 + "\n\n"

    if not df_manuais.empty:
        conteudo_txt += "--- SEÇÃO 1: MANUAIS ---\n"
        for _, row in df_manuais.iterrows():
            conteudo_txt += f"Título: {row.get('titulo')}\nConteúdo: {row.get('conteudo')}\n" + "-" * 50 + "\n"

    if not df_ocorrencias.empty:
        conteudo_txt += "\n--- SEÇÃO 2: OCORRÊNCIAS ---\n"
        for _, row in df_ocorrencias.iterrows():
            conteudo_txt += f"Erro: {row.get('problema')}\nSistema: {row.get('sistema')}\nSolução: {row.get('solucao')}\n" + "-" * 50 + "\n"

    st.download_button(
        label="📥 Baixar Base Unificada Completa (TXT)",
        data=conteudo_txt,
        file_name="base_conhecimento_actuar.txt",
        mime="text/plain",
    )

# ==========================================
# ABA 8: AUDIT LOG
# ==========================================
indice_audit = abas_navegacao.index("📜 Audit Log (Gestão)")
with tabs[indice_audit]:
    st.subheader("📜 Histórico de Auditoria (Audit Log)")
    try:
        if supabase and st.session_state.active_key:
            res_logs = supabase.table("audit_logs").select("*").order("id", desc=True).limit(100).execute()
            df_logs = pd.DataFrame(res_logs.data)
            if not df_logs.empty:
                st.dataframe(df_logs[["created_at", "usuario_email", "acao", "detalhes"]], use_container_width=True)
            else:
                st.info("Nenhum registro de log encontrado.")
    except Exception as e:
        st.error(f"Erro ao carregar log: {e}")