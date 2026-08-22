# -*- coding: utf-8 -*-
import json
import os
import re
import time
import pandas as pd
import streamlit as st
from supabase import Client, create_client

# ==========================================
# 1. CONFIGURAÇÃO E DESIGN SYSTEM (MODERNO DARK DEFINITIVO)
# ==========================================
st.set_page_config(
    page_title="actuar.group - Engineering Hub",
    page_icon="favicon.png",
    layout="wide",
)

st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

# ==========================================
# 2. CONEXÃO E BANCO DE DADOS
# ==========================================
default_url = st.secrets.get("SUPABASE_URL", "")
default_key = st.secrets.get("SUPABASE_KEY", "")

if "override_url" not in st.session_state:
  st.session_state.override_url = default_url
if "override_key" not in st.session_state:
  st.session_state.override_key = default_key


@st.cache_resource
def init_supabase(url: str, key: str) -> Client:
  return create_client(url, key)


try:
  supabase = init_supabase(
      st.session_state.override_url, st.session_state.override_key
  )
except Exception as e:
  supabase = None


def buscar_ocorrencias_db():
  if not supabase:
    return pd.DataFrame()
  res = (
      supabase.table("ocorrencias").select("*").order("id", desc=True).execute()
  )
  return pd.DataFrame(res.data)


def buscar_manuais_db():
  if not supabase:
    return pd.DataFrame()
  try:
    res = (
        supabase.table("manuais_produto")
        .select("*")
        .order("id", desc=True)
        .execute()
    )
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
    registrar_log(
        usuario_email,
        "CRIOU",
        f"Cadastrou a ocorrência: {dados.get('problema')}",
    )
    return True
  except Exception as e:
    st.error(f"Erro ao salvar no Supabase: {e}")
    return False


def salvar_manual_db(dados, usuario_email):
  try:
    dados_limpos = limpar_dados_para_json(dados)
    supabase.table("manuais_produto").insert(dados_limpos).execute()
    registrar_log(
        usuario_email,
        "MANUAL_CRIADO",
        f"Cadastrou manual técnico: {dados.get('titulo')}",
    )
    return True
  except Exception as e:
    st.error(
        f"Erro ao salvar manual (Verifique se a tabela 'manuais_produto' foi"
        f" criada no Supabase): {e}"
    )
    return False


def deletar_manual_db(manual_id, usuario_email):
  try:
    supabase.table("manuais_produto").delete().eq("id", manual_id).execute()
    registrar_log(
        usuario_email, "MANUAL_EXCLUIDO", f"Excluiu o manual ID #{manual_id}"
    )
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
        motivo_final = (
            " | ".join(motivo_partes) if motivo_partes else "Não informado"
        )
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
      registrar_log(
          usuario_email,
          "IMPORTOU",
          f"Importou {importadas} ocorrências via arquivo TXT.",
      )
    return importadas
  except Exception as e:
    st.error(f"Erro ao processar importação do arquivo TXT: {e}")
    return 0


def atualizar_ocorrencia_db(ocorrencia_id, dados_atualizados, usuario_email):
  try:
    dados_atualizados.pop("origem", None)
    dados_limpos = limpar_dados_para_json(dados_atualizados)
    supabase.table("ocorrencias").update(dados_limpos).eq(
        "id", ocorrencia_id
    ).execute()
    registrar_log(
        usuario_email, "EDITOU", f"Editou a ocorrência ID #{ocorrencia_id}"
    )
    return True
  except Exception as e:
    st.error(f"Erro ao atualizar registro: {e}")
    return False


def deletar_ocorrencia_db(ocorrencia_id, usuario_email):
  try:
    supabase.table("comentarios").delete().eq(
        "ocorrencia_id", ocorrencia_id
    ).execute()
    res = supabase.table("ocorrencias").delete().eq("id", ocorrencia_id).execute()

    if res.data and len(res.data) > 0:
      registrar_log(
          usuario_email, "EXCLUIU", f"Excluiu a ocorrência ID #{ocorrencia_id}"
      )
      return True
    else:
      st.error(
          "O banco bloqueou a exclusão. Verifique se o RLS está liberado no"
          " Supabase."
      )
      return False
  except Exception as e:
    st.error(f"Erro ao excluir no Supabase: {e}")
    return False


def gerenciar_voto(ocorrencia_id, tipo_voto, usuario_email):
  try:
    res_comentarios = (
        supabase.table("comentarios")
        .select("*")
        .eq("ocorrencia_id", ocorrencia_id)
        .eq("usuario", usuario_email)
        .execute()
    )
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

    res_ocor = (
        supabase.table("ocorrencias")
        .select("votos_pos, votos_neg")
        .eq("id", ocorrencia_id)
        .execute()
    )
    if not res_ocor.data:
      return
    v_pos = res_ocor.data[0].get("votos_pos", 0) or 0
    v_neg = res_ocor.data[0].get("votos_neg", 0) or 0

    if voto_anterior is None:
      supabase.table("comentarios").insert({
          "ocorrencia_id": ocorrencia_id,
          "usuario": usuario_email,
          "comentario": f"[VOTO_{tipo_voto.upper()}]",
      }).execute()
      if tipo_voto == "pos":
        v_pos += 1
      else:
        v_neg += 1
    elif voto_anterior == tipo_voto:
      if comentario_voto_id:
        supabase.table("comentarios").delete().eq(
            "id", comentario_voto_id
        ).execute()
      if tipo_voto == "pos":
        v_pos = max(0, v_pos - 1)
      else:
        v_neg = max(0, v_neg - 1)
    else:
      if comentario_voto_id:
        supabase.table("comentarios").delete().eq(
            "id", comentario_voto_id
        ).execute()
      supabase.table("comentarios").insert({
          "ocorrencia_id": ocorrencia_id,
          "usuario": usuario_email,
          "comentario": f"[VOTO_{tipo_voto.upper()}]",
      }).execute()
      if tipo_voto == "pos":
        v_pos += 1
        v_neg = max(0, v_neg - 1)
      else:
        v_neg += 1
        v_pos = max(0, v_pos - 1)

    supabase.table("ocorrencias").update(
        {"votos_pos": v_pos, "votos_neg": v_neg}
    ).eq("id", ocorrencia_id).execute()
  except Exception as e:
    st.error(f"Erro ao gerenciar voto: {e}")


def buscar_comentarios(ocorrencia_id):
  res = (
      supabase.table("comentarios")
      .select("*")
      .eq("ocorrencia_id", ocorrencia_id)
      .order("id", desc=True)
      .execute()
  )
  return res.data


def salvar_comentario(ocorrencia_id, usuario, texto):
  supabase.table("comentarios").insert({
      "ocorrencia_id": ocorrencia_id,
      "usuario": usuario,
      "comentario": texto,
  }).execute()


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
      u = (
          url_res.get("publicUrl")
          or url_res.get("public_url")
          or str(url_res)
      )
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
# ALGORITMO DE BUSCA INTELIGENTE DO COPILOT (OCORRÊNCIAS + MANUAIS)
# ==========================================
def buscar_melhor_solucao_copilot(query, df_ocorrencias, df_manuais):
  if not query:
    return [], []

  query_lower = query.lower().strip()
  stopwords = {
      "a",
      "o",
      "de",
      "do",
      "da",
      "em",
      "um",
      "uma",
      "para",
      "com",
      "que",
      "os",
      "as",
      "dos",
      "das",
      "por",
      "mais",
      "como",
      "mas",
      "foi",
      "ao",
      "ele",
      "seu",
      "sua",
      "ou",
      "quando",
      "muito",
      "nos",
      "já",
      "só",
      "pelo",
      "pela",
      "até",
      "isso",
      "ela",
      "entre",
      "depois",
      "sem",
      "mesmo",
      "aos",
      "também",
  }

  palavras_query = [
      p.lower()
      for p in re.findall(r"\w+", query_lower)
      if p.lower() not in stopwords and len(p) > 1
  ]

  if not palavras_query:
    palavras_query = re.findall(r"\w+", query_lower)

  # 1. Buscar nas Ocorrências
  resultados_ocorrencias = []
  if not df_ocorrencias.empty:
    for _, row in df_ocorrencias.iterrows():
      texto_base = (
          f"{row.get('problema', '')} {row.get('motivo', '')}"
          f" {row.get('equipamento', '')} {row.get('sistema', '')}"
          f" {row.get('solucao', '')}"
      ).lower()
      score = 0
      if query_lower in texto_base:
        score += 15
      for p in palavras_query:
        if p in texto_base:
          if p in str(row.get("problema", "")).lower():
            score += 5
          elif p in str(row.get("motivo", "")).lower():
            score += 3
          else:
            score += 1
      if score > 0:
        resultados_ocorrencias.append((score, row))
    resultados_ocorrencias.sort(key=lambda x: x[0], reverse=True)

  # 2. Buscar nos Manuais de Produtos e Regras de Negócio
  resultados_manuais = []
  if not df_manuais.empty:
    for _, row in df_manuais.iterrows():
      texto_manual = (
          f"{row.get('titulo', '')} {row.get('sistema_produto', '')}"
          f" {row.get('conteudo', '')}"
      ).lower()
      score = 0
      if query_lower in texto_manual:
        score += 20
      for p in palavras_query:
        if p in texto_manual:
          if p in str(row.get("titulo", "")).lower():
            score += 6
          else:
            score += 2
      if score > 0:
        resultados_manuais.append((score, row))
    resultados_manuais.sort(key=lambda x: x[0], reverse=True)

  match_ocor = [r[1] for r in resultados_ocorrencias[:3]]
  match_man = [r[1] for r in resultados_manuais[:3]]

  return match_ocor, match_man


# ==========================================
# 3. CONTROLE DE SESSÃO E SIDEBAR LIMPA
# ==========================================
if "favoritos" not in st.session_state:
  st.session_state.favoritos = []

with st.sidebar:
  if os.path.exists("logo_dark.png"):
    st.image("logo_dark.png", width=70)
  elif os.path.exists("logo.png"):
    st.image("logo.png", width=70)
  st.markdown("---")

# ==========================================
# 4. CABEÇALHO E ESTRUTURA DE ABAS
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

col_header_left, col_header_right = st.columns([6, 4])

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

with col_header_right:
  st.markdown("")

st.markdown("---")

try:
  df_ocorrencias = buscar_ocorrencias_db()
except Exception:
  df_ocorrencias = pd.DataFrame()

try:
  df_manuais = buscar_manuais_db()
except Exception:
  df_manuais = pd.DataFrame()

for col in [
    "sistema",
    "equipamento",
    "problema",
    "motivo",
    "solucao",
    "status",
    "nivel",
    "votos_pos",
    "votos_neg",
    "anexo_url",
]:
  if not df_ocorrencias.empty and col not in df_ocorrencias.columns:
    df_ocorrencias[col] = None

# CRIAÇÃO DAS ABAS
abas_navegacao = [
    "📋 Diagnósticos",
    "⚡ Guia Interativo",
    "🤖 Copilot IA",
    "📚 Manuais & Produtos",
    "📺 Modo TV",
    "⭐ Meus Favoritos",
    "➕ Cadastrar Tratativa",
    "📥 Importar & Exportar (TXT)",
    "📜 Audit Log (Gestão)",
]

tabs = st.tabs(abas_navegacao)


def renderizar_solucao_estruturada(solucao_data, anexo_global=None):
  if (
      anexo_global
      and pd.notna(anexo_global)
      and str(anexo_global).strip() != ""
  ):
    urls_problema = [
        u.strip() for u in str(anexo_global).split(",") if u.strip()
    ]
    urls_problema = list(dict.fromkeys(urls_problema))

    if urls_problema:
      with st.expander(
          f"📎 Ver Evidências do Problema (Sintoma) — {len(urls_problema)}"
          " arquivo(s)",
          expanded=False,
      ):
        for idx_prob, url_file in enumerate(urls_problema):
          nome_arquivo = url_file.split("/")[-1].split("?")[0]
          if "_" in nome_arquivo:
            partes_nome = nome_arquivo.split("_", 2)
            nome_exibicao = (
                partes_nome[-1] if len(partes_nome) > 2 else nome_arquivo
            )
          else:
            nome_exibicao = nome_arquivo

          extensoes_imagem = (".png", ".jpg", ".jpeg", ".gif", ".webp")
          if url_file.lower().endswith(extensoes_imagem):
            try:
              st.image(
                  url_file,
                  width=450,
                  caption=f"Imagem {idx_prob + 1}: {nome_exibicao}",
              )
            except Exception:
              st.markdown(
                  f"📥 Baixar Arquivo {idx_prob + 1}:"
                  f" [**{nome_exibicao}**]({url_file})"
              )
          else:
            st.markdown(
                f"📄 Arquivo {idx_prob + 1}: [**{nome_exibicao}**]({url_file})"
            )
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

        if urls_passo:
          with st.expander(
              f"📷 Ver Anexos do Passo {num_passo} — {len(urls_passo)}"
              " arquivo(s)",
              expanded=False,
          ):
            for idx_f, url_file in enumerate(urls_passo):
              nome_arquivo = url_file.split("/")[-1].split("?")[0]
              if "_" in nome_arquivo:
                partes_nome = nome_arquivo.split("_", 2)
                nome_exibicao = (
                    partes_nome[-1] if len(partes_nome) > 2 else nome_arquivo
                )
              else:
                nome_exibicao = nome_arquivo

              extensoes_imagem = (".png", ".jpg", ".jpeg", ".gif", ".webp")
              if url_file.lower().endswith(extensoes_imagem):
                try:
                  st.image(
                      url_file,
                      width=450,
                      caption=(
                          f"Evidência {idx_f + 1} - Passo"
                          f" {num_passo}: {nome_exibicao}"
                      ),
                  )
                except Exception:
                  st.markdown(
                      f"📥 Baixar Arquivo {idx_f + 1}:"
                      f" [**{nome_exibicao}**]({url_file})"
                  )
              else:
                st.markdown(
                    f"📄 Arquivo {idx_f + 1}:"
                    f" [**{nome_exibicao}**]({url_file})"
                )
      st.markdown("")
  else:
    st.success(f"**Solução Recomendada:**\n{solucao_data}")


# ==========================================
# ABA 1: CONSULTA COM TABELA INTERATIVA
# ==========================================
indice_diag = abas_navegacao.index("📋 Diagnósticos")
with tabs[indice_diag]:
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
    f_busca = st.text_input(
        "🔍 Buscar termo ou palavra-chave:",
        "",
        key="f_busca_tab0",
        placeholder="Ex: DLL, facial, timeout, IP...",
    )

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
            df_filtered["problema"]
            .astype(str)
            .str.contains(regex_pattern, case=False, na=False, regex=True)
            | df_filtered["motivo"]
            .astype(str)
            .str.contains(regex_pattern, case=False, na=False, regex=True)
            | df_filtered["solucao"]
            .astype(str)
            .str.contains(regex_pattern, case=False, na=False, regex=True)
        ]

  st.session_state.df_filtered = df_filtered

  if df_filtered.empty:
    st.info("Nenhuma ocorrência encontrada com os filtros selecionados.")
  else:
    st.markdown(f"### 📊 Resultados Filtrados ({len(df_filtered)} registros)")
    st.caption(
        "💡 **Como usar:** Digite acima para refinar a busca e **clique"
        " diretamente na linha** da tabela abaixo para carregar os detalhes"
        " completos."
    )

    df_display = (
        df_filtered[["sistema", "equipamento", "problema", "status", "nivel"]]
        .copy()
        .reset_index(drop=True)
    )

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
    elif hasattr(evento_tabela, "selection") and hasattr(
        evento_tabela.selection, "rows"
    ):
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
      texto_botao_fav = (
          "⭐ Remover dos Favoritos" if is_fav else "☆ Favoritar Chamado"
      )

      st.markdown("---")
      with st.container(border=True):
        col_det_title, col_det_fav = st.columns([4, 1])
        with col_det_title:
          st.markdown(f"### 🚨 [ID #{ocor_id}] {prob}")
        with col_det_fav:
          if st.button(texto_botao_fav, key=f"fav_btn_{ocor_id}"):
            if is_fav:
              st.session_state.favoritos = [
                  i for i in st.session_state.favoritos if i != ocor_id
              ]
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
        v_pos = row.get("votos_pos", 0) or 0
        v_neg = row.get("votos_neg", 0) or 0

        comentarios = buscar_comentarios(ocor_id)
        user_email_atual = "tecnico@actuar.group"

        user_voto = None
        for c in comentarios:
          if c["usuario"].lower() == user_email_atual.lower():
            if c["comentario"] == "[VOTO_POS]":
              user_voto = "pos"
              break
            elif c["comentario"] == "[VOTO_NEG]":
              user_voto = "neg"
              break

        texto_pos = f"👍 Funcionou ({v_pos})" + (
            " ✅" if user_voto == "pos" else ""
        )
        texto_neg = f"👎 Não funcionou ({v_neg})" + (
            " ✅" if user_voto == "neg" else ""
        )

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
        comentarios_reais = [
            c for c in comentarios if not c["comentario"].startswith("[VOTO_")
        ]
        for c in comentarios_reais:
          st.caption(f"**{c['usuario']}**: {c['comentario']}")

        with st.form(key=f"form_coment_{ocor_id}"):
          novo_coment = st.text_input(
              "Adicionar dica de campo:",
              placeholder="Ex: Funciona apenas em modo Admin",
          )
          if st.form_submit_button("Enviar Comentário"):
            if novo_coment:
              salvar_comentario(ocor_id, user_email_atual, novo_coment)
              st.toast("Anotação adicionada!", icon="💬")
              st.rerun()

        st.markdown("---")
        with st.expander(f"✏️ Editar Relato Finalizado #{ocor_id}"):
          with st.form(key=f"form_edit_{ocor_id}"):
            edit_col1, edit_col2 = st.columns(2)

            idx_sist = LISTA_SISTEMA.index(sist) if sist in LISTA_SISTEMA else 0
            idx_hw = LISTA_HARDWARE.index(hw) if hw in LISTA_HARDWARE else 0

            lista_status = [
                "🟢 Solução Definitiva",
                "🟡 Contorno / Paliativo",
                "🔴 Bug / Em Análise",
            ]
            idx_status = (
                lista_status.index(status) if status in lista_status else 0
            )

            lista_niveis = [
                "N1 - Fácil / Rápido",
                "N2 - Intermediário",
                "N3 - Avançado / Laboratório",
            ]
            idx_nivel = [
                i for i, n in enumerate(lista_niveis) if n.startswith(str(nivel)[:2])
            ]
            idx_nivel = idx_nivel[0] if idx_nivel else 0

            with edit_col1:
              edit_hw = st.selectbox(
                  "⚙️ Catraca / Hardware:",
                  LISTA_HARDWARE,
                  index=idx_hw,
                  key=f"eh_{ocor_id}",
              )
              edit_status = st.selectbox(
                  "📌 Status:",
                  lista_status,
                  index=idx_status,
                  key=f"est_{ocor_id}",
              )
            with edit_col2:
              edit_sist = st.selectbox(
                  "💻 Sistema:",
                  LISTA_SISTEMA,
                  index=idx_sist,
                  key=f"es_{ocor_id}",
              )
              edit_nivel = st.selectbox(
                  "📊 Nível:",
                  lista_niveis,
                  index=idx_nivel,
                  key=f"en_{ocor_id}",
              )

            edit_prob = st.text_input(
                "Problema (Sintoma):", value=prob, key=f"ep_{ocor_id}"
            )

            st.markdown(
                "📎 **Editar / Adicionar Arquivos do Problema (Sintoma):**"
            )
            urls_prob_existentes = (
                [u.strip() for u in str(anexo).split(",") if u.strip()]
                if anexo and pd.notna(anexo)
                else []
            )
            urls_prob_existentes = list(dict.fromkeys(urls_prob_existentes))

            urls_prob_para_manter = []
            if urls_prob_existentes:
              for idx_pi, url_pi in enumerate(urls_prob_existentes):
                nome_arq_pi = url_pi.split("/")[-1].split("?")[0]
                cp1, cp2 = st.columns([3, 1])
                with cp1:
                  if url_pi.lower().endswith(
                      (".png", ".jpg", ".jpeg", ".gif", ".webp")
                  ):
                    try:
                      st.image(url_pi, width=150)
                    except Exception:
                      st.markdown(f"📄 {nome_arq_pi}")
                  else:
                    st.markdown(f"📄 {nome_arq_pi}")
                with cp2:
                  if st.checkbox(
                      "Manter",
                      value=True,
                      key=f"manter_prob_{ocor_id}_{idx_pi}",
                  ):
                    urls_prob_para_manter.append(url_pi)

            edit_files_prob = st.file_uploader(
                "Adicionar novos arquivos ao Problema:",
                type=[
                    "png",
                    "jpg",
                    "jpeg",
                    "pdf",
                    "txt",
                    "docx",
                    "xlsx",
                    "csv",
                    "zip",
                ],
                accept_multiple_files=True,
                key=f"edit_prob_files_{ocor_id}",
            )

            edit_motivo = st.text_area(
                "Motivo (Causa Raiz):",
                value=row.get("motivo", ""),
                key=f"em_{ocor_id}",
            )

            st.markdown("### 🛠️ Editar Passos da Solução")

            passos_atuais = []
            try:
              if solucao_val and str(solucao_val).strip().startswith("["):
                passos_atuais = json.loads(str(solucao_val))
            except Exception:
              pass

            if not passos_atuais:
              passos_atuais = [{
                  "passo": 1,
                  "texto": str(solucao_val),
                  "anexo": None,
              }]

            edit_passos_dados = []
            for p_num in range(1, 4):
              p_obj = next(
                  (x for x in passos_atuais if x.get("passo") == p_num),
                  {"texto": "", "anexo": None},
              )
              st.markdown(f"**Passo {p_num}**")
              e_txt = st.text_area(
                  f"Texto do Passo {p_num}:",
                  value=p_obj.get("texto", ""),
                  key=f"edit_p_txt_{ocor_id}_{p_num}",
              )

              anexo_atual_passo = p_obj.get("anexo")
              urls_existentes = (
                  [
                      u.strip()
                      for u in str(anexo_atual_passo).split(",")
                      if u.strip()
                  ]
                  if anexo_atual_passo and pd.notna(anexo_atual_passo)
                  else []
              )
              urls_existentes = list(dict.fromkeys(urls_existentes))

              urls_para_manter = []
              if urls_existentes:
                st.markdown("📷 *Imagens atuais (desmarque para excluir):*")
                for idx_img, url_img in enumerate(urls_existentes):
                  nome_arq = url_img.split("/")[-1].split("?")[0]
                  col_prev, col_chk = st.columns([3, 1])
                  with col_prev:
                    if url_img.lower().endswith(
                        (".png", ".jpg", ".jpeg", ".gif", ".webp")
                    ):
                      try:
                        st.image(url_img, width=150)
                      except Exception:
                        st.markdown(f"📄 {nome_arq}")
                    else:
                      st.markdown(f"📄 {nome_arq}")
                  with col_chk:
                    if st.checkbox(
                        "Manter",
                        value=True,
                        key=f"manter_{ocor_id}_{p_num}_{idx_img}",
                    ):
                      urls_para_manter.append(url_img)

              e_files = st.file_uploader(
                  f"Adicionar novas fotos ao Passo {p_num}:",
                  type=[
                      "png",
                      "jpg",
                      "jpeg",
                      "pdf",
                      "txt",
                      "docx",
                      "xlsx",
                      "csv",
                      "zip",
                  ],
                  accept_multiple_files=True,
                  key=f"edit_p_file_{ocor_id}_{p_num}",
              )

              if e_txt.strip() or urls_para_manter or e_files:
                novas_urls = (
                    upload_multiplos_arquivos(e_files) if e_files else None
                )
                lista_final_urls = list(urls_para_manter)
                if novas_urls:
                  lista_final_urls.extend([
                      u.strip() for u in novas_urls.split(",") if u.strip()
                  ])
                lista_final_urls = list(dict.fromkeys(lista_final_urls))
                url_final_passo = (
                    ",".join(lista_final_urls) if lista_final_urls else None
                )

                edit_passos_dados.append({
                    "passo": p_num,
                    "texto": e_txt.strip(),
                    "anexo": url_final_passo,
                })

            if st.form_submit_button("💾 Salvar Alterações"):
              json_solucao_final = (
                  json.dumps(edit_passos_dados) if edit_passos_dados else ""
              )

              novas_urls_prob = (
                  upload_multiplos_arquivos(edit_files_prob)
                  if edit_files_prob
                  else None
              )
              lista_final_prob = list(urls_prob_para_manter)
              if novas_urls_prob:
                lista_final_prob.extend([
                    u.strip() for u in novas_urls_prob.split(",") if u.strip()
                ])
              lista_final_prob = list(dict.fromkeys(lista_final_prob))
              anexo_url_final = (
                  ",".join(lista_final_prob) if lista_final_prob else None
              )

              dados_novos = {
                  "sistema": edit_sist,
                  "equipamento": edit_hw,
                  "problema": edit_prob,
                  "motivo": edit_motivo,
                  "solucao": json_solucao_final,
                  "status": edit_status,
                  "nivel": edit_nivel,
                  "anexo_url": anexo_url_final,
              }

              if atualizar_ocorrencia_db(
                  ocor_id, dados_novos, "tecnico@actuar.group"
              ):
                st.toast(
                    f"Tratativa #{ocor_id} atualizada com sucesso!", icon="✅"
                )
                st.rerun()

        if st.button(
            f"🗑️ Excluir Tratativa #{ocor_id}", key=f"btn_del_{ocor_id}"
        ):
          sucesso = deletar_ocorrencia_db(ocor_id, "tecnico@actuar.group")
          if sucesso:
            st.toast(f"Tratativa #{ocor_id} excluída com sucesso!", icon="🗑️")
            st.rerun()

# ==========================================
# ABA: GUIA DE DIAGNÓSTICO INTERATIVO (SOLUÇÃO DIRETA & PEÇA INDICADA)
# ==========================================
indice_fluxo = abas_navegacao.index("⚡ Guia Interativo")
with tabs[indice_fluxo]:
  st.subheader("⚡ Guia Interativo — Solução Direta & Substituição de Peças")
  st.markdown(
      "Descreva o problema ou sintoma. O assistente analisa a base de dados nos"
      " bastidores e retorna **apenas a solução exata** e o **componente/peça**"
      " que deve ser substituído (se aplicável), sem exibir listas ou despejos."
  )

  col_g1, col_g2 = st.columns([1, 2])
  with col_g1:
    sist_guia_opt = ["Todos os Sistemas"] + LISTA_SISTEMA
    filtro_sist_guia = st.selectbox(
        "Filtrar por Sistema (Opcional):", sist_guia_opt, key="guia_filtro_sist"
    )
  with col_g2:
    texto_guia_input = st.text_input(
        "Descreva o comportamento, sintoma ou dúvida:",
        placeholder="Ex: braço travado, erro de DLL, falha de comunicação, leitor...",
        key="guia_input_descricao_livre",
    )

  if texto_guia_input:
    df_manuais_local = df_manuais.copy()
    if (
        filtro_sist_guia != "Todos os Sistemas"
        and not df_manuais_local.empty
        and "sistema_produto" in df_manuais_local.columns
    ):
      df_manuais_local = df_manuais_local[
          df_manuais_local["sistema_produto"] == filtro_sist_guia
      ]

    df_ocor_local = df_ocorrencias.copy()
    if (
        filtro_sist_guia != "Todos os Sistemas"
        and not df_ocor_local.empty
        and "sistema" in df_ocor_local.columns
    ):
      df_ocor_local = df_ocor_local[df_ocor_local["sistema"] == filtro_sist_guia]

    match_ocor, match_man = buscar_melhor_solucao_copilot(
        texto_guia_input, df_ocor_local, df_manuais_local
    )

    st.markdown("---")

    if match_ocor or match_man:
      melhor_ocor = match_ocor[0] if match_ocor else None
      melhor_man = match_man[0] if match_man else None

      with st.container(border=True):
        st.markdown("### 🎯 Solução e Ação Recomendada")

        if melhor_ocor:
          prob_encontrado = melhor_ocor.get("problema", "N/A")
          hw_encontrado = melhor_ocor.get("equipamento", "Indiferente")
          motivo_encontrado = melhor_ocor.get("motivo", "Não especificado")
          solucao_val = melhor_ocor.get("solucao", "")

          st.markdown(f"**Problema Identificado:** {prob_encontrado}")
          st.markdown(f"**Hardware Envolvido:** {hw_encontrado}")
          st.markdown(f"**Causa Raiz:** {motivo_encontrado}")

          # Identificação inteligente de peça para troca
          texto_analise_peca = f"{motivo_encontrado} {solucao_val}".lower()
          pecas_comuns = [
              "placa",
              "fonte",
              "cabo",
              "sensor",
              "leitor",
              "motor",
              "correia",
              "bobina",
              "display",
              "teclado",
              "biometria",
              "módulo",
              "conector",
          ]
          peca_sugerida = (
              "Nenhuma substituição de peça física necessária (ajuste de"
              " software / rede)."
          )
          for p in pecas_comuns:
            if p in texto_analise_peca:
              peca_sugerida = (
                  f"Substituir / Verificar componente: **{p.upper()}**"
              )
              break

          st.error(f"🔧 **Peça / Componente Indicado:** {peca_sugerida}")
          st.markdown("---")
          renderizar_solucao_estruturada(solucao_val, melhor_ocor.get("anexo_url"))

        elif melhor_man:
          st.markdown(
              f"**Referência Técnica:** {melhor_man.get('titulo')}"
          )
          st.info(melhor_man.get("conteudo"))
    else:
      st.warning(
          "⚠️ Nenhuma correspondência direta encontrada na base para este"
          " sintoma."
      )
  else:
    st.info(
        "💡 Digite a descrição do problema acima para obter imediatamente a"
        " solução direta e a peça a ser trocada."
    )

# ==========================================
# ABA 2: COPILOT IA (ASSISTENTE INTELIGENTE COM MANUAIS)
# ==========================================
indice_copilot = abas_navegacao.index("🤖 Copilot IA")
with tabs[indice_copilot]:
  st.subheader("🤖 Assistente Inteligente de Diagnóstico (Copilot)")
  st.markdown(
      "Descreva o problema ou sintoma em **linguagem natural** (ex: *Como"
      " configuro a porta TCP no sistema Legado ou no Edge?*). O Copilot"
      " consultará tanto a **Documentação Oficial dos Produtos** quanto os"
      " **Chamados Passados**."
  )

  if "copilot_messages" not in st.session_state:
    st.session_state.copilot_messages = [{
        "role": "assistant",
        "content": (
            "Olá! Sou o Copilot técnico da actuar.group. Já estou integrado à"
            " base de manuais e ocorrências. Qual é a dúvida ou problema do"
            " produto hoje?"
        ),
    }]

  user_query = st.chat_input(
      "Ex: Erro de DLL na biometria facial do The New..."
  )

  if user_query:
    st.session_state.copilot_messages = [
        {
            "role": "assistant",
            "content": (
                "Olá! Sou o Copilot técnico da actuar.group. Já estou integrado à"
                " base de manuais e ocorrências. Qual é a dúvida ou problema do"
                " produto hoje?"
            ),
        },
        {"role": "user", "content": user_query},
    ]

    match_ocor, match_man = buscar_melhor_solucao_copilot(
        user_query, df_ocorrencias, df_manuais
    )

    if match_ocor or match_man:
      resposta_texto = f"Encontrei **{len(match_man)}** manual(is) de produto e **{len(match_ocor)}** tratativa(s) relevante(s) na base:"
      st.session_state.copilot_messages.append({
          "role": "assistant",
          "content": resposta_texto,
          "match_ocor": match_ocor,
          "match_man": match_man,
      })
    else:
      resposta_texto = (
          "Não encontrei informações nos manuais nem em chamados passados sobre"
          " este termo exato. Recomendo cadastrar os detalhes na aba **📚 Manuais"
          " & Produtos** para que eu passe a conhecer este aspecto do produto."
      )
      st.session_state.copilot_messages.append({
          "role": "assistant",
          "content": resposta_texto,
          "match_ocor": [],
          "match_man": [],
      })

  for msg in st.session_state.copilot_messages:
    with st.chat_message(msg["role"]):
      st.markdown(msg["content"])

      if "match_man" in msg and msg["match_man"]:
        st.markdown("#### 📚 Manuais e Documentações Oficiais Encontradas:")
        for m in msg["match_man"]:
          with st.expander(
              f"📖 [Manual] {m.get('titulo')} ({m.get('sistema_produto')})"
          ):
            st.markdown(f"**Conteúdo / Regras do Produto:**")
            st.info(m.get("conteudo"))

      if "match_ocor" in msg and msg["match_ocor"]:
        st.markdown("#### 🚨 Ocorrências / Chamados Compatíveis:")
        for m in msg["match_ocor"]:
          with st.expander(
              f"📌 [ID #{m['id']}] — {m['problema']} ({m['sistema']} /"
              f" {m['equipamento']})"
          ):
            st.markdown(f"**Motivo / Causa Raiz:** {m['motivo']}")
            renderizar_solucao_estruturada(m["solucao"], m["anexo_url"])

# ==========================================
# ABA 3: MANUAIS & PRODUTOS (ALIMENTAR O CONHECIMENTO DO PRODUTO)
# ==========================================
indice_manuais = abas_navegacao.index("📚 Manuais & Produtos")
with tabs[indice_manuais]:
  st.subheader("📚 Base de Conhecimento de Produtos e Manuais Técnicos")
  st.markdown(
      "Alimente aqui a IA com **manuais completos, parâmetros, regras de"
      " negócio e especificações** dos seus sistemas e hardwares. Quanto mais"
      " informações você cadastrar, mais inteligente e assertivo o Copilot será"
      " nos diagnósticos!"
  )

  with st.form("form_novo_manual", clear_on_submit=True):
    col_m1, col_m2 = st.columns(2)
    with col_m1:
      m_sistema = st.selectbox(
          "💻 Sistema / Módulo Afetado:",
          LISTA_SISTEMA,
          key="manual_sistema",
      )
      m_titulo = st.text_input(
          "Título do Manual / Especificação:",
          placeholder="Ex: Manual de Configuração de IPs e Portas - The New",
      )
    with col_m2:
      m_hardware = st.selectbox(
          "⚙️ Hardware Relacionado (Opcional):",
          LISTA_HARDWARE,
          key="manual_hw",
      )

    m_conteudo = st.text_area(
        "📄 Conteúdo Completo, Parâmetros ou Regras do Produto:",
        placeholder=(
            "Cole aqui todo o texto do manual, especificações técnicas,"
            " comandos SQL, comportamentos esperados, códigos de erro e regras"
            " de funcionamento do produto..."
        ),
        height=200,
    )

    if st.form_submit_button("💾 Salvar Manual na Base de Conhecimento"):
      if m_titulo and m_conteudo:
        dados_manual = {
            "sistema_produto": m_sistema,
            "hardware": m_hardware,
            "titulo": m_titulo,
            "conteudo": m_conteudo,
        }
        if salvar_manual_db(dados_manual, "tecnico@actuar.group"):
          st.toast(
              "Manual cadastrado com sucesso! O Guia Interativo e o Copilot"
              " já estão com acesso a ele.",
              icon="🎉",
          )
          st.rerun()
      else:
        st.error(
            "Preencha o título e o conteúdo do manual antes de salvar."
        )

  st.markdown("---")
  st.markdown("### 📋 Manuais Cadastrados Atualmente")
  if df_manuais.empty:
    st.info(
        "Nenhum manual técnico cadastrado ainda. Adicione acima para treinar a"
        " IA sobre o seu produto!"
    )
  else:
    for _, row in df_manuais.iterrows():
      m_id = row["id"]
      m_tit = row.get("titulo", "Sem título")
      m_sist = row.get("sistema_produto", "N/A")
      m_hw = row.get("hardware", "N/A")
      m_cont = row.get("conteudo", "")

      with st.expander(f"📖 [ID #{m_id}] {m_tit} ({m_sist} / {m_hw})"):
        st.markdown(f"**Conteúdo Registrado:**\n{m_cont}")
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
  st.caption(
      "Visão executiva simplificada para exibição em monitores e TVs de suporte."
  )

  if df_ocorrencias.empty:
    st.info("Nenhuma ocorrência registrada para exibir no Modo TV.")
  else:
    total_ocorr = len(df_ocorrencias)
    total_definitiva = len(
        df_ocorrencias[
            df_ocorrencias["status"].str.contains(
                "Definitiva", case=False, na=False
            )
        ]
    )
    total_contorno = len(
        df_ocorrencias[
            df_ocorrencias["status"].str.contains(
                "Contorno", case=False, na=False
            )
        ]
    )
    total_bug = len(
        df_ocorrencias[
            df_ocorrencias["status"].str.contains("Bug", case=False, na=False)
        ]
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total de Ocorrências", total_ocorr)
    m2.metric("Soluções Definitivas", total_definitiva)
    m3.metric("Contornos / Paliativos", total_contorno)
    m4.metric("Bugs / Em Análise", total_bug)

    st.markdown("---")
    st.markdown("### 📋 Últimas Ocorrências Registradas")

    df_tv = (
        df_ocorrencias[["sistema", "equipamento", "problema", "status", "nivel"]]
        .head(12)
        .reset_index(drop=True)
    )
    st.dataframe(
        df_tv,
        column_config={
            "sistema": "Sistema",
            "equipamento": "Hardware",
            "problema": "Problema (Sintoma)",
            "status": "Status",
            "nivel": "Nível",
        },
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("---")
    auto_refresh = st.checkbox(
        "🔄 Ativar atualização automática (a cada 60 segundos)",
        value=False,
        key="tv_auto_refresh",
    )
    if auto_refresh:
      time.sleep(60)
      st.rerun()

# ==========================================
# ABA 5: MEUS FAVORITOS
# ==========================================
indice_fav = abas_navegacao.index("⭐ Meus Favoritos")
with tabs[indice_fav]:
  st.subheader("⭐ Meus Chamados Frequentes & Favoritos")
  st.caption("Acesse rapidamente os problemas que você mais resolve.")

  if not st.session_state.favoritos or df_ocorrencias.empty:
    st.info("Você ainda não favoritou nenhuma ocorrência.")
  else:
    df_fav = df_ocorrencias[
        df_ocorrencias["id"].isin(st.session_state.favoritos)
    ]

    for _, row in df_fav.iterrows():
      ocor_id = int(row["id"])
      sist = row.get("sistema", "N/A")
      hw = row.get("equipamento", "N/A")
      prob = row.get("problema", "Sem descrição")
      status = row.get("status", "🟢 Solução Definitiva")
      nivel = row.get("nivel", "N1")
      anexo = row.get("anexo_url", None)
      solucao_val = row.get("solucao", "")

      titulo_card_fav = (
          f"⭐ [FAVORITO] {prob}  |  📂 [{sist} • {hw}]  —  {status}"
      )

      with st.expander(titulo_card_fav):
        if st.button("❌ Remover dos Favoritos", key=f"rm_fav_tab_{ocor_id}"):
          st.session_state.favoritos = [
              i for i in st.session_state.favoritos if i != ocor_id
          ]
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
# ABA 6: CADASTRAR TRATATIVA
# ==========================================
indice_cad = abas_navegacao.index("➕ Cadastrar Tratativa")
with tabs[indice_cad]:
  st.subheader("➕ Novo Mapeamento Técnico")
  with st.form("form_novo", clear_on_submit=True):
    col_c1, col_c2 = st.columns(2)
    with col_c1:
      in_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE)
      in_status = st.selectbox(
          "📌 Status da Tratativa:",
          [
              "🟢 Solução Definitiva",
              "🟡 Contorno / Paliativo",
              "🔴 Bug / Em Análise",
          ],
      )
    with col_c2:
      in_sist = st.selectbox("💻 Sistema (Software):", LISTA_SISTEMA)
      in_nivel = st.selectbox(
          "📊 Nível de Complexidade:",
          [
              "N1 - Fácil / Rápido",
              "N2 - Intermediário",
              "N3 - Avançado / Laboratório",
          ],
      )

    in_prob = st.text_input(
        "Problema (Sintoma):",
        placeholder="Ex: Catraca trava comunicação ao autenticar facial",
    )
    in_files_prob = st.file_uploader(
        "📎 Imagens ou Arquivos do Problema (Sintoma):",
        type=["png", "jpg", "jpeg", "pdf", "txt", "docx", "xlsx", "csv", "zip"],
        accept_multiple_files=True,
        key="cad_prob_files",
    )

    in_motivo = st.text_area(
        "Motivo (Causa Raiz):",
        placeholder="Ex: Conflito de IPs na rede do cliente ou porta bloqueada",
    )

    st.markdown("---")
    st.markdown("### 🛠️ Passos da Solução")
    st.caption("Adicione os procedimentos necessários para resolver o problema.")

    passos_novos_lista = []
    for p_idx in range(1, 4):
      st.markdown(f"**Passo {p_idx}**")
      col_p_txt, col_p_file = st.columns([2, 1])
      with col_p_txt:
        txt_p = st.text_area(
            f"Descrição do Passo {p_idx}:",
            placeholder=f"Ex: {p_idx}° Faça tal procedimento...",
            key=f"cad_p_txt_{p_idx}",
        )
      with col_p_file:
        files_p = st.file_uploader(
            f"Anexos Passo {p_idx}",
            type=[
                "png",
                "jpg",
                "jpeg",
                "pdf",
                "txt",
                "docx",
                "xlsx",
                "csv",
                "zip",
            ],
            accept_multiple_files=True,
            key=f"cad_p_file_{p_idx}",
        )

      if txt_p.strip():
        url_anexo_p = upload_multiplos_arquivos(files_p) if files_p else None
        passos_novos_lista.append({
            "passo": p_idx,
            "texto": txt_p.strip(),
            "anexo": url_anexo_p,
        })

    if st.form_submit_button("💾 Salvar Mapeamento no Banco"):
      if in_prob and in_motivo and passos_novos_lista:
        json_solucao = json.dumps(passos_novos_lista)
        url_anexo_prob = (
            upload_multiplos_arquivos(in_files_prob) if in_files_prob else None
        )
        autor_reg = "tecnico@actuar.group"

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
        if salvar_ocorrencia_db(dados, autor_reg):
          st.toast("Tratativa salva com sucesso!", icon="🎉")
          st.rerun()
      else:
        st.error(
            "Preencha o problema, o motivo e ao menos o Passo 1 da solução."
        )

# ==========================================
# ABA 7: IMPORTAR & EXPORTAR BANCO EM TXT
# ==========================================
indice_export = abas_navegacao.index("📥 Importar & Exportar (TXT)")
with tabs[indice_export]:
  st.subheader("📥 Importar & Exportar Base de Conhecimento Completa (.TXT)")
  st.caption(
      "Importe ocorrências em lote através de um arquivo `.TXT` estruturado"
      " ou baixe a base unificada completa contendo manuais, produtos e tratativas."
  )

  st.markdown("### 📤 Importar Ocorrências em Lote")
  with st.form("form_import_txt"):
    arquivo_txt = st.file_uploader(
        "Selecione o arquivo .TXT estruturado:", type=["txt"]
    )
    submitted_import = st.form_submit_button("🚀 Processar e Importar Ocorrências")
    if submitted_import:
      if arquivo_txt is not None:
        qtd = processar_importacao_txt(
            arquivo_txt.getvalue(), "tecnico@actuar.group"
        )
        if qtd > 0:
          st.success(f"{qtd} ocorrências foram importadas com sucesso!")
          time.sleep(1)
          st.rerun()
        else:
          st.warning("Nenhuma ocorrência válida encontrada.")
      else:
        st.warning("Envie um arquivo .TXT válido.")

  st.markdown("---")
  st.markdown("### 📥 Exportar Base Completa Unificada (Manuais + Tratativas)")
  
  tipo_export_ocor = st.radio(
      "Selecione o escopo das ocorrências a serem incluídas na exportação:",
      [
          "Todas as Ocorrências (Base Completa)",
          "Apenas Ocorrências Filtradas (aba Diagnósticos)",
      ],
      horizontal=True,
  )

  df_para_exportar_ocor = (
      df_ocorrencias
      if tipo_export_ocor == "Todas as Ocorrências (Base Completa)"
      else st.session_state.get("df_filtered", df_ocorrencias)
  )

  st.info(
      f"📊 Itens na exportação: **{len(df_manuais)}** manual(is) de produto(s) e "
      f"**{len(df_para_exportar_ocor)}** ocorrência(s)/tratativa(s)."
  )

  conteudo_txt = ""
  conteudo_txt += "=" * 70 + "\n"
  conteudo_txt += "ACTUAR.GROUP - EXPORTAÇÃO GERAL DA BASE DE CONHECIMENTO\n"
  conteudo_txt += f"Data de geração: {time.strftime('%d/%m/%Y %H:%M:%S')}\n"
  conteudo_txt += "=" * 70 + "\n\n"

  conteudo_txt += "======================================================================\n"
  conteudo_txt += "SEÇÃO 1: MANUAIS, PRODUTOS E REGRAS DE NEGÓCIO\n"
  conteudo_txt += "======================================================================\n\n"

  if df_manuais.empty:
    conteudo_txt += "[Nenhum manual cadastrado na base]\n\n"
  else:
    for _, row in df_manuais.iterrows():
      conteudo_txt += f"Manual ID: #{row.get('id', 'N/A')}\n"
      conteudo_txt += f"Título: {row.get('titulo', 'N/A')}\n"
      conteudo_txt += f"Sistema / Módulo: {row.get('sistema_produto', 'N/A')}\n"
      conteudo_txt += f"Hardware: {row.get('hardware', 'N/A')}\n"
      conteudo_txt += f"Data de Criação: {row.get('created_at', 'N/A')}\n"
      conteudo_txt += f"Conteúdo / Regras:\n{row.get('conteudo', 'N/A')}\n"
      conteudo_txt += "-" * 50 + "\n\n"

  conteudo_txt += "======================================================================\n"
  conteudo_txt += "SEÇÃO 2: OCORRÊNCIAS, DIAGNÓSTICOS E TRATATIVAS\n"
  conteudo_txt += "======================================================================\n\n"

  if df_para_exportar_ocor.empty:
    conteudo_txt += "[Nenhuma ocorrência registrada]\n\n"
  else:
    for _, row in df_para_exportar_ocor.iterrows():
      conteudo_txt += f"Erro: {row.get('problema', 'N/A')}\n"
      conteudo_txt += f"Sistema: {row.get('sistema', 'N/A')}\n"
      conteudo_txt += f"Hardware: {row.get('equipamento', 'N/A')}\n"
      conteudo_txt += f"Status: {row.get('status', 'N/A')}\n"
      conteudo_txt += f"Nível: {row.get('nivel', 'N/A')}\n"
      conteudo_txt += f"Motivo / Causa Raiz: {row.get('motivo', 'N/A')}\n"
      conteudo_txt += f"Solução: {row.get('solucao', 'N/A')}\n"
      conteudo_txt += f"Anexo URL: {row.get('anexo_url', 'N/A')}\n"
      conteudo_txt += "-" * 50 + "\n\n"

  st.download_button(
      label="📥 Baixar Base Completa em TXT (Manuais + Tratativas)",
      data=conteudo_txt,
      file_name="base_geral_completa_actuar.txt",
      mime="text/plain",
  )

# ==========================================
# ABA 8: AUDIT LOG
# ==========================================
indice_audit = abas_navegacao.index("📜 Audit Log (Gestão)")
with tabs[indice_audit]:
  st.subheader("📜 Histórico de Auditoria (Audit Log)")
  st.caption("Acompanhe todas as interações e alterações realizadas.")

  try:
    res_logs = (
        supabase.table("audit_logs")
        .select("*")
        .order("id", desc=True)
        .limit(100)
        .execute()
    )
    df_logs = pd.DataFrame(res_logs.data)
    if not df_logs.empty:
      st.dataframe(
          df_logs[["created_at", "usuario_email", "acao", "detalhes"]],
          column_config={
              "created_at": "Data/Hora",
              "usuario_email": "Usuário",
              "acao": "Ação",
              "detalhes": "Detalhamento",
          },
          use_container_width=True,
      )
    else:
      st.info("Nenhum histórico registrado no momento.")
  except Exception as e:
    st.error(f"Erro ao carregar log: {e}")