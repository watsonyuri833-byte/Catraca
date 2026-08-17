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
            anexo = row.get('anexo_url', None)
            
            with st.expander(f"[{status}] {sist} + {hw} — {prob}"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**💻 Sistema:** {sist}")
                c2.markdown(f"**⚙️ Hardware:** {hw}")
                c3.markdown(f"**⏱️ Complexidade/Tempo:** {nivel} ({tempo})")
                
                st.markdown(f"**Motivo (Causa Raiz):**\n{row.get('motivo', '-')}")
                st.success(f"**Solução Recomendada:**\n{row.get('solucao', '-')}")
                
                # Exibição de Imagem/Anexo
                if anexo and str(anexo).startswith("http"):
                    st.markdown("📷 **Evidência Anexada:**")
                    st.image(anexo, width=450)

                # Avaliações (Votos)
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

                # Comentários
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

                # Botão de Exclusão (Disponível sempre para você como Admin)
                st.markdown("---")
                if st.button(f"🗑️ Excluir Tratativa #{ocor_id}", key=f"del_{ocor_id}"):
                    deletar_ocorrencia_db(ocor_id, st.session_state.user.email)
                    st.toast(f"Tratativa #{ocor_id} excluída!", icon="🗑️")
                    st.rerun()