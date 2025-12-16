import json
import math
import streamlit as st

st.set_page_config(
    page_title="Radix - Chinese Character Explorer",
    page_icon="🈑",
    layout="wide",
    initial_sidebar_state="expanded"
)

IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

def apply_dynamic_css():
    css = """
    <style>
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #1a2a3a 0%, #2c3e50 100%);
            color: #ecf0f1;
        }
        [data-testid="stSidebar"] .stMarkdown,
        [data-testid="stSidebar"] label,
        [data-testid="stSidebar"] .stSelectbox > div > div > div,
        [data-testid="stSidebar"] .stTextInput > div > div > input,
        [data-testid="stSidebar"] .stRadio > div > label,
        [data-testid="stSidebar"] .stButton > button {
            color: #ecf0f1 !important;
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label > div:first-child {
            background-color: #ecf0f1 !important;
            border-color: #bdc3c7 !important;
        }
        [data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"] > div:first-child {
            background-color: #3498db !important;
        }
        .app-header {
            text-align: center;
            padding: 2rem 0;
            background: white;
            border-radius: 15px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            margin-bottom: 2rem;
        }
        .app-title {
            font-size: 3em;
            font-weight: 800;
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-line {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1.5rem 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            border-left: 4px solid #3498db;
            text-align: center;
            font-size: 1.1em;
            color: #2c3e50;
        }
        .results-header-sidebar {
            font-size: 1.4em;
            font-weight: 700;
            color: #ecf0f1;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        .selected-char-sidebar {
            font-size: 4em;
            text-align: center;
            color: #e74c3c;
            margin: 30px 0;
            font-weight: bold;
            text-shadow: 2px 2px 8px rgba(0,0,0,0.2);
            padding: 20px;
            background: white;
            border-radius: 15px;
        }
        .preview-card {
            background: white;
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            margin: 2rem 0;
            border: 2px solid #e74c3c;
        }
        .preview-char {
            font-size: 5em;
            text-align: center;
            color: #e74c3c;
            margin: 20px 0;
            font-weight: bold;
        }
        .preview-details {
            text-align: center;
            font-size: 1.1em;
            color: #2c3e50;
            line-height: 2;
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 10px;
        }
        .char-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            border-left: 4px solid #3498db;
        }
        .char-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        .comp-grid .stButton button {
            font-size: 2em !important;
            height: 80px !important;
            background: white !important;
            border: 2px solid #e0e0e0 !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
        }
        .comp-grid .stButton button:hover {
            background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%) !important;
            border-color: #e74c3c !important;
            transform: scale(1.05);
        }
        .compounds-box {
            padding: 1.5rem;
            background: linear-gradient(135deg, #f1f8e9 0%, #dcedc8 100%);
            border-radius: 12px;
            margin-top: 1rem;
            border-left: 4px solid #8bc34a;
        }
        .compounds-title {
            font-weight: 700;
            color: #558b2f;
            font-size: 1.1em;
        }
        .compounds-list {
            font-size: 1.3em;
            color: #33691e;
            line-height: 2;
        }
        .info-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            padding: 1.5rem;
            border-radius: 12px;
            border-left: 4px solid #2196f3;
            color: #1565c0;
        }
    </style>
    """
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
    st.error("⚠️ Failed to load 'enhanced_component_map_with_etymology.json'.")

# Improved clean_field – handles lists properly
def clean_field(field):
    if isinstance(field, list):
        if not field:
            return "—"
        return " · ".join(str(x) for x in field if x and str(x).strip())
    return str(field) if field else "—"

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
    if details and details != "—":
        return f"{hint}; {details}"
    return hint

def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    if not d or '?' in d:
        return "—"
    return d

def get_all_components(char, max_depth=5, depth=0, seen=None):
    if seen is None:
        seen = set()
    if char in seen or depth > max_depth or len(char) != 1:
        return set()
    seen.add(char)
    s = set()
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    if d:
        for c in d:
            if c in IDC_CHARS or c == '?' or len(c) != 1:
                continue
            s.add(c)
            s.update(get_all_components(c, max_depth, depth+1, seen.copy()))
    return s

# Session state defaults
defaults = {
    "selected_comp": "", "stroke_count": 0, "radical": "none", "component_idc": "none",
    "display_mode": "Single Character", "text_input_comp": "", "page": 1,
    "text_input_warning": None, "show_inputs": True, "last_valid_selected_comp": "",
    "preview_comp": None, "preview_active": False
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

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
        st.session_state.text_input_warning = "⚠️ Please enter exactly one character"
        return
    if v in component_map:
        st.session_state.selected_comp = v
        st.session_state.last_valid_selected_comp = v
        st.session_state.text_input_comp = v
        st.session_state.text_input_warning = None
        st.session_state.show_inputs = False
        st.session_state.preview_active = False
    else:
        st.session_state.text_input_warning = "❌ Character not found"

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
    for k in ["stroke_count", "radical", "component_idc", "page", "show_inputs",
              "preview_active", "preview_comp", "text_input_warning"]:
        st.session_state[k] = defaults[k]

def render_preview(c):
    meta = component_map.get(c, {}).get("meta", {})
    stroke_info = get_stroke_count(c)
    stroke_text = f"{stroke_info} strokes" if stroke_info else "unknown"
    f = {
        "📌 Pinyin": clean_field(meta.get("pinyin", "—")),
        "✍️ Strokes": stroke_text,
        "🔰 Radical": clean_field(meta.get("radical", "—")),
        "🧩 Decomposition": format_decomposition(c),
        "📖 Definition": clean_field(meta.get("definition", "—")),
        "📜 Etymology": get_etymology_text(meta),
    }
    details = "<br>".join(f"<strong>{k}:</strong> {v}" for k, v in f.items())
    st.markdown(f"""
        <div class='preview-card'>
            <div class='preview-char'>{c}</div>
            <div class='preview-details'>{details}</div>
        </div>
    """, unsafe_allow_html=True)

def main():
    if not component_map:
        st.stop()

    apply_dynamic_css()

    st.markdown("""
        <div class='app-header'>
            <div class='app-title'>🈑 Radix</div>
            <div style='font-size:1.2em; color:#7f8c8d; margin-top:0.5rem;'>Chinese Character Component Explorer</div>
        </div>
    """, unsafe_allow_html=True)

    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("<h1 style='text-align:center; color:#ecf0f1; margin-bottom:30px; font-size:2.5em;'>🈑 Radix</h1>", unsafe_allow_html=True)

        if st.session_state.show_inputs:
            # Browsing mode
            st.markdown("### 🔍 Filters")

            stroke_set = {s for s in (get_stroke_count(c) for c in component_map) if isinstance(s, int)}
            stroke_opts = [0] + sorted(stroke_set)
            current_stroke = st.session_state.stroke_count if st.session_state.stroke_count in stroke_opts else 0
            st.selectbox("✍️ Stroke Count", options=stroke_opts, index=stroke_opts.index(current_stroke),
                         format_func=lambda x: "Any" if x == 0 else f"{x} strokes",
                         key="w_stroke", on_change=sync_stroke)

            rad_set = {component_map.get(c, {}).get("meta", {}).get("radical", "") for c in component_map if component_map.get(c, {}).get("meta", {}).get("radical")}
            rad_opts = ["none"] + sorted(rad_set)
            st.selectbox("🔰 Radical", options=rad_opts, index=rad_opts.index(st.session_state.radical),
                         format_func=lambda x: "Any" if x == "none" else x,
                         key="w_radical", on_change=sync_radical)

            idc_set = {d[0] for d in (component_map.get(c, {}).get("meta", {}).get("decomposition", "") for c in component_map) if d and d[0] in IDC_CHARS}
            idc_opts = ["none"] + sorted(idc_set)
            st.selectbox("🧩 Structure (IDC)", options=idc_opts, index=idc_opts.index(st.session_state.component_idc),
                         format_func=lambda x: "Any" if x == "none" else x,
                         key="w_idc", on_change=sync_idc)

            st.markdown("---")
            st.markdown("### 🎯 Quick Jump")
            if st.session_state.text_input_warning:
                st.warning(st.session_state.text_input_warning)
            st.text_input("Enter a character", value=st.session_state.text_input_comp,
                          key="w_text", on_change=sync_text, placeholder="e.g. 水, 火, 木")

        else:
            # Results mode – your original functionality restored
            st.markdown("### ⚙️ Actions")
            st.button("◀️ Back to Browse", on_click=back, use_container_width=True, type="primary")
            st.button("🔄 Reset Filters", on_click=reset, use_container_width=True)

            st.markdown("---")
            st.markdown(f"<div class='selected-char-sidebar'>{st.session_state.selected_comp}</div>", unsafe_allow_html=True)

            related = component_map[st.session_state.selected_comp].get("related_characters", [])
            chars = [c for c in related if len(c) == 1]

            # Safe extraction of n from display_mode
            if st.session_state.display_mode == "Single Character":
                n = 0
            else:
                n = int(st.session_state.display_mode.split("-")[0])

            compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w) == n] for c in chars} if n else {c: [] for c in chars}
            valid_chars = [c for c in chars if n == 0 or compounds[c]]

            st.markdown(f"<div class='results-header-sidebar'>🧬 Found {len(valid_chars)} Results</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 📋 Output Type")
            modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
            mode_icons = {"Single Character": "🔤", "2-Character Phrases": "📝", "3-Character Phrases": "📄", "4-Character Phrases": "📃"}
            st.radio("", options=modes, index=modes.index(st.session_state.display_mode),
                     format_func=lambda x: f"{mode_icons[x]} {x}",
                     key="w_display", on_change=sync_display)

    # === MAIN AREA ===
    if st.session_state.show_inputs:
        # Browsing + preview
        filter_parts = []
        if st.session_state.stroke_count > 0: filter_parts.append(f"**{st.session_state.stroke_count} strokes**")
        if st.session_state.radical != "none": filter_parts.append(f"**Radical:** {st.session_state.radical}")
        if st.session_state.component_idc != "none": filter_parts.append(f"**Structure:** {st.session_state.component_idc}")
        filter_summary = " · ".join(filter_parts) if filter_parts else "**No filters applied**"
        instruction = "💡 **Click TWICE on a tile** to explore built characters" if st.session_state.preview_active else "💡 **Click a tile** to preview"

        st.markdown(f"""
            <div class='status-line'>
                <div>🔎 Active Filters: {filter_summary}</div>
                <div style='margin-top:8px; font-style:italic;'>{instruction}</div>
            </div>
        """, unsafe_allow_html=True)

        filtered = [c for c in component_map if
                    (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
                    (st.session_state.radical == "none" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
                    (st.session_state.component_idc == "none" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))]
        extra = get_all_components(st.session_state.selected_comp, max_depth=5)
        filtered = list(set(filtered) | (extra & set(component_map)))
        sorted_comps = sorted(filtered, key=lambda c: get_stroke_count(c) or 999)

        if not sorted_comps:
            st.markdown("<div class='info-box'>ℹ️ No components match your filters. Try loosening them!</div>", unsafe_allow_html=True)
            return

        if st.session_state.preview_active and st.session_state.preview_comp:
            render_preview(st.session_state.preview_comp)

        PAGE_SIZE = 120
        GRID_COLS = 15
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        col_prev, col_info, col_next = st.columns([1, 3, 1])
        with col_prev:
            if st.button("◀️ Previous", disabled=st.session_state.page <= 1):
                st.session_state.page -= 1
                st.rerun()
        with col_info:
            start = (st.session_state.page - 1) * PAGE_SIZE + 1
            end = min(st.session_state.page * PAGE_SIZE, total)
            st.markdown(f"<div style='text-align:center; padding:12px 0; font-weight:600;'>Page {st.session_state.page}/{max_page} — Showing {start}–{end} of {total}</div>", unsafe_allow_html=True)
        with col_next:
            if st.button("Next ▶️", disabled=st.session_state.page >= max_page):
                st.session_state.page += 1
                st.rerun()

        page = sorted_comps[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]
        st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
        cols = st.columns(GRID_COLS)
        for i, ch in enumerate(page):
            with cols[i % GRID_COLS]:
                is_preview = st.session_state.preview_active and st.session_state.preview_comp == ch
                st.button(ch, key=f"b_{ch}_{st.session_state.page}", use_container_width=True,
                          type="primary" if is_preview else "secondary",
                          on_click=tile_click, args=(ch,))
        st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Results view – full original functionality
        related = component_map[st.session_state.selected_comp].get("related_characters", [])
        chars = [c for c in related if len(c) == 1]

        if st.session_state.display_mode == "Single Character":
            n = 0
        else:
            n = int(st.session_state.display_mode.split("-")[0])

        compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w) == n] for c in chars} if n else {c: [] for c in chars}
        chars = [c for c in chars if n == 0 or compounds[c]]

        if not chars:
            st.markdown("<div class='info-box'>ℹ️ No results for this component and selected output type.</div>", unsafe_allow_html=True)
            return

        for c in sorted(chars, key=lambda x: get_stroke_count(x) or 999):
            meta = component_map.get(c, {}).get("meta", {})
            stroke_info = get_stroke_count(c)
            stroke_text = f"{stroke_info} strokes" if stroke_info else "unknown"

            fd = {
                "📌 Pinyin": clean_field(meta.get("pinyin", "—")),
                "✍️ Strokes": stroke_text,
                "🔰 Radical": clean_field(meta.get("radical", "—")),
                "🧩 Decomposition": format_decomposition(c),
                "📖 Definition": clean_field(meta.get("definition", "—")),
                "📜 Etymology": get_etymology_text(meta),
            }
            details = " · ".join(f"<strong>{k}:</strong> {v}" for k, v in fd.items())

            col_char, col_info = st.columns([1, 9])
            with col_char:
                st.button(c, key=f"res_{c}", on_click=tile_click, args=(c,), use_container_width=True, type="primary")
            with col_info:
                st.markdown(f"<div class='char-card'>{details}</div>", unsafe_allow_html=True)

            if compounds.get(c):
                comp_list = " · ".join(sorted(compounds[c]))
                st.markdown(f"""
                    <div class='compounds-box'>
                        <div class='compounds-title'>📚 {st.session_state.display_mode}:</div>
                        <div class='compounds-list'>{comp_list}</div>
                    </div>
                """, unsafe_allow_html=True)

        if chars and n:
            with st.expander("📤 Export All Compounds"):
                all_compounds = "\n".join(w for c in chars for w in compounds[c])
                st.text_area("Copy the list below:", all_compounds, height=200)
                st.download_button(
                    label="⬇️ Download as Text File",
                    data=all_compounds,
                    file_name=f"compounds_{st.session_state.selected_comp}_{n}char.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
