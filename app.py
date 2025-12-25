    else:
        st.session_state.display_mode = "Single Character"
        path_items = ["🏠 Root"] + st.session_state.history + [f"<b>{st.session_state.selected_comp}</b>"]
        path_str = " → ".join(path_items)
        st.markdown(
            f"""
            <div class='status-line'>
                <div style='margin-bottom:8px;'>
                    <span class='status-tag'>Location</span>
                    <span class='map-path'>{path_str}</span>
                </div>
                <div class='status-text' style='font-size:0.85em; color:#666;'>Single-click previews. Use Explore button to enter.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected = st.session_state.selected_comp
        decomp_raw = component_map.get(selected, {}).get("meta", {}).get("decomposition", "")
        components_list = [c for c in decomp_raw if c not in IDC_CHARS and c != "?" and c != "–"]

        related_raw = component_map.get(selected, {}).get("related_characters", [])
        children_list = [c for c in related_raw if isinstance(c, str) and len(c) == 1]
        children_sorted = sorted(children_list, key=sort_key_usage_then_zipf)

        final_chars_list = []
        seen = set()
        for c in components_list:
            if c not in seen and c in component_map:
                final_chars_list.append(c)
                seen.add(c)
        for c in children_sorted:
            if c not in seen and c in component_map:
                final_chars_list.append(c)
                seen.add(c)

        chars = final_chars_list
        LIMIT = 120
        clickable_chars = apply_script_filter(chars[:LIMIT])
        static_chars = apply_script_filter(chars[LIMIT:])

        # === CLICKABLE CHARACTERS (with one-click preview) ===
        for c in clickable_chars:
            col_char, col_details = st.columns([2, 10])

            with col_char:
                is_preview = st.session_state.preview_comp == c

                st.markdown("<div class='char-btn-wrap'>", unsafe_allow_html=True)
                st.button(
                    c,
                    key=f"explore_char_{c}",
                    type="primary" if is_preview else "secondary",
                    on_click=list_tile_click,
                    args=(c,),
                )
                st.markdown("</div>", unsafe_allow_html=True)

                st.markdown("<div class='pen-btn-wrap'>", unsafe_allow_html=True)
                if st.button("🖊️", key=f"stroke_btn_{c}", help="View stroke order"):
                    st.session_state.stroke_view_char = c
                    st.session_state.stroke_view_active = True
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            with col_details:
                st.markdown(
                    generate_clean_card_html(c, usage_count=component_usage_count(c)),
                    unsafe_allow_html=True
                )

            st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

        # === STATIC CHARACTERS ===
        if static_chars:
            st.markdown("---")
            st.markdown(
                f"<div style='text-align:center; color:#888; font-weight:bold; margin-bottom:20px;'>"
                f"⬇️ {len(static_chars)} More Results (Copy & Paste into Shortcut sidebar to explore) ⬇️"
                f"</div>",
                unsafe_allow_html=True,
            )

            for c in static_chars:
                col_char, col_details = st.columns([2, 10])

                with col_char:
                    st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)

                with col_details:
                    st.markdown(
                        generate_clean_card_html(c, usage_count=component_usage_count(c)),
                        unsafe_allow_html=True
                    )

                st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

        if static_chars:
            st.markdown("---")
            st.markdown(
                f"<div style='text-align:center; color:#888; font-weight:bold; margin-bottom:20px;'>"
                f"⬇️ {len(static_chars)} More Results (Copy & Paste into Shortcut sidebar to explore) ⬇️"
                f"</div>",
                unsafe_allow_html=True,
            )
            
            for c in static_chars:
                col_char, col_details = st.columns([2, 10])
                
                with col_char:
                    st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
                
                with col_details:
                    st.markdown(
                        generate_clean_card_html(c, usage_count=component_usage_count(c)),
                        unsafe_allow_html=True
                    )
                
                st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
