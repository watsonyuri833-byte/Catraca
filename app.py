# ==========================================
# ABA 1: CONSULTA + EDIÇÃO + FAVORITO + AVALIAÇÃO + EXCLUSÃO (ORGANIZADA)
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
        f_busca = st.text_input("Buscar termo ou palavra-chave:", "", key="f_busca_tab0")

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
        # 1. Tabela Resumo limpa para visão panorâmica instantânea
        st.markdown("### 📊 Visão Geral dos Chamados Filtrados")
        df_display = df_filtered[["id", "sistema", "equipamento", "problema", "status", "nivel"]].copy()
        st.dataframe(
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
            use_container_width=True
        )
        
        st.markdown("---")
        st.markdown("### 🔎 Detalhar, Avaliar ou Editar Ocorrência")
        
        # 2. Seletor focado para abrir apenas o chamado desejado
        ids_disponiveis = df_filtered["id"].tolist()
        mapa_opcoes = {
            row['id']: f"ID #{row['id']} - [{row.get('sistema', 'N/A')} • {row.get('equipamento', 'N/A')}] {str(row.get('problema', ''))[:55]}..." 
            for _, row in df_filtered.iterrows()
        }
        
        ocor_id_selecionado = st.selectbox(
            "Selecione uma ocorrência abaixo para carregar os detalhes completos e passos:",
            options=ids_disponiveis,
            format_func=lambda x: mapa_opcoes.get(x, str(x))
        )
        
        if ocor_id_selecionado:
            row = df_filtered[df_filtered["id"] == ocor_id_selecionado].iloc[0]
            ocor_id = int(row['id'])
            sist = row.get('sistema', 'N/A')
            hw = row.get('equipamento', 'N/A')
            prob = row.get('problema', 'Sem descrição')
            status = row.get('status', '🟢 Solução Definitiva')
            nivel = row.get('nivel', 'N1')
            tempo = row.get('tempo_estimado', '-')
            anexo = row.get('anexo_url', None)
            solucao_val = row.get('solucao', '')
            
            is_fav = ocor_id in st.session_state.favoritos
            texto_botao_fav = "⭐ Remover dos Favoritos" if is_fav else "☆ Favoritar Chamado"
            
            # Container dedicado com borda para isolar visualmente o chamado selecionado
            with st.container(border=True):
                col_det_title, col_det_fav = st.columns([4, 1])
                with col_det_title:
                    st.markdown(f"### 🚨 {prob}")
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
                
                c1, c2, c3, c4 = st.columns(4)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**⏱️ Tempo:** {nivel} ({tempo})")
                c4.markdown(f"**📌 Status:** {status}")
                
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
                            
                            lista_tempos = ["15 minutos", "30 minutos", "1 hora", "2+ horas", "Requer troca/envio"]
                            idx_tempo = lista_tempos.index(tempo) if tempo in lista_tempos else 0

                            with edit_col1:
                                edit_hw = st.selectbox("⚙️ Catraca / Hardware:", LISTA_HARDWARE, index=idx_hw, key=f"eh_{ocor_id}")
                                edit_status = st.selectbox("📌 Status:", lista_status, index=idx_status, key=f"est_{ocor_id}")
                                edit_nivel = st.selectbox("📊 Nível:", lista_niveis, index=idx_nivel, key=f"en_{ocor_id}")
                            with edit_col2:
                                edit_sist = st.selectbox("💻 Sistema:", LISTA_SISTEMA, index=idx_sist, key=f"es_{ocor_id}")
                                edit_tempo = st.selectbox("⏱️ Tempo Estimado:", lista_tempos, index=idx_tempo, key=f"et_{ocor_id}")

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
                                    "tempo_estimado": edit_tempo,
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