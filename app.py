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
        /* Global Styles */
        .main {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }
        
        /* Sidebar Styling */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #2c3e50 0%, #34495e 100%);
        }
        
        [data-testid="stSidebar"] .stMarkdown, 
        [data-testid="stSidebar"] label {
            color: #ecf0f1 !important;
        }
        
        /* Header Styles */
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
            margin-bottom: 0.5rem;
        }
        
        .app-subtitle {
            font-size: 1.2em;
            color: #7f8c8d;
            font-weight: 300;
        }
        
        /* Status Line */
        .status-line {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1.5rem 0;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            border-left: 4px solid #3498db;
        }
        
        .status-filters {
            font-size: 1.1em;
            color: #2c3e50;
            font-weight: 600;
            margin-bottom: 0.5rem;
        }
        
        .status-instruction {
            font-size: 0.95em;
            color: #7f8c8d;
            font-style: italic;
        }
        
        /* Sidebar Results Header */
        .results-header-sidebar {
            font-size: 1.3em;
            font-weight: 700;
            color: #ecf0f1;
            background: rgba(255,255,255,0.1);
            padding: 15px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: center;
            backdrop-filter: blur(10px);
        }
        
        /* Selected Character Display */
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
        
        /* Preview Card */
        .preview-card {
            background: white;
            padding: 2.5rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.12);
            margin: 2rem 0;
            border: 2px solid #e74c3c;
            animation: slideIn 0.3s ease-out;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .preview-char {
            font-size: 5em;
            text-align: center;
            color: #e74c3c;
            margin: 20px 0;
            font-weight: bold;
            text-shadow: 3px 3px 10px rgba(231, 76, 60, 0.3);
        }
        
        .preview-details {
            text-align: center;
            font-size: 1.1em;
            color: #2c3e50;
            line-height: 2;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 10px;
        }
        
        /* Character Card */
        .char-card {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            margin-bottom: 1rem;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            border-left: 4px solid #3498db;
        }
        
        .char-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }
        
        .char-card-header {
            display: flex;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .char-display {
            font-size: 3em;
            color: #e74c3c;
            margin-right: 1rem;
            font-weight: bold;
        }
        
        .char-details {
            font-size: 0.95em;
            color: #555;
            line-height: 1.8;
        }
        
        /* Component Grid */
        .comp-grid .stButton button {
            font-size: 2em !important;
            height: 80px !important;
            background: white !important;
            border: 2px solid #e0e0e0 !important;
            border-radius: 12px !important;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08) !important;
            transition: all 0.2s ease !important;
            font-weight: 600 !important;
        }
        
        .comp-grid .stButton button:hover {
            background: linear-gradient(135deg, #fff5f5 0%, #ffe5e5 100%) !important;
            border-color: #e74c3c !important;
            transform: scale(1.05);
            box-shadow: 0 4px 16px rgba(231, 76, 60, 0.3) !important;
        }
        
        /* Pagination */
        .pagination-container {
            background: white;
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.08);
            margin: 1.5rem 0;
        }
        
        .pagination-info {
            text-align: center;
            padding: 10px 0;
            font-size: 1.2em;
            color: #2c3e50;
            font-weight: 600;
        }
        
        /* Compounds Display */
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
            margin-bottom: 0.5rem;
            font-size: 1.1em;
        }
        
        .compounds-list {
            font-size: 1.3em;
            color: #33691e;
            line-height: 2;
        }
        
        /* Filter Section */
        .filter-section {
            background: rgba(255,255,255,0.05);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            backdrop-filter: blur(10px);
        }
        
        .filter-title {
            font-size: 1.4em;
            font-weight: 700;
            color: #ecf0f1;
            margin-bottom: 1rem;
            text-align: center;
        }
        
        /* Info Box */
        .info-box {
            background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border-left: 4px solid #2196f3;
            color: #1565c0;
            font-size: 1.05em;
        }
        
        /* Warning Box */
        .warning-box {
            background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%);
            padding: 1rem;
            border-radius: 10px;
            border-left: 4px solid #ff9800;
            color: #e65100;
            font-weight: 600;
            margin: 1rem 0;
        }
        
        /* Action Buttons */
        .stButton button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            transition: all 0.3s ease !important;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }
        
        ::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%);
            border-radius: 10px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: #c0392b;
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
    st.error("⚠️ Failed to load data. Please ensure 'enhanced_component_map_with_etymology.json' exists.")

def clean_field(field):
    """Clean and format field data"""
    return field,[object Object], if isinstance(field, list) and field else field or "—"
    
def get_stroke_count(char):
    """Get stroke count for a character"""
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
    """Extract and format etymology information"""
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", "No hint"))
    details = clean_field(etymology.get("details", ""))
    return f"{hint}{'; ' + details if details and details != '—' else ''}"

def format_decomposition(char):
    """Format decomposition string"""
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "—" if not d or '?' in d else d

def get_all_components(char, max_depth=5, depth=0, seen=None):
    """Recursively get all components of a character"""
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

# State initialization
defaults = {
    "selected_comp": "", 
    "stroke_count": 0, 
    "radical": "none", 
    "component_idc": "none",
    "display_mode": "Single Character", 
    "text_input_comp": "", 
    "page": 1, 
    "text_input_warning": None,
    "show_inputs": True, 
    "last_valid_selected_comp": "", 
    "preview_comp": None, 
    "preview_active": False
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
        st.session_state.text_input_warning = "❌ Character not found in database"

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
    st.session_state.text_input_warning = None

def render_preview(c):
    """Render character preview card"""
    meta = component_map.get(c, {}).get("meta", {})
    f = {
        "📌 Pinyin": clean_field(meta.get("pinyin", "—")),
        "✍️ Strokes": f"{get_stroke_count(c)} strokes" if get_stroke_count(c) else "unknown",
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

    # === HEADER ===
    st.markdown("""
        <div class='app-header'>
            <div class='app-title'>🈑 Radix</div>
            <div class='app-subtitle'>Chinese Character Component Explorer</div>
        </div>
    """, unsafe_allow_html=True)

    # === SIDEBAR ===
    with st.sidebar:
        st.markdown("<h1 style='text-align:center; color:#ecf0f1; margin-bottom:30px; font-size:2.5em;'>🈑 Radix</h1>", unsafe_allow_html=True)

        if st.session_state.show_inputs:
            # Browsing mode
            st.markdown("<div class='filter-section'>", unsafe_allow_html=True)
            st.markdown("<div class='filter-title'>🔍 Filters</div>", unsafe_allow_html=True)

            stroke_set = {s for s in (get_stroke_count(c) for c in component_map) if isinstance(s, int)}
            stroke_opts = ,[object Object], + sorted(stroke_set)
            current = st.session_state.stroke_count if isinstance(st.session_state.stroke_count, int) and st.session_state.stroke_count in stroke_opts else 0
            st.selectbox("✍️ Stroke Count", options=stroke_opts, index=stroke_opts.index(current),
                         format_func=lambda x: "Any" if x == 0 else f"{x} strokes", key="w_stroke", on_change=sync_stroke)

            rad_set = {component_map.get(c, {}).get("meta", {}).get("radical", "") for c in component_map if component_map.get(c, {}).get("meta", {}).get("radical")}
            rad_opts = ["none"] + sorted(rad_set)
            st.selectbox("🔰 Radical", options=rad_opts, index=rad_opts.index(st.session_state.radical),
                        format_func=lambda x: "Any" if x == "none" else x, key="w_radical", on_change=sync_radical)

            idc_set = {d,[object Object], for d in (component_map.get(c, {}).get("meta", {}).get("decomposition", "") for c in component_map) if d and d,[object Object], in IDC_CHARS}
            idc_opts = ["none"] + sorted(idc_set)
            st.selectbox("🧩 Structure (IDC)", options=idc_opts, index=idc_opts.index(st.session_state.component_idc),
                        format_func=lambda x: "Any" if x == "none" else x, key="w_idc", on_change=sync_idc)
            
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("<div style='color:#ecf0f1; font-weight:600; margin-bottom:10px;'>🎯 Quick Jump</div>", unsafe_allow_html=True)
            
            if st.session_state.text_input_warning:
                st.markdown(f"<div class='warning-box'>{st.session_state.text_input_warning}</div>", unsafe_allow_html=True)
            
            st.text_input("Enter a character", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text, placeholder="e.g. 水, 火, 木")

        else:
            # Results mode
            st.markdown("<div style='color:#ecf0f1; font-weight:700; font-size:1.3em; margin-bottom:15px;'>⚙️ Actions</div>", unsafe_allow_html=True)
            st.button("◀️ Back to Browse", on_click=back, use_container_width=True, type="primary")
            st.button("🔄 Reset All Filters", on_click=reset, use_container_width=True)

            st.markdown("---")
            
            # Selected character display
            st.markdown(f"<div class='selected-char-sidebar'>{st.session_state.selected_comp}</div>", unsafe_allow_html=True)

            # Results count
            related = component_map[st.session_state.selected_comp].get("related_characters", [])
            chars = [c for c in related if len(c)==1]
            n = int(st.session_state.display_mode,[object Object],) if st.session_state.display_mode != "Single Character" else 0
            compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars} if n else {c:[] for c in chars}
            valid_chars = [c for c in chars if n==0 or compounds[c]]
            st.markdown(f"<div class='results-header-sidebar'>🧬 Found {len(valid_chars)} Results</div>", unsafe_allow_html=True)

            # Output Type
            st.markdown("---")
            st.markdown("<div style='color:#ecf0f1; font-weight:700; font-size:1.3em; margin-bottom:15px;'>📋 Output Type</div>", unsafe_allow_html=True)
            modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
            mode_icons = {"Single Character": "🔤", "2-Character Phrases": "📝", "3-Character Phrases": "📄", "4-Character Phrases": "📃"}
            st.radio("", options=modes, index=modes.index(st.session_state.display_mode),
                    format_func=lambda x: f"{mode_icons[x]} {x}", key="w_display", on_change=sync_display)

    # === MAIN CONTENT ===
    if st.session_state.show_inputs:
        # Browsing mode
        filter_parts = []
        if st.session_state.stroke_count > 0:
            filter_parts.append(f"**{st.session_state.stroke_count} strokes**")
        if st.session_state.radical != "none":
            filter_parts.append(f"**Radical:** {st.session_state.radical}")
        if st.session_state.component_idc != "none":
            filter_parts.append(f"**Structure:** {st.session_state.component_idc}")

        filter_summary = " · ".join(filter_parts) if filter_parts else "**No filters applied**"
        instruction = "💡 **Click TWICE on a tile** to explore characters built with this component" if st.session_state.preview_active else "💡 **Click a tile** to preview details"
        
        st.markdown(f"""
            <div class='status-line'>
                <div class='status-filters'>🔎 Active Filters: {filter_summary}</div>
                <div class='status-instruction'>{instruction}</div>
            </div>
        """, unsafe_allow_html=True)

        filtered = [c for c in component_map if
            (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
            (st.session_state.radical == "none" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
            (st.session_state.component_idc == "none" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
        ]
        extra = get_all_components(st.session_state.selected_comp, max_depth=5)
        filtered = list(set(filtered) | (extra & set(component_map)))
        sorted_comps = sorted(filtered, key=lambda c: get_stroke_count(c) or 999)

        if not sorted_comps:
            st.markdown("<div class='info-box'>ℹ️ No components match your current filters. Try adjusting them!</div>", unsafe_allow_html=True)
            return

        if st.session_state.preview_active and st.session_state.preview_comp:
            render_preview(st.session_state.preview_comp)

        PAGE_SIZE = 120
        GRID_COLS = 15
        total = len(sorted_comps)
        max_page = max(1, math.ceil(total / PAGE_SIZE))
        st.session_state.page = max(1, min(st.session_state.page, max_page))

        st.markdown("<div class='pagination-container'>", unsafe_allow_html=True)
        p1, p2, p3 = st.columns([1, 3, 1])
        with p1:
            if st.button("◀️ Previous", disabled=st.session_state.page<=1, use_container_width=True): 
                st.session_state.page -= 1
                st.rerun()
        with p2:
            start = (st.session_state.page-1)*PAGE_SIZE + 1
            end = min(st.session_state.page*PAGE_SIZE, total)
            st.markdown(f"<div class='pagination-info'>Page {st.session_state.page} of {max_page} · Showing {start}–{end} of {total}</div>", unsafe_allow_html=True)
        with p3:
            if st.button("Next ▶️", disabled=st.session_state.page>=max_page, use_container_width=True): 
                st.session_state.page += 1
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

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
        chars = [c for c in related if len(c)==1]
        n = int(st.session_state.display_mode,[object Object],) if st.session_state.display_mode != "Single Character" else 0
        compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars} if n else {c:[] for c in chars}
        chars = [c for c in chars if n==0 or compounds[c]]

        if not chars:
            st.markdown("<div class='info-box'>ℹ️ No results found for this component and output type combination.</div>", unsafe_allow_html=True)
            return

        for c in sorted(chars, key=lambda x: get_stroke_count(x) or 999):
            meta = component_map.get(c, {}).get("meta", {})
            fd = {
                "📌 Pinyin": clean_field(meta.get("pinyin", "—")),
                "✍️ Strokes": f"{get_stroke_count(c)} strokes" if get_stroke_count(c) else "unknown",
                "🔰 Radical": clean_field(meta.get("radical", "—")),
                "🧩 Decomposition": format_decomposition(c),
                "📖 Definition": clean_field(meta.get("definition", "—")),
                "📜 Etymology": get_etymology_text(meta),
            }
            
            col1, col2 = st.columns([1, 9])
            with col1:
                st.button(c, key=f"res_{c}", on_click=tile_click, args=(c,), use_container_width=True, type="primary")
            with col2:
                det = " · ".join(f"<strong>{k}:</strong> {v}" for k, v in fd.items())
                st.markdown(f"<div class='char-card'><div class='char-details'>{det}</div></div>", unsafe_allow_html=True)
            
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
                    file_name=f"compounds_{st.session_state.selected_comp}_{n}chars.txt",
                    mime="text/plain"
                )

if __name__ == "__main__":
    main()
