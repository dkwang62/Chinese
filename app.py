import json
import math
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(layout="wide")

IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

def bootstrap_session_state():
    st.session_state.setdefault("font_scale", 1.0)

bootstrap_session_state()

def apply_dynamic_css():
    font_scale = st.session_state.get("font_scale", 1.0)
    css = f"""
    <style>
        :root {{ --fontScale: __FONTSCALE__; }}
        .selected-card {{
            background-color: #e8f4f8;
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: flex;
            align-items: center;
            gap: 20px;
            border-left: 6px solid #3498db;
        }}
        .selected-char {{ font-size: calc(3em * var(--fontScale)); color: #e74c3c; }}
        .details {{ font-size: calc(1.6em * var(--fontScale)); color: #2c3e50; }}
        .details strong {{ color: #34495e; }}
        .results-header {{ font-size: calc(1.8em * var(--fontScale)); color: #2c3e50; margin: 30px 0 15px; }}
        .char-card {{
            background: white;
            padding: 18px;
            border-radius: 10px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .comp-grid .stButton button {{
            font-size: calc(1.4em * var(--fontScale));
            height: 60px;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.08);
        }}
        .comp-grid .stButton button:hover {{
            background: #fff5f5;
            border-color: #f2c6c6;
            color: #c0392b;
        }}
        .status-line {{
            font-size: 1.1em;
            color: #555;
            margin: 15px 0;
            font-style: italic;
        }}
        @media (max-width: 768px) {{
            .selected-card {{ flex-direction: column; text-align: center; }}
            .comp-grid .stButton button {{ font-size: calc(1.2em * var(--fontScale)); height: 55px; }}
        }}
    </style>
    """.replace("__FONTSCALE__", str(font_scale))
    st.markdown(css, unsafe_allow_html=True)

@st.cache_data
def load_component_map():
    with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

try:
    component_map = load_component_map()
except Exception as e:
    component_map = {}
    st.error("Failed to load data.")

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"

def get_stroke_count(char):
    strokes = component_map.get(char, {}).get("meta", {}).get("strokes", None)
    try:
        if isinstance(strokes, (int, float)) and strokes > 0:
            return int(strokes)
        if isinstance(strokes, str) and strokes.isdigit():
            return int(strokes)
    except:
        pass
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
    "selected_comp": "", "stroke_count": 0, "radical": "No Filter", "component_idc": "No Filter",
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
    st.session_state.radical = "No Filter"
    st.session_state.component_idc = "No Filter"
    st.session_state.page = 1
    st.session_state.show_inputs = True
    st.session_state.preview_active = False
    st.session_state.preview_comp = None

def render_preview(c):
    meta = component_map.get(c, {}).get("meta", {})
    f = {
        "Pinyin": clean_field(meta.get("pinyin", "—")),
        "Strokes": f"{get_stroke_count(c)} strokes" if get_stroke_count(c) else "unknown",
        "Radical": clean_field(meta.get("radical", "—")),
        "Decomposition": format_decomposition(c),
        "Definition": clean_field(meta.get("definition", "—")),
        "Etymology": get_etymology_text(meta),
    }
    details = " · ".join(f"<strong>{k}:</strong> {v}" for k, v in f.items())
    st.markdown(f'<div class="selected-card"><h2 class="selected-char">{c}</h2><div class="details">{details}</div></div>', unsafe_allow_html=True)
    st.caption("Click again to confirm selection")

def main():
    if not component_map:
        st.stop()

    apply_dynamic_css()
    st.markdown("<h1 style='text-align:center;'>🈑 Radix</h1>", unsafe_allow_html=True)

    # === SIDEBAR CONTROLS ===
    with st.sidebar:
        st.markdown("### Filters")

        # Strokes: force everything to int
        raw_strokes = [get_stroke_count(c) for c in component_map]
        stroke_set = {s for s in raw_strokes if isinstance(s, int)}
        stroke_opts = [0] + sorted(stroke_set)
        # Ensure current value is valid int
        current = st.session_state.stroke_count if isinstance(st.session_state.stroke_count, int) and st.session_state.stroke_count in stroke_opts else 0
        st.selectbox(
            "Strokes",
            options=stroke_opts,
            index=stroke_opts.index(current),
            format_func=lambda x: "Any" if x == 0 else str(x),
            key="w_stroke",
            on_change=sync_stroke
        )

        # Radical
        rad_set = {component_map.get(c, {}).get("meta", {}).get("radical", "") for c in component_map if component_map.get(c, {}).get("meta", {}).get("radical")}
        rad_opts = ["No Filter"] + sorted(rad_set)
        st.selectbox(
            "Radical",
            options=rad_opts,
            index=rad_opts.index(st.session_state.radical),
            key="w_radical",
            on_change=sync_radical
        )

        # Structure
        idc_set = {d[0] for d in (component_map.get(c, {}).get("meta", {}).get("decomposition", "") for c in component_map) if d and d[0] in IDC_CHARS}
        idc_opts = ["No Filter"] + sorted(idc_set)
        st.selectbox(
            "Structure",
            options=idc_opts,
            index=idc_opts.index(st.session_state.component_idc),
            key="w_idc",
            on_change=sync_idc
        )

        st.markdown("---")
        if st.session_state.text_input_warning:
            st.warning(st.session_state.text_input_warning)
        st.text_input("Jump to character", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text, placeholder="e.g. 水")

    # === MAIN AREA ===
    if not st.session_state.show_inputs:
        col1, col2 = st.columns([1,1])
        with col1: st.button("← Back", on_click=back, use_container_width=True)
        with col2: st.button("Reset Filters", on_click=reset, use_container_width=True)

        if st.session_state.selected_comp not in component_map:
            st.stop()

        meta = component_map[st.session_state.selected_comp]["meta"]
        f = {
            "Pinyin": clean_field(meta.get("pinyin", "—")),
            "Strokes": f"{get_stroke_count(st.session_state.selected_comp)} strokes" if get_stroke_count(st.session_state.selected_comp) else "unknown",
            "Radical": clean_field(meta.get("radical", "—")),
            "Decomposition": format_decomposition(st.session_state.selected_comp),
            "Definition": clean_field(meta.get("definition", "—")),
            "Etymology": get_etymology_text(meta),
        }
        details = " · ".join(f"<strong>{k}:</strong> {v}" for k, v in f.items())
        st.markdown(f'<div class="selected-card"><h2 class="selected-char">{st.session_state.selected_comp}</h2><div class="details">{details}</div></div>', unsafe_allow_html=True)

        with st.expander("Output Type", expanded=False):
            modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
            st.radio("", options=modes, index=modes.index(st.session_state.display_mode), key="w_display", on_change=sync_display, horizontal=True)

        related = component_map[st.session_state.selected_comp].get("related_characters", [])
        chars = [c for c in related if len(c)==1]
        n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
        compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars} if n else {c:[] for c in chars}
        chars = [c for c in chars if n==0 or compounds[c]]

        st.markdown(f"<div class='results-header'>🧬 Results — {len(chars)}</div>", unsafe_allow_html=True)
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
            st.button(c, key=f"res_{c}", on_click=tile_click, args=(c,))
            st.markdown(f"<div class='char-card'><div class='details'>{det}</div></div>", unsafe_allow_html=True)
            if compounds.get(c):
                st.markdown(f"<div class='compounds-section'><strong>{st.session_state.display_mode}:</strong> {' '.join(sorted(compounds[c]))}</div>", unsafe_allow_html=True)

        if chars and n:
            with st.expander("Export Compounds"):
                st.text_area("Copy list", "\n".join(w for c in chars for w in compounds[c]), height=150)
        return

    # === BROWSING MODE ===
    parts = []
    if st.session_state.stroke_count > 0: parts.append(f"{st.session_state.stroke_count} strokes")
    if st.session_state.radical != "No Filter": parts.append(f"Radical: {st.session_state.radical}")
    if st.session_state.component_idc != "No Filter": parts.append(f"Structure: {st.session_state.component_idc}")
    status = " · ".join(parts) or "No filters"
    st.markdown(f"<div class='status-line'>Filtered: {status}</div>", unsafe_allow_html=True)

    st.caption("Click tile → preview → click again to confirm")

    filtered = [c for c in component_map if
        (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
        (st.session_state.radical == "No Filter" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
        (st.session_state.component_idc == "No Filter" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
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
    GRID_COLS = 15
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

if __name__ == "__main__":
    main()
