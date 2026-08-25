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

    @keyframes balancoCatraca {
        0% { transform: rotate(-6deg); }
        50% { transform: rotate(6deg); }
        100% { transform: rotate(-6deg); }
    }

    [data-testid="stSidebar"] div[data-testid="stImage"]:nth-of-type(2) img {
        animation: balancoCatraca 3s ease-in-out infinite !important;
        border-radius: 8px;
        transform-origin: center center;
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
        return pd.DataFrame()
    try:
        res = supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        colunas_obrigatorias = ["id", "sistema", "equipamento", "problema", "motivo", "solucao", "status", "nivel", "votos_pos", "votos_neg", "anexo_url"]
        for col in colunas_obrigatorias:
            if col not in df.columns:
                df[col] = None
        return df
    except Exception:
        return pd.DataFrame()

def buscar_manuais_db():
    if not supabase or not st.session_state.active_key:
        return pd.DataFrame()
    try:
        res = supabase.table("manuais_produto").select("*").order("id", desc=True).execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            if "hardware" not in df.columns:
                df["hardware"] = "Indiferente"
            if "link_url" not in df.columns:
                df["link_url"] = None
            if "link_titulo" not in df.columns:
                df["link_titulo"] = None
        return df
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

def salvar_manual_db(dados, usuario_email):
    try:
        dados_limpos = limpar_dados_para_json(dados)
        supabase.table("manuais_produto").insert(dados_limpos).execute()
        registrar_log(usuario_email, "MANUAL_CRIADO", f"Cadastrou item no mapa: {dados.get('titulo')}")
        return True
    except Exception as e:
        st.error(f"Erro ao salvar: {e}")
        return False

def atualizar_manual_db(manual_id, dados, usuario_email):
    try:
        dados_limpos = limpar_dados_para_json(dados)
        supabase.table("manuais_produto").update(dados_limpos).eq("id", manual_id).execute()
        registrar_log(usuario_email, "MANUAL_ATUALIZADO", f"Atualizou o item ID #{manual_id}: {dados.get('titulo')}")
        return True
    except Exception as e:
        st.error(f"Erro ao atualizar: {e}")
        return False

def deletar_manual_db(manual_id, usuario_email):
    try:
        supabase.table("manuais_produto").delete().eq("id", manual_id).execute()
        registrar_log(usuario_email, "MANUAL_EXCLUIDO", f"Excluiu o item ID #{manual_id}")
        return True
    except Exception as e:
        st.error(f"Erro ao excluir: {e}")
        return False

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
    except Exception:
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

def renderizar_bloco_imagens(urls_str, titulo_secao=""):
    if urls_str and pd.notna(urls_str) and str(urls_str).strip() != "":
        urls = [u.strip() for u in str(urls_str).split(",") if u.strip()]
        if urls:
            if titulo_secao:
                st.markdown(f"**{titulo_secao}**")
            for idx, url_file in enumerate(urls):
                nome_arquivo = url_file.split("/")[-1].split("?")[0]
                nome_exibicao = nome_arquivo.split("_", 2)[-1] if "_" in nome_arquivo else nome_arquivo
                if url_file.lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp")):
                    try:
                        st.image(url_file, width=450, caption=f"Imagem {idx + 1}: {nome_exibicao}")
                    except Exception:
                        st.markdown(f"📥 Baixar Arquivo {idx + 1}: [**{nome_exibicao}**]({url_file})")
                else:
                    st.markdown(f"📄 Arquivo {idx + 1}: [**{nome_exibicao}**]({url_file})")

def renderizar_bloco_links(link_url, link_titulo):
    if link_url and pd.notna(link_url) and str(link_url).strip() != "":
        titulo_exibicao = link_titulo if (link_titulo and pd.notna(link_titulo) and str(link_titulo).strip() != "") else "Acessar Link Externo / Vídeo"
        st.markdown(f"🔗 [**{titulo_exibicao}**]({link_url.strip()})", unsafe_allow_html=True)

def renderizar_conteudo_estruturado(conteudo_data, anexo_global=None):
    renderizar_bloco_imagens(anexo_global, "📎 Evidências do Tópico")
    
    passos = []
    try:
        if conteudo_data and str(conteudo_data).strip().startswith("["):
            passos = json.loads(str(conteudo_data))
    except Exception:
        passos = []

    if passos and isinstance(passos, list):
        st.markdown("**Procedimento em Etapas:**")
        for idx, item in enumerate(passos):
            num_passo = item.get("passo", idx + 1)
            texto_passo = item.get("texto", "")
            url_passo = item.get("anexo", None)
            erro_passo = item.get("erro", "")
            erro_anexo = item.get("erro_anexo", None)
            link_passo = item.get("link_url", "")
            link_titulo_passo = item.get("link_titulo", "")

            st.markdown(f"**{num_passo}º** {texto_passo}")
            
            if link_passo:
                renderizar_bloco_links(link_passo, link_titulo_passo)

            if url_passo:
                with st.expander(f"📷 Anexos do Passo {num_passo}", expanded=False):
                    renderizar_bloco_imagens(url_passo)

            if erro_passo and str(erro_passo).strip() != "":
                with st.expander(f"⚠️ Erros / Possíveis Falhas (Passo {num_passo})", expanded=False):
                    st.markdown(f"{erro_passo}")
                    if erro_anexo:
                        renderizar_bloco_imagens(erro_anexo, "📸 Imagens/Evidências do Erro:")

            st.markdown("")
    else:
        st.markdown(f"{conteudo_data}")

# ==========================================
# 4. MOTOR IA GEMINI + RAG HÍBRIDO E CONVERSA
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
            texto = f"{row.get('titulo', '')} {row.get('sistema_produto', '')} {row.get('hardware', '')} {row.get('conteudo', '')}".lower()
            score = sum(4 if p in str(row.get('titulo', '')).lower() else 1 for p in palavras_query if p in texto)
            if score > 0:
                resultados_man.append((score, row.to_dict()))
        resultados_man.sort(key=lambda x: x[0], reverse=True)

    return [r[1] for r in resultados_ocor[:4]], [r[1] for r in resultados_man[:4]]

def processar_resposta_gemini_chat(historico_conversa, contexto_ocor, contexto_man):
    if not gemini_client:
        return "⚠️ Chave de API do Gemini não configurada no sistema. Por favor, contate o administrador."

    prompt_sistema = """Você é o Assistente Especialista em Suporte Técnico da actuar.group.
Sua missão é auxiliar os técnicos analisando obrigatoriamente a base de dados interna de ocorrências e manuais fornecida abaixo, combinando-a com seu raciocínio técnico avançado.
"""

    contexto_str = "=== HISTÓRICO COMPLETO DA CONVERSA NO TÓPICO ===\n"
    for msg in historico_conversa:
        papel = "TÉCNICO" if msg["role"] == "user" else "COPILOT"
        contexto_str += f"{papel}: {msg['content']}\n\n"

    contexto_str += "=== DADOS DISPONÍVEIS NA BASE TÉCNICA INTERNA (OCORRÊNCIAS & MANUAIS) ===\n"
    if contexto_man:
        for m in contexto_man:
            contexto_str += f"[MAPA MENTAL/MANUAL] Título: {m.get('titulo')} | Galho: {m.get('sistema_produto')} > {m.get('hardware')}\nConteúdo: {m.get('conteudo')}\n"
            if m.get('link_url'):
                contexto_str += f"Link Relacionado ({m.get('link_titulo')}): {m.get('link_url')}\n"
            contexto_str += "\n"
    if contexto_ocor:
        for o in contexto_ocor:
            contexto_str += f"[OCORRÊNCIA] Problema: {o.get('problema')} | Causa: {o.get('motivo')}\nSolução: {o.get('solucao')}\n\n"
    
    if not contexto_man and not contexto_ocor:
        contexto_str += "[AVISO] Nenhum registro exato encontrado na base interna. Utilize seu conhecimento técnico especializado para orientar o procedimento.\n\n"

    try:
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
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
# 5. SIDEBAR
# ==========================================
if "favoritos" not in st.session_state:
    st.session_state.favoritos = []

if "editando_manual_id" not in st.session_state:
    st.session_state.editando_manual_id = None

with st.sidebar:
    if os.path.exists("logo_dark.png"):
        st.image("logo_dark.png", width=70)
    elif os.path.exists("logo.png"):
        st.image("logo.png", width=70)

    st.markdown("### actuar.group")
    st.caption("Engineering Hub & Support Center")
    st.markdown("---")

    if os.path.exists("catraca.png"):
        st.image("catraca.png", width=240)
        st.caption(
            "<div style='text-align: center; color: #8b949e; font-size: 11px;'>"
            "Hardware Oficial<br><b>actuar.group</b></div>",
            unsafe_allow_html=True,
        )

# ==========================================
# 6. CABEÇALHO E NAVEGAÇÃO PRINCIPAL
# ==========================================
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
    "🌳 Mapa de Onboarding (Legado vs EDesk)",
    "📚 Manuais & Produtos",
    "📺 Modo TV",
    "⭐ Meus Favoritos",
    "➕ Cadastrar Tratativa",
    "📥 Importar & Exportar (TXT)",
    "📜 Audit Log (Gestão)",
]

tabs = st.tabs(abas_navegacao)

# ==========================================
# ABA 1: DIAGNÓSTICOS
# ==========================================
indice_diag = abas_navegacao.index("📋 Diagnósticos")
with tabs[indice_diag]:
    st.subheader("🔍 Base Mapeada de Ocorrências")
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])

    with col_f1:
        sist_base = set()
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

                renderizar_conteudo_estruturado(solucao_val, anexo)

# ==========================================
# ABA 2: GEMINI IA COPILOT
# ==========================================
indice_copilot = abas_navegacao.index("🤖 Gemini IA Copilot")
with tabs[indice_copilot]:
    st.subheader("🤖 Assistente IA de Diagnóstico Avançado")
    st.caption("O Copilot cruza instantaneamente a sua dúvida com o banco de dados interno e entrega a resposta fundamentada pela IA.")

    if "historico_copilot" not in st.session_state:
        st.session_state.historico_copilot = []

    col_cp_top, col_cp_reset = st.columns([5, 1])
    with col_cp_reset:
        if st.button("🔄 Novo Tópico", key="reset_copilot"):
            st.session_state.historico_copilot = []
            st.rerun()

    for msg in st.session_state.historico_copilot:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = st.chat_input("Digite sua dúvida técnica para o Copilot...", key="input_copilot")

    if user_input:
        st.session_state.historico_copilot.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Analisando banco de dados e gerando resposta com IA..."):
                duvida_primeira = st.session_state.historico_copilot[0]["content"] if len(st.session_state.historico_copilot) > 0 else user_input
                query_busca = f"{duvida_primeira} {user_input}"

                match_ocor, match_man = buscar_contexto_relevante(query_busca, df_ocorrencias, df_manuais)

                resposta_ia = processar_resposta_gemini_chat(
                    historico_conversa=st.session_state.historico_copilot,
                    contexto_ocor=match_ocor,
                    contexto_man=match_man
                )

                st.markdown(resposta_ia)
                st.session_state.historico_copilot.append({"role": "assistant", "content": resposta_ia})

# ==========================================
# ABA 3: MAPA DE ONBOARDING (ÁRVORE VISUAL & CADASTRO / EDIÇÃO)
# ==========================================
indice_onboarding = abas_navegacao.index("🌳 Mapa de Onboarding (Legado vs EDesk)")
with tabs[indice_onboarding]:
    st.subheader("🌳 Mapa Hierárquico de Onboarding (Legado vs EDesk)")
    st.caption("Navegue pelos galhos do mapa mental abaixo ou edite/adicione nós conforme necessário.")

    galhos_principais = ["Legado", "EDesk"]
    
    col_m_acao, col_m_filtro = st.columns([2, 2])
    with col_m_acao:
        modo_mapa = st.radio("Modo do Mapa:", ["👁️ Visualizar Mapa de Nós", "➕ Adicionar Novo Nó / Galho"], horizontal=True)
    with col_m_filtro:
        galho_selecionado_filtro = st.selectbox("Galho Principal Alvo:", galhos_principais, key="filtro_galho_raiz")

    st.markdown("---")

    # SE ESTIVER EDITANDO UM NÓ ESPECÍFICO
    if st.session_state.editando_manual_id is not None and not df_manuais.empty:
        item_edit_df = df_manuais[df_manuais["id"] == st.session_state.editando_manual_id]
        if not item_edit_df.empty:
            item_edit = item_edit_df.iloc[0]
            st.markdown(f"### ✏️ Editando Nó ID #{item_edit['id']}")
            
            passos_atuais_edicao = []
            try:
                if item_edit.get("conteudo") and str(item_edit.get("conteudo")).strip().startswith("["):
                    passos_atuais_edicao = json.loads(str(item_edit.get("conteudo")))
            except Exception:
                passos_atuais_edicao = []

            with st.form("form_editar_no_mapa"):
                edit_galho = st.selectbox("Galho Principal:", galhos_principais, index=galhos_principais.index(item_edit.get("sistema_produto")) if item_edit.get("sistema_produto") in galhos_principais else 0)
                edit_subgalho = st.selectbox("Subpasta do Galho:", ["Manual de Instalação", "Erros e Soluções", "Outro Subtópico"], index=0)
                edit_titulo = st.text_input("Título do Tópico / Erro:", value=str(item_edit.get("titulo", "")))

                st.markdown("---")
                st.markdown("🛠️ **Passos do Procedimento:**")
                passos_editados_lista = []
                for p_idx in range(1, 6):
                    passo_existente = next((p for p in passos_atuais_edicao if p.get("passo") == p_idx), {})
                    
                    st.markdown(f"**Passo {p_idx}**")
                    col_p_txt, col_p_file = st.columns([2, 1])
                    with col_p_txt:
                        txt_p = st.text_area(f"Descrição do Passo {p_idx}:", value=passo_existente.get("texto", ""), key=f"edit_p_txt_{p_idx}", height=70)
                    with col_p_file:
                        files_p = st.file_uploader(f"Novos Anexos Passo {p_idx}", accept_multiple_files=True, key=f"edit_p_file_{p_idx}")

                    col_l_passo, col_err_passo = st.columns(2)
                    with col_l_passo:
                        link_url_p = st.text_input(f"Link do Passo {p_idx} (Opcional):", value=passo_existente.get("link_url", ""), key=f"edit_p_link_{p_idx}")
                        link_tit_p = st.text_input(f"Título do Link {p_idx}:", value=passo_existente.get("link_titulo", ""), key=f"edit_p_link_tit_{p_idx}")
                    with col_err_passo:
                        txt_err_p = st.text_area(f"⚠️ Possíveis Erros / Falhas do Passo {p_idx}:", value=passo_existente.get("erro", ""), key=f"edit_p_err_{p_idx}", height=70)
                        
                        # Bloco de gerenciamento / exclusão individual de imagens de erro existentes
                        urls_erro_atual = passo_existente.get("erro_anexo", None)
                        imagens_erro_mantidas = []
                        if urls_erro_atual and str(urls_erro_atual).strip():
                            st.markdown("🗑️ **Excluir imagens de erro individuais:**")
                            lista_urls_err = [u.strip() for u in str(urls_erro_atual).split(",") if u.strip()]
                            for img_idx, img_url in enumerate(lista_urls_err):
                                nome_img = img_url.split("/")[-1].split("?")[0]
                                mantem = st.checkbox(f"Manter imagem: {nome_img[:20]}...", value=True, key=f"edit_mantem_err_{p_idx}_{img_idx}")
                                if mantem:
                                    imagens_erro_mantidas.append(img_url)

                        files_err = st.file_uploader(f"Adicionar imagens para Erros (Passo {p_idx})", accept_multiple_files=True, key=f"edit_p_err_file_{p_idx}")

                    if txt_p.strip():
                        url_anexo_p = upload_multiplos_arquivos(files_p) if files_p else passo_existente.get("anexo", None)
                        
                        # Processa novos arquivos de erro e junta com os mantidos
                        novas_urls_err = upload_multiplos_arquivos(files_err) if files_err else None
                        if novas_urls_err:
                            lista_novas = [u.strip() for u in novas_urls_err.split(",") if u.strip()]
                            imagens_erro_mantidas.extend(lista_novas)
                        
                        final_erro_anexo = ",".join(imagens_erro_mantidas) if imagens_erro_mantidas else None

                        passos_editados_lista.append({
                            "passo": p_idx,
                            "texto": txt_p.strip(),
                            "anexo": url_anexo_p,
                            "erro": txt_err_p.strip() if txt_err_p else "",
                            "erro_anexo": final_erro_anexo,
                            "link_url": link_url_p.strip() if link_url_p else "",
                            "link_titulo": link_tit_p.strip() if link_tit_p else ""
                        })
                    st.markdown("---")

                st.markdown("🌐 **Vídeo ou Link Externo Geral de Apoio (Opcional):**")
                col_l1, col_l2 = st.columns([2, 1])
                with col_l1:
                    link_url_in = st.text_input("URL do Link / Vídeo Geral:", value=str(item_edit.get("link_url") or ""))
                with col_l2:
                    link_titulo_in = st.text_input("Nome/Título do Link Geral:", value=str(item_edit.get("link_titulo") or ""))

                arquivos_globais_no = st.file_uploader("📎 Adicionar Novas Evidências Gerais:", accept_multiple_files=True, key="edit_files_global")

                col_btn_salvar_ed, col_btn_canc_ed = st.columns(2)
                with col_btn_salvar_ed:
                    if st.form_submit_button("💾 Salvar Alterações"):
                        if edit_titulo and passos_editados_lista:
                            json_conteudo = json.dumps(passos_editados_lista)
                            url_anexos_global = upload_multiplos_arquivos(arquivos_globais_no) if arquivos_globais_no else item_edit.get("anexo_url")
                            
                            dados_atualizados = {
                                "sistema_produto": edit_galho,
                                "hardware": edit_subgalho,
                                "titulo": edit_titulo.strip(),
                                "conteudo": json_conteudo,
                                "link_url": link_url_in.strip() if link_url_in else None,
                                "link_titulo": link_titulo_in.strip() if link_titulo_in else None,
                                "anexo_url": url_anexos_global
                            }
                            
                            if atualizar_manual_db(st.session_state.editando_manual_id, dados_atualizados, "tecnico@actuar.group"):
                                st.session_state.editando_manual_id = None
                                st.toast("Nó atualizado com sucesso!", icon="🎉")
                                st.rerun()
                        else:
                            st.error("Preencha o Título e ao menos o Passo 1.")
                with col_btn_canc_ed:
                    if st.form_submit_button("❌ Cancelar Edição"):
                        st.session_state.editando_manual_id = None
                        st.rerun()
            st.markdown("---")

    if df_manuais.empty:
        st.info("O mapa está vazio. Utilize a opção 'Adicionar Novo Nó / Galho' acima para estruturar o primeiro item.")
    else:
        df_m = df_manuais.copy()
        for col_n in ["sistema_produto", "hardware", "link_url", "link_titulo", "anexo_url"]:
            if col_n not in df_m.columns:
                df_m[col_n] = None

        for raiz in galhos_principais:
            df_raiz = df_m[df_m["sistema_produto"] == raiz]
            
            with st.expander(f"📂 **{raiz}** ({len(df_raiz)} itens vinculados)", expanded=(raiz == galho_selecionado_filtro)):
                if df_raiz.empty:
                    st.markdown(f"_Nenhum conteúdo cadastrado sob **{raiz}**._")
                else:
                    sub_galhos = df_raiz["hardware"].unique()
                    
                    for sg in sub_galhos:
                        df_sg = df_raiz[df_raiz["hardware"] == sg]
                        
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;╰─ 📂 **{sg}**")
                        
                        for _, row_item in df_sg.iterrows():
                            with st.container(border=True):
                                st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;╰─ 🔹 **{row_item.get('titulo')}**")
                                
                                renderizar_conteudo_estruturado(row_item.get('conteudo'), row_item.get('anexo_url'))
                                renderizar_bloco_links(row_item.get('link_url'), row_item.get('link_titulo'))
                                
                                col_b_edit, col_b_del, _ = st.columns([1, 1, 4])
                                with col_b_edit:
                                    if st.button(f"✏️ Editar #{row_item.get('id')}", key=f"edit_no_btn_{row_item.get('id')}"):
                                        st.session_state.editando_manual_id = int(row_item.get('id'))
                                        st.rerun()
                                with col_b_del:
                                    if st.button(f"🗑️ Excluir #{row_item.get('id')}", key=f"del_no_{row_item.get('id')}"):
                                        deletar_manual_db(row_item.get('id'), "tecnico@actuar.group")
                                        st.rerun()

    if modo_mapa == "➕ Adicionar Novo Nó / Galho":
        st.markdown("---")
        st.markdown(f"### ➕ Adicionar Conteúdo no Galho: **{galho_selecionado_filtro}**")
        
        with st.form("form_mapa_interativo", clear_on_submit=True):
            sub_galho_tipo = st.selectbox("Subpasta do Galho:", ["Manual de Instalação", "Erros e Soluções", "Outro Subtópico"], key="map_sub_g")
            
            titulo_no = st.text_input("Título do Tópico / Erro:", placeholder="Ex: Actuar Acesso / Configuração de IP...")
            
            st.markdown("---")
            st.markdown("🛠️ **Passos do Procedimento (Passo a Passo com Erros e Links):**")
            passos_mapa_lista = []
            for p_idx in range(1, 6):
                st.markdown(f"**Passo {p_idx}**")
                col_p_txt, col_p_file = st.columns([2, 1])
                with col_p_txt:
                    txt_p = st.text_area(f"Descrição do Passo {p_idx}:", key=f"map_p_txt_{p_idx}", height=70)
                with col_p_file:
                    files_p = st.file_uploader(f"Anexos Passo {p_idx}", accept_multiple_files=True, key=f"map_p_file_{p_idx}")

                col_l_passo, col_err_passo = st.columns(2)
                with col_l_passo:
                    link_url_p = st.text_input(f"Link do Passo {p_idx} (Opcional):", placeholder="https://...", key=f"map_p_link_{p_idx}")
                    link_tit_p = st.text_input(f"Título do Link {p_idx}:", placeholder="Ex: Vídeo do Passo", key=f"map_p_link_tit_{p_idx}")
                with col_err_passo:
                    txt_err_p = st.text_area(f"⚠️ Possíveis Erros / Falhas do Passo {p_idx}:", placeholder="Descreva o erro ou como resolver se falhar aqui...", key=f"map_p_err_{p_idx}", height=70)
                    files_err = st.file_uploader(f"📸 Imagens/Evidências do Erro (Passo {p_idx})", accept_multiple_files=True, key=f"map_p_err_file_{p_idx}")

                if txt_p.strip():
                    url_anexo_p = upload_multiplos_arquivos(files_p) if files_p else None
                    url_erro_anexo_p = upload_multiplos_arquivos(files_err) if files_err else None
                    
                    passos_mapa_lista.append({
                        "passo": p_idx,
                        "texto": txt_p.strip(),
                        "anexo": url_anexo_p,
                        "erro": txt_err_p.strip() if txt_err_p else "",
                        "erro_anexo": url_erro_anexo_p,
                        "link_url": link_url_p.strip() if link_url_p else "",
                        "link_titulo": link_tit_p.strip() if link_tit_p else ""
                    })
                st.markdown("---")

            st.markdown("🌐 **Vídeo ou Link Externo Geral de Apoio (Opcional):**")
            col_l1, col_l2 = st.columns([2, 1])
            with col_l1:
                link_url_in = st.text_input("URL do Link / Vídeo Geral:", placeholder="https://youtube.com/watch?v=... ou link da wiki")
            with col_l2:
                link_titulo_in = st.text_input("Nome/Título do Link Geral:", placeholder="Ex: Vídeo Explicativo YouTube")

            arquivos_globais_no = st.file_uploader("📎 Imagens / Evidências Gerais do Tópico (Opcional):", accept_multiple_files=True, key="map_files_global")
            
            if st.form_submit_button("💾 Inserir Nó no Mapa"):
                if titulo_no and passos_mapa_lista:
                    json_conteudo = json.dumps(passos_mapa_lista)
                    url_anexos_global = upload_multiplos_arquivos(arquivos_globais_no) if arquivos_globais_no else None
                    
                    dados_no = {
                        "sistema_produto": galho_selecionado_filtro,
                        "hardware": sub_galho_tipo,
                        "titulo": titulo_no.strip(),
                        "conteudo": json_conteudo,
                        "link_url": link_url_in.strip() if link_url_in else None,
                        "link_titulo": link_titulo_in.strip() if link_titulo_in else None,
                        "anexo_url": url_anexos_global
                    }
                    
                    if salvar_manual_db(dados_no, "tecnico@actuar.group"):
                        st.toast("Nó adicionado com sucesso ao mapa!", icon="🎉")
                        st.rerun()
                else:
                    st.error("Preencha o Título e pelo menos o Passo 1 do procedimento.")

# ==========================================
# ABA 4: MANUAIS & PRODUTOS
# ==========================================
indice_manuais = abas_navegacao.index("📚 Manuais & Produtos")
with tabs[indice_manuais]:
    st.subheader("📚 Base de Conhecimento de Produtos e Manuais Técnicos")

    with st.form("form_novo_manual", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            m_sistema = st.text_input("💻 Sistema / Módulo Afetado:", placeholder="Ex: Edge / Control ID")
            m_titulo = st.text_input("Título do Manual / Especificação:", placeholder="Ex: Manual do Modo Stream Control ID")
        with col_m2:
            m_hardware = st.selectbox("⚙️ Hardware Relacionado:", LISTA_HARDWARE, key="manual_hw")

        m_conteudo = st.text_area("📄 Conteúdo Completo e Instruções do Produto:", placeholder="Escreva aqui todas as instruções...", height=200)

        st.markdown("🌐 **Vídeo ou Link Externo de Apoio (Opcional):**")
        col_ml1, col_ml2 = st.columns([2, 1])
        with col_ml1:
            m_link_url = st.text_input("URL do Link / Vídeo:", placeholder="https://...", key="man_link_url")
        with col_ml2:
            m_link_titulo = st.text_input("Nome/Título do Link:", placeholder="Ex: Vídeo de Treinamento", key="man_link_tit")

        if st.form_submit_button("💾 Salvar Manual na Base de Conhecimento"):
            if m_titulo and m_conteudo:
                dados_manual = {
                    "sistema_produto": m_sistema.strip(),
                    "hardware": m_hardware,
                    "titulo": m_titulo,
                    "conteudo": m_conteudo,
                    "link_url": m_link_url.strip() if m_link_url else None,
                    "link_titulo": m_link_titulo.strip() if m_link_titulo else None,
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
                renderizar_conteudo_estruturado(row.get('conteudo'), row.get('anexo_url'))
                renderizar_bloco_links(row.get('link_url'), row.get('link_titulo'))
                
                if st.button(f"🗑️ Excluir Manual #{m_id}", key=f"del_manual_{m_id}"):
                    if deletar_manual_db(m_id, "tecnico@actuar.group"):
                        st.toast("Manual excluído!", icon="🗑️")
                        st.rerun()

# ==========================================
# ABA 5: MODO TV
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
# ABA 6: FAVORITOS
# ==========================================
indice_fav = abas_navegacao.index("⭐ Meus Favoritos")
with tabs[indice_fav]:
    st.subheader("⭐ Meus Chamados Frequentes & Favoritos")
    if st.session_state.favoritos and not df_ocorrencias.empty:
        df_fav = df_ocorrencias[df_ocorrencias["id"].isin(st.session_state.favoritos)]
        for _, row in df_fav.iterrows():
            ocor_id = int(row["id"])
            with st.expander(f"⭐ [FAVORITO #{ocor_id}] {row.get('problema')}"):
                renderizar_conteudo_estruturado(row.get("solucao"), row.get("anexo_url"))

# ==========================================
# ABA 7: CADASTRAR TRATATIVA
# ==========================================
indice_cad = abas_navegacao.index("➕ Cadastrar Tratativa")
with tabs[indice_cad]:
    st.subheader("➕ Novo Mapeamento Técnico")
    with st.form("form_novo", clear_on_submit=True):
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            in_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE, key="cad_hw")
            in_status = st.selectbox("📌 Status:", ["🟢 Solução Definitiva", "🟡 Contorno / Paliativo", "🔴 Bug / Em Análise"], key="cad_status")
        with col_c2:
            in_sist = st.text_input("💻 Sistema / Módulo (Livre):", placeholder="Ex: Legado(Acesso)")
            in_nivel = st.selectbox("📊 Nível:", ["N1 - Fácil / Rápido", "N2 - Intermediário", "N3 - Avançado / Laboratório"], key="cad_nivel")

        in_prob = st.text_input("Problema (Sintoma):")
        in_files_prob = st.file_uploader("📎 Arquivos do Problema:", accept_multiple_files=True, key="cad_prob_files")
        in_motivo = st.text_area("Motivo (Causa Raiz):")

        st.markdown("### 🛠️ Passos da Solução")
        passos_novos_lista = []
        for p_idx in range(1, 5):
            st.markdown(f"**Passo {p_idx}**")
            col_p_txt, col_p_file = st.columns([2, 1])
            with col_p_txt:
                txt_p = st.text_area(f"Descrição do Passo {p_idx}:", key=f"cad_p_txt_{p_idx}")
            with col_p_file:
                files_p = st.file_uploader(f"Anexos Passo {p_idx}", accept_multiple_files=True, key=f"cad_p_file_{p_idx}")

            col_l_passo, col_err_passo = st.columns(2)
            with col_l_passo:
                link_url_p = st.text_input(f"Link do Passo {p_idx} (Opcional):", placeholder="https://...", key=f"cad_p_link_{p_idx}")
                link_tit_p = st.text_input(f"Título do Link {p_idx}:", placeholder="Ex: Vídeo do Passo", key=f"cad_p_link_tit_{p_idx}")
            with col_err_passo:
                txt_err_p = st.text_area(f"⚠️ Possíveis Erros / Falhas do Passo {p_idx}:", placeholder="Descreva o erro ou solução se falhar aqui...", key=f"cad_p_err_{p_idx}", height=70)
                files_err = st.file_uploader(f"📸 Imagens/Evidências do Erro (Passo {p_idx})", accept_multiple_files=True, key=f"cad_p_err_file_{p_idx}")

            if txt_p.strip():
                url_anexo_p = upload_multiplos_arquivos(files_p) if files_p else None
                url_erro_anexo_p = upload_multiplos_arquivos(files_err) if files_err else None

                passos_novos_lista.append({
                    "passo": p_idx,
                    "texto": txt_p.strip(),
                    "anexo": url_anexo_p,
                    "erro": txt_err_p.strip() if txt_err_p else "",
                    "erro_anexo": url_erro_anexo_p,
                    "link_url": link_url_p.strip() if link_url_p else "",
                    "link_titulo": link_titulo_p.strip() if link_titulo_p else ""
                })
            st.markdown("---")

        if st.form_submit_button("💾 Salvar Mapeamento no Banco"):
            if in_sist and in_prob and in_motivo and passos_novos_lista:
                json_solucao = json.dumps(passos_novos_lista)
                url_anexo_prob = upload_multiplos_arquivos(in_files_prob) if in_files_prob else None

                dados = {
                    "sistema": in_sist.strip(),
                    "equipamento": in_hw,
                    "problema": in_prob,
                    "motivo": in_motivo,
                    "solucao": json_solucao,
                    "status": in_status,
                    "nivel": in_nivel,
                    "anexo_url": url_anexo_prob,
                }
                if salvar_manual_db(dados, "tecnico@actuar.group"):
                    st.toast("Tratativa salva com sucesso!", icon="🎉")
                    st.rerun()
            else:
                st.error("Preencha o sistema, problema, motivo e ao menos 1 passo da solução.")

# ==========================================
# ABA 8: IMPORTAR & EXPORTAR TXT
# ==========================================
indice_export = abas_navegacao.index("📥 Importar & Exportar (TXT)")
with tabs[indice_export]:
    st.subheader("📥 Importar & Exportar Base Completa em .TXT")

    conteudo_txt = "=" * 70 + "\nACTUAR.GROUP - EXPORTAÇÃO DA BASE DE CONHECIMENTO\n" + "=" * 70 + "\n\n"

    if not df_manuais.empty:
        conteudo_txt += "--- SEÇÃO 1: MAPA HIERÁRQUICO DE ONBOARDING ---\n"
        for _, row in df_manuais.iterrows():
            conteudo_txt += f"Galho: {row.get('sistema_produto')} | Subpasta: {row.get('hardware')} | Título: {row.get('titulo')}\nConteúdo: {row.get('conteudo')}\n"
            if row.get('link_url'):
                conteudo_txt += f"Link ({row.get('link_titulo')}): {row.get('link_url')}\n"
            conteudo_txt += "-" * 50 + "\n"

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
# ABA 9: AUDIT LOG
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