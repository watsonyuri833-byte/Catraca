import streamlit as st
import pandas as pd

# Configuração da página
st.set_page_config(
    page_title="actuar.group - Troubleshooting & Pódio",
    page_icon="⚡",
    layout="wide"
)

# Estilização CSS customizada para visual SaaS Dark
st.markdown("""
<style>
    /* Estilo dos cards de pódio e métricas */
    .st-podium-card {
        background-color: #1E293B;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border: 1px solid #334155;
        margin-bottom: 10px;
    }
    .st-gold { border: 2px solid #EAB308; }
    .st-silver { border: 2px solid #94A3B8; }
    .st-bronze { border: 2px solid #D97706; }
    
    /* Ajuste dos botões de navegação superiores */
    div.stButton > button {
        width: 100%;
        border-radius: 8px;
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
    }
    div.stButton > button:hover {
        background-color: #334155;
        border-color: #6366F1;
    }
</style>
""", unsafe_allow_html=True)

# Topo: Cabeçalho
col_logo, col_space, col_user = st.columns([2, 5, 2])
with col_logo:
    st.title("actuar.group")
with col_user:
    st.write("🌙 **Modo Escuro** | 👤 Analyst")

st.markdown("---")

# --- NAVEGAÇÃO POR ABAS NO TOPO ---
nav_cols = st.columns(6)
with nav_cols[0]:
    page_dash = st.button("📊 Troubleshooting")
with nav_cols[1]:
    page_prio = st.button("⭐ Prioridades")
with nav_cols[2]:
    page_pecas = st.button("📦 Solicit. Peças")
with nav_cols[3]:
    page_rank = st.button("🏆 Ranking Geral")
with nav_cols[4]:
    page_envio = st.button("🚚 Envio")
with nav_cols[5]:
    page_faq = st.button("❓ FAQ / Métricas")

# Gerenciamento de Estado da Navegação
if "pagina" not in st.session_state:
    st.session_state.pagina = "Troubleshooting"

if page_dash: st.session_state.pagina = "Troubleshooting"
if page_prio: st.session_state.pagina = "Prioridades"
if page_pecas: st.session_state.pagina = "Solicit. Peças"
if page_rank: st.session_state.pagina = "Ranking Geral"
if page_envio: st.session_state.pagina = "Envio"
if page_faq: st.session_state.pagina = "FAQ / Métricas"

st.markdown("---")

# --- CONTEÚDO DAS PÁGINAS ---

if st.session_state.pagina == "Troubleshooting":
    st.subheader("🔍 Base de Erros e Soluções (Catracas & Periféricos)")
    st.caption("Consulte os diagnósticos técnicos e tratativas recomendadas.")

    # Filtros
    f_col1, f_col2 = st.columns(2)
    with f_col1:
        eq_filter = st.selectbox("Equipamento:", ["Todos", "Catraca", "Control iD", "Face Webcam"])
    with f_col2:
        search_query = st.text_input("Buscar problema ou palavra-chave:", "")

    st.markdown("### 📋 Mapeamento de Ocorrências")
    
    # Exemplo de Cards estilo SaaS
    with st.expander("🔴 [Control iD] Mostra nome de outro aluno ao ler o rosto"):
        st.error("**Causa Raiz:** Corrupção da base de fotos local no dispositivo.")
        st.success("**Solução:** Apagar memória de fotos do aparelho e refazer resync completo.")

    with st.expander("🟡 [Face Webcam] Imagem travando ou caindo conexão"):
        st.warning("**Causa Raiz:** Extensor USB passivo com perda de pacotes.")
        st.success("**Solução:** Conectar direto na porta USB ou utilizar extensor 3.0 ativo.")

    with st.expander("🔴 [Catraca] Libera no facial local, mas não via comando TCP/IP"):
        st.error("**Causa Raiz:** Configuração de sentido ou bloqueio de porta/firmware.")
        st.success("**Solução:** Verificar parametrização de sentido da placa e liberar portas de comando.")

elif st.session_state.pagina == "Ranking Geral":
    st.subheader("🏆 Pódio por Departamento")
    st.caption("Top 3 colocados do departamento de suporte a catracas.")

    c_s, c1, c2, c3, c_e = st.columns([1, 3, 3, 3, 1])
    
    with c1:
        st.markdown("""
        <div class="st-podium-card st-silver">
            <h3>🥈 2º Lugar</h3>
            <h4>Watson Cruz</h4>
            <h2>1685 pts</h2>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown("""
        <div class="st-podium-card st-gold">
            <h3>🥇 1º Lugar</h3>
            <h4>Analista Destaque</h4>
            <h2>1971 pts</h2>
        </div>
        """, unsafe_allow_html=True)
        
    with c3:
        st.markdown("""
        <div class="st-podium-card st-bronze">
            <h3>🥉 3º Lugar</h3>
            <h4>Analista 3</h4>
            <h2>848 pts</h2>
        </div>
        """, unsafe_allow_html=True)

elif st.session_state.pagina == "Envio":
    st.subheader("🚚 Envio de Peças")
    st.info("📦 **Área em construção:** As telas de rastreamento de envio de peças e extensores serão integradas em breve.")

else:
    st.subheader(f"📌 {st.session_state.pagina}")
    st.write("Módulo em desenvolvimento.")