import json
import math
import streamlit as st

st.set_page_config(layout="wide")

IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

def apply_dynamic_css():
    css = """
    <style>
        /* ... keep your other existing styles (buttons, headers, etc.) ... */

        /* UPDATED: Make instructions prominent */
        .status-line {
            font-size: 1.1em;
            font-weight: 600;
            color: #0f5132;
            background-color: #d1e7dd; /* Light green background for visibility */
            border: 1px solid #badbcc;
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0 30px 0;
            text-align: center;
        }

        /* ... keep other styles ... */
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_data
def load_component_map():
    # Ensure this file exists in your directory
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {}

try:
    component_map = load_component_map()
except Exception as e:
    component_map = {}
    st.error(f"Failed to load data: {e}")

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"

def get_stroke_count(char):
    strokes = component_map.get(char, {}).get("meta", {}).get("strokes", None)
    try:
        if isinstance(strokes, (int, float)) and strokes > 0: return int(strokes)
        if isinstance(strokes, str) and strokes.isdigit(): return int(strokes)
    except: pass
    return None

def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", "No hint"))
    details = clean_field(etymology.get("details", ""))
    return f"{hint}{'; ' + details if details and details != '—' else ''}"

def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "—" if not d or '?' in d else d

def get_all_components(char, max_depth=5, depth=0, seen=None):
    if seen is None: seen = set()
    if char in seen or depth > max_depth or len(char) != 1: return set()
    seen.add(char)
    s = set()
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    if d:
        for c in d:
            if c in IDC_CHARS or c == '?' or len(c) != 1: continue
            s.add(c)
            s.update(get_all_components(c, max_depth, depth+1, seen.copy()))
    return s

# State init
defaults = {
    "selected_comp": "", "stroke_count": 0, "radical": "none", "component_idc": "none",
    "display_mode": "Single Character", "text_input_comp": "", "page": 1, "text_input_warning": None,
    "show_inputs": True, "last_valid_selected_comp": "", "preview_comp": None, "preview_active": False
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Callbacks
def sync_stroke():
    val = st.session_state.w_stroke
    st.session_state.stroke_count = int(val) if val != 0 else 0
    st.session_state.page = 1

def sync_radical():
    st.session_state.radical = st.session_state.w_radical
    st.session_state.page = 1

def sync_idc():
    st.session_state.component_idc = st.session_state.w_idc
    st.session_state.page = 1

def sync_display():
    st.session_state.display_mode = st.session_state.w_display

def sync_text():
    v = st.session_state.w_text.strip()
    if len(v) != 1:
        st.session_state.text_input_warning = "One character only"
        return
    if v in component_map:
        st.session_state.selected_comp = v
        st.session_state.last_valid_selected_comp = v
        st.session_state.text_input_comp = v
        st.session_state.text_input_warning = None
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
    else:
        st.session_state.text_input_warning = "Not found"

def tile_click(c):
    if st.session_state.preview_active and st.session_state.preview_comp == c:
        st.session_state.selected_comp = c
        st.session_state.last_valid_selected_comp = c
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
        st.session_state.preview_comp = None
    else:
        st.session_state.preview_active = True
        st.session_state.preview_comp = c

def back():
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None

def reset():
    st.session_state.stroke_count = 0
    st.session_state.radical = "none"
    st.session_state.component_idc = "none"
    st.session_state.page = 1
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None

def render_preview(c):
    meta = component_map.get(c, {}).get("meta", {})
    
    # 1. Get the raw values
    val_pinyin = clean_field(meta.get("pinyin", "—"))
    val_strokes = f"{get_stroke_count(c)} strokes" if get_stroke_count(c) else ""
    val_radical = clean_field(meta.get("radical", "—"))
    val_decomp = format_decomposition(c)
    val_def = clean_field(meta.get("definition", "—"))
    val_etym = get_etymology_text(meta)

    # 2. Build the list of parts to display
    parts = []

    # No Label: Pinyin
    if val_pinyin != "—": 
        parts.append(val_pinyin)

    # No Label: Strokes
    if val_strokes: 
        parts.append(val_strokes)

    # Label: Radical (Usually helpful to distinguish from the main char)
    if val_radical != "—": 
        parts.append(f"<strong>Radical:</strong> {val_radical}")

    # Label: Decomposition
    if val_decomp != "—": 
        parts.append(f"<strong>Decomposition:</strong> {val_decomp}")

    # No Label: Definition
    if val_def != "—": 
        parts.append(val_def)

    # Label: Etymology
    if val_etym: 
        parts.append(f"<strong>Etymology:</strong> {val_etym}")

    # 3. Join them with the separator
    details = " · ".join(parts)
    
    # 4. Render
    with st.container():
        c1, c2 = st.columns([1, 8], vertical_alignment="center")
        
        with c1:
            st.markdown(f'''
                <div style="
                    font-size: 3.5em; 
                    font-weight: bold; 
                    color: #e74c3c; 
                    text-align: center; 
                    line-height: 1;
                ">
                    {c}
                </div>
            ''', unsafe_allow_html=True)
            
        with c2:
            st.markdown(f'''
                <div style="
                    font-size: 1.1em; 
                    color: #2c3e50; 
                    line-height: 1.5;
                ">
                    {details}
                </div>
            ''', unsafe_allow_html=True)
            
    st.markdown("---")
    
    # --- NEW LAYOUT: Side-by-Side and Proportional ---
    # Create a container with a border for the preview area
    with st.container():
        # Use columns: Narrow column for Char, Wide column for Text
        # vertical_alignment="center" ensures the text aligns with the character
        c1, c2 = st.columns([1, 8], vertical_alignment="center")
        
        with c1:
            # Character: Smaller, contained, red
            st.markdown(f'''
                <div style="
                    font-size: 3.5em; 
                    font-weight: bold; 
                    color: #e74c3c; 
                    text-align: center; 
                    line-height: 1;
                ">
                    {c}
                </div>
            ''', unsafe_allow_html=True)
            
        with c2:
            # Description: Normal readable size, left-aligned
            st.markdown(f'''
                <div style="
                    font-size: 1.1em; 
                    color: #2c3e50; 
                    line-height: 1.5;
                ">
                    {details}
                </div>
            ''', unsafe_allow_html=True)
            
    # Add a divider or spacer after the preview to separate it from the grid below
    st.markdown("---")

def main():
    if not component_map:
        st.stop()

    apply_dynamic_css()

    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("<h1 style='text-align:center; margin-bottom:30px;'>🈑 Radix</h1>", unsafe_allow_html=True)

        if st.session_state.show_inputs:
            # Browsing mode
            st.markdown("### Filters")

            stroke_set = {s for s in (get_stroke_count(c) for c in component_map) if isinstance(s, int)}
            stroke_opts = [0] + sorted(stroke_set)
            current = st.session_state.stroke_count if isinstance(st.session_state.stroke_count, int) and st.session_state.stroke_count in stroke_opts else 0
            st.selectbox("Strokes", options=stroke_opts, index=stroke_opts.index(current),
                         format_func=lambda x: "Any" if x == 0 else str(x), key="w_stroke", on_change=sync_stroke)

            rad_set = {component_map.get(c, {}).get("meta", {}).get("radical", "") for c in component_map if component_map.get(c, {}).get("meta", {}).get("radical")}
            rad_opts = ["none"] + sorted(rad_set)
            st.selectbox("Radical", options=rad_opts, index=rad_opts.index(st.session_state.radical), key="w_radical", on_change=sync_radical)

            idc_set = {d[0] for d in (component_map.get(c, {}).get("meta", {}).get("decomposition", "") for c in component_map) if d and d[0] in IDC_CHARS}
            idc_opts = ["none"] + sorted(idc_set)
            st.selectbox("Structure", options=idc_opts, index=idc_opts.index(st.session_state.component_idc), key="w_idc", on_change=sync_idc)

            st.markdown("---")
            if st.session_state.text_input_warning:
                st.warning(st.session_state.text_input_warning)
            st.text_input("Jump to character", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text, placeholder="e.g. 水")

        else:
            # Results mode Sidebar
            st.markdown("### Actions")
            st.button("← Back to list", on_click=back, use_container_width=True)
            st.button("Reset Filters", on_click=reset, use_container_width=True)

            # Selected character
            st.markdown(f"<div class='selected-char-sidebar'>{st.session_state.selected_comp}</div>", unsafe_allow_html=True)

            # Results count logic (using deduplicated count for display)
            related = component_map[st.session_state.selected_comp].get("related_characters", [])
            chars_raw = [c for c in related if len(c)==1]
            chars_unique = list(set(chars_raw)) # Deduplicate for count
            
            n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
            compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars_unique} if n else {c:[] for c in chars_unique}
            valid_chars = [c for c in chars_unique if n==0 or compounds[c]]
            
            st.markdown(f"<div class='results-header-sidebar'>🧬 Results — {len(valid_chars)}</div>", unsafe_allow_html=True)

            # Output Type
            st.markdown("### Output Type")
            modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
            st.radio("", options=modes, index=modes.index(st.session_state.display_mode), key="w_display", on_change=sync_display)

    # === MAIN CONTENT ===
    if st.session_state.show_inputs:
        # Browsing mode
        filter_parts = []
        if st.session_state.stroke_count > 0:
            filter_parts.append(f"{st.session_state.stroke_count} strokes")
        if st.session_state.radical != "none":
            filter_parts.append(f"Radical: {st.session_state.radical}")
        if st.session_state.component_idc != "none":
            filter_parts.append(f"Structure: {st.session_state.component_idc}")

        filter_summary = " · ".join(filter_parts) if filter_parts else "none"
        instruction = "Click TILE twice to see characters built on this component" if st.session_state.preview_active else "Click a TILE to preview"
        st.markdown(f"<div class='status-line'>Filtered: {filter_summary} — {instruction}</div>", unsafe_allow_html=True)

        filtered = [c for c in component_map if
            (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
            (st.session_state.radical == "none" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
            (st.session_state.component_idc == "none" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
        ]
        extra = get_all_components(st.session_state.selected_comp, max_depth=5)
        filtered = list(set(filtered) | (extra & set(component_map)))
        sorted_comps = sorted(filtered, key=lambda c: get_stroke_count(c) or 999)

        if not sorted_comps:
            st.info("No components match current filters.")
            return

        if st.session_state.preview_active and st.session_state.preview_comp:
            render_preview(st.session_state.preview_comp)

        PAGE_SIZE = 120
        # --- FIX 1: REDUCE COLUMNS TO MAKE TILES WIDER ---
        GRID_COLS = 10 
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        p1, p2, p3 = st.columns([1, 3, 1])
        with p1:
            if st.button("◀ Prev", disabled=st.session_state.page<=1): st.session_state.page -= 1
        with p2:
            start = (st.session_state.page-1)*PAGE_SIZE + 1
            end = min(st.session_state.page*PAGE_SIZE, total)
            st.markdown(f"<div style='text-align:center; padding:10px 0; font-size:1.1em; color:#555;'>{start}–{end} of {total}</div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next ▶", disabled=st.session_state.page>=max_page): st.session_state.page += 1

        page = sorted_comps[(st.session_state.page-1)*PAGE_SIZE : st.session_state.page*PAGE_SIZE]
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(GRID_COLS)
        for i, ch in enumerate(page):
            with cols[i % GRID_COLS]:
                preview = st.session_state.preview_active and st.session_state.preview_comp == ch
                st.button(ch, key=f"b_{ch}_{st.session_state.page}", use_container_width=True,
                          type="primary" if preview else "secondary", on_click=tile_click, args=(ch,))
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Results mode
        related = component_map[st.session_state.selected_comp].get("related_characters", [])
        
        # Deduplicate and filter
        chars = list(set([c for c in related if len(c)==1])) 
        n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
        compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars} if n else {c:[] for c in chars}
        chars = [c for c in chars if n==0 or compounds[c]]

        for c in sorted(chars, key=lambda x: get_stroke_count(x) or 999):
            meta = component_map.get(c, {}).get("meta", {})
            fd = {
                "Pinyin": clean_field(meta.get("pinyin", "—")),
                "Strokes": f"{get_stroke_count(c)} strokes" if get_stroke_count(c) else "unknown",
                "Radical": clean_field(meta.get("radical", "—")),
                "Decomposition": format_decomposition(c),
                "Definition": clean_field(meta.get("definition", "—")),
                "Etymology": get_etymology_text(meta),
            }
            det = " · ".join(f"<strong>{k}:</strong> {v}" for k, v in fd.items())
            
            # Create columns for layout
            c1, c2 = st.columns([1, 10]) 
            
            with c1:
                st.button(c, key=f"res_{c}", on_click=tile_click, args=(c,), use_container_width=True)
            
            with c2:
                # 1. Render Description (White Box)
                st.markdown(f"<div class='char-card'><div class='details'>{det}</div></div>", unsafe_allow_html=True)
                
                # 2. Render Phrases (Green Box)
                # Reduced margin-top to 5px so it sits tight against the white box
                if compounds.get(c):
                    st.markdown(f"<div style='padding:10px; background:#f1f8e9; border-radius:8px; margin-top:5px;'><strong>{st.session_state.display_mode}:</strong> {' '.join(sorted(compounds[c]))}</div>", unsafe_allow_html=True)
                
                # 3. Add Spacer for the NEXT character (The "Blank Row")
                st.markdown("<div style='height: 30px'></div>", unsafe_allow_html=True)
        if chars and n:
            with st.expander("Export Compounds"):
                st.text_area("Copy list", "\n".join(w for c in chars for w in compounds[c]), height=150)

if __name__ == "__main__":
    main()
