import json
import math
import html
import sqlite3
import unicodedata
import streamlit as st
from streamlit.components.v1 import html as st_html

# --- Optional: OpenCC for Traditional/Simplified Conversion ---
try:
    from opencc import OpenCC
    cc_t2s = OpenCC("t2s")
    cc_s2t = OpenCC("s2t")
except ImportError:
    cc_t2s = None
    cc_s2t = None

st.set_page_config(layout="wide", page_title="Radix", page_icon="🈑")

IDC_CHARS = {"⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"}
SCRIPT_FILTERS = ["Any", "Simplified", "Traditional"]

# --- DATA PIPELINE OPTIMIZATIONS ---

@st.cache_resource
def get_zipf_frequency():
    try:
        from wordfreq import zipf_frequency
        return zipf_frequency
    except Exception:
        return None

ZIPF = get_zipf_frequency()

def zipf_commonness_raw(ch: str) -> float:
    """Core frequency logic used during pre-calculation."""
    if not ch or ZIPF is None:
        return float("-inf")
    try:
        z = float(ZIPF(ch, "zh"))
    except:
        z = float("-inf")
    
    if z <= 0:
        if cc_s2t:
            try: z = max(z, float(ZIPF(cc_s2t.convert(ch), "zh")))
            except: pass
        if cc_t2s:
            try: z = max(z, float(ZIPF(cc_t2s.convert(ch), "zh")))
            except: pass
    return z

@st.cache_data
def load_and_augment_map():
    """
    STAGE 1 & 2: Load and Pre-calculate metadata.
    Reduces O(N) operations during render to O(1) lookups.
    """
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}

    # Pre-calculate expensive metrics once per session
    for char, info in data.items():
        meta = info.get("meta", {})
        # Pre-calc Usage
        rel = info.get("related_characters", [])
        info['usage_count'] = len({c for c in rel if isinstance(c, str) and len(c) == 1})
        # Pre-calc Commonness
        info['zipf_val'] = zipf_commonness_raw(char)
        # Clean strokes
        s = meta.get("strokes")
        try:
            if isinstance(s, (int, float)): info['stroke_count'] = int(s)
            elif isinstance(s, str) and s.isdigit(): info['stroke_count'] = int(s)
            else: info['stroke_count'] = None
        except:
            info['stroke_count'] = None
            
    return data

@st.cache_data
def get_component_stats(_component_map):
    """
    STAGE 3: Statistical Indexing.
    Indexes radicals and structures for the sidebar.
    """
    r_counts = {}
    s_counts = {}
    idc_counts = {}
    used_comps = set()
    
    for c, data in _component_map.items():
        # Radical Indexing
        r = data.get("meta", {}).get("radical")
        if r: r_counts[r] = r_counts.get(r, 0) + 1
        
        # Stroke Indexing
        s = data.get('stroke_count')
        if s: s_counts[s] = s_counts.get(s, 0) + 1
        
        # IDC / Structure Indexing
        d = data.get("meta", {}).get("decomposition", "")
        if d:
            if d[0] in IDC_CHARS:
                idc = d[0]
                idc_counts[idc] = idc_counts.get(idc, 0) + 1
            clean_d = "".join([ch for ch in d if ch not in IDC_CHARS])
            for ch in clean_d:
                used_comps.add(ch)
                
    # Group radicals by stroke count for the UI
    r_groups = {}
    for r in r_counts:
        # Get stroke count of the radical itself
        rad_data = _component_map.get(r, {})
        gs = rad_data.get('stroke_count') or 999
        r_groups.setdefault(gs, []).append(r)
    
    for gs in r_groups:
        r_groups[gs].sort()
        
    return {
        "rad_groups": r_groups,
        "rad_counts": r_counts,
        "stroke_counts": s_counts,
        "idc_counts": idc_counts,
        "used_components": used_comps
    }

# --- Initialization ---
component_map = load_and_augment_map()
stats_cache = get_component_stats(component_map) if component_map else {}

# --- CSS & Database Logic ---

def apply_dynamic_css():
    css = """
    <style>
    .results-header-sidebar {font-size: 1.4em; font-weight: bold; color: #2c3e50; margin: 20px 0 10px 0; text-align: center;}
    .char-card {background: white; padding: 20px; border-radius: 10px; margin-bottom: 0px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);}
    .meta-row {font-size: 0.95em; color: #555; margin-bottom: 8px; display: flex; align-items: center; flex-wrap: wrap; gap: 10px;}
    .meta-pinyin {font-weight: bold; font-size: 2.2em; color: #d35400;}
    .meta-tag {background: #f1f3f5; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; color: #495057;}
    .meta-tag-trad {background: #fff8e1; color: #856404; border: 1px solid #ffeeba;}
    .meta-tag-simp {background: #d1e7dd; color: #0f5132; border: 1px solid #badbcc;}
    .def-row {font-size: 1.1em; line-height: 1.4; color: #2c3e50; margin-bottom: 8px;}
    .ety-row {font-size: 0.9em; color: #666; font-style: italic; border-top: 1px solid #eee; padding-top: 8px; margin-top: 4px;}
    .comp-grid .stButton button {font-size: 2em; height: 80px; background: white; border: 1px solid #e0e0e0; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); padding: 0; line-height: 80px;}
    .comp-grid .stButton button:hover {background: #fff5f5; border-color: #f2c6c6; color: #c0392b;}
    div[data-testid="column"] .stButton button { width: 100%; border-radius: 8px; transition: all 0.2s ease; }
    .char-btn-wrap button { font-size: 3.5em !important; font-weight: bold !important; background: white !important; border: 2px solid #e0e0e0 !important; padding: 5px !important; min-height: 80px !important; }
    .pen-btn-wrap button { font-size: 1.5em !important; border: 1px solid #eee !important; background: #f8f9fa !important; margin-top: 5px !important; height: 40px !important; line-height: 1 !important; color: #555 !important; }
    .char-static-box { font-size: 3.5em; font-weight: bold; background: #fdfdfd; color: #999; border: 2px solid #eee; border-radius: 12px; padding: 5px; min-height: 80px; display: flex; align-items: center; justify-content: center; width: 100%; cursor: default; }
    .status-line { font-size: 1.1em; font-weight: 600; color: #0f5132; background-color: #d1e7dd; border: 1px solid #badbcc; padding: 15px; border-radius: 8px; margin: 20px 0 30px 0; }
    .status-tag { background-color: #f1f3f5; color: #2c3e50; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.9em; border: 1px solid #e9ecef; display: inline-flex; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .map-path { font-family: monospace; color: #155724; margin-left: 10px; }
    .preview-count-line {font-size: 1.3em; text-align: center; color: #2c3e50; margin: 20px 0 25px 0;}
    .preview-count-line .char {font-size: 1.4em; font-weight: bold; color: #e74c3c;}
    .jump-footer {margin-top: 40px; padding: 20px; background: #f8f9fa; border-top: 1px solid #e0e0e0; text-align: center;}
    .stroke-header {font-size: 0.85em; color: #888; border-bottom: 1px solid #eee; margin: 10px 0 5px 0; padding-bottom: 2px;}
    .compound-item { display: flex; align-items: baseline; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #e0e0e0; }
    .cp-word { font-weight: bold; font-size: 1.1em; color: #2c3e50; min-width: 80px; margin-right: 10px; }
    .cp-pinyin { color: #d35400; font-family: monospace; margin-right: 10px; font-weight: 500; font-size: 1.5em;}
    .cp-mean { color: #333; font-size: 0.95em; flex: 1; }
    .splash-wrap {max-width: 1100px; margin: 0 auto; padding: 34px 10px 10px 10px;}
    .splash-card {background: white; border: 1px solid #eee; border-radius: 18px; padding: 34px; box-shadow: 0 6px 22px rgba(0,0,0,0.06);}
    .splash-title {font-size: 2.3em; font-weight: 850; line-height: 1.12; color:#111;}
    .splash-sub {margin-top: 10px; font-size: 1.15em; color:#444; line-height: 1.5;}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_resource
def get_db_connection():
    try:
        conn = sqlite3.connect("phrases.db", check_same_thread=False)
        return conn
    except Exception:
        return None

def batch_get_phrase_details(words, conn):
    if not conn or not words: return {}
    try:
        placeholders = ",".join(["?"] * len(words))
        cursor = conn.cursor()
        query = f"SELECT word, pinyin, meanings FROM phrases WHERE word IN ({placeholders})"
        cursor.execute(query, list(words))
        results = cursor.fetchall()
        return {row[0]: {"pinyin": row[1], "meanings": row[2]} for row in results}
    except Exception: return {}

# --- Logic Helpers (Optimized for O(1) Lookups) ---

def get_stroke_count(char):
    return component_map.get(char, {}).get("stroke_count")

def component_usage_count(comp: str) -> int:
    return component_map.get(comp, {}).get("usage_count", 0)

def sort_key_usage_then_zipf(ch: str):
    info = component_map.get(ch, {})
    use = info.get('usage_count', 0)
    z = info.get('zipf_val', float("-inf"))
    strokes = info.get('stroke_count') or 999
    group = 0 if use >= 3 else 1
    return (group, -use, -z, strokes, ch) if group == 0 else (group, -z, strokes, ch)

def apply_script_filter(chars: list[str]) -> list[str]:
    f = st.session_state.get("script_filter", "Any")
    if f == "Any": return chars
    if f == "Simplified":
        return [c for c in chars if (not cc_t2s) or (cc_t2s.convert(c) == c)]
    return [c for c in chars if (not cc_s2t) or (cc_s2t.convert(c) == c)]

def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "–"

def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", ""))
    if not hint or hint.lower() == "no hint": hint = ""
    details = clean_field(etymology.get("details", ""))
    if details == "–": details = ""
    parts = [p for p in [hint, details] if p]
    return "; ".join(parts) if parts else None

def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "–" if not d or "?" in d else d

def normalize_single_hanzi(raw: str) -> str:
    if not raw: return ""
    s = unicodedata.normalize("NFC", raw)
    chars = [ch for ch in s.strip() if (not ch.isspace()) and unicodedata.category(ch) != "Cf"]
    return chars[0] if len(chars) == 1 else ""

def resolve_to_known_variant(ch: str) -> str:
    if not ch: return ""
    if ch in component_map: return ch
    if cc_s2t and cc_s2t.convert(ch) in component_map: return cc_s2t.convert(ch)
    if cc_t2s and cc_t2s.convert(ch) in component_map: return cc_t2s.convert(ch)
    return ""

def reset_script_filter_to_any():
    st.session_state.script_filter = "Any"
    st.session_state.pop("w_script_filter", None)

# --- State Management ---
defaults = {
    "onboarding_done": False, "selected_comp": "", "stroke_range": (3, 8),
    "radical": "none", "component_idc": "none", "display_mode": "Single Character",
    "text_input_comp": "", "page": 1, "text_input_warning": None, "show_inputs": True,
    "last_valid_selected_comp": "", "preview_comp": None, "stroke_view_active": False,
    "stroke_view_char": "", "script_filter": "Any", "component_only": True,
    "favourites_list": [], "fav_cursor": 0, "history": [],
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# --- Callbacks ---
def sync_stroke_range():
    st.session_state.stroke_range = st.session_state.w_stroke_range
    st.session_state.page = 1

def sync_idc():
    st.session_state.component_idc = st.session_state.w_idc
    st.session_state.page = 1

def sync_component_only():
    st.session_state.component_only = st.session_state.w_component_only
    st.session_state.page = 1

def sync_script_filter():
    st.session_state.script_filter = st.session_state.w_script_filter

def sync_text():
    raw = st.session_state.get("w_text", "")
    v = normalize_single_hanzi(raw)
    if not v:
        st.session_state.text_input_warning = "One character only"
        return
    resolved = resolve_to_known_variant(v)
    if not resolved:
        st.session_state.text_input_warning = "Not found"
        return
    reset_script_filter_to_any()
    st.session_state.history = []
    st.session_state.selected_comp = resolved
    st.session_state.last_valid_selected_comp = resolved
    st.session_state.text_input_comp = resolved
    st.session_state.text_input_warning = None
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.display_mode = "Single Character"

def sync_sidebar_text():
    raw = st.session_state.get("sb_search", "")
    v = normalize_single_hanzi(raw)
    if not v:
        st.toast("Please enter exactly one character.")
        return
    resolved = resolve_to_known_variant(v)
    if not resolved:
        st.toast("Character not found.")
        return
    reset_script_filter_to_any()
    st.session_state.history = []
    st.session_state.selected_comp = resolved
    st.session_state.last_valid_selected_comp = resolved
    st.session_state.text_input_comp = resolved
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.display_mode = "Single Character"

def tile_click(c):
    if st.session_state.show_inputs:
        if st.session_state.preview_comp == c:
            reset_script_filter_to_any()
            st.session_state.history = []
            st.session_state.selected_comp = c
            st.session_state.last_valid_selected_comp = c
            st.session_state.show_inputs = False
            st.session_state.preview_comp = None
            st.session_state.text_input_comp = c
            st.session_state.stroke_view_active = False
            st.session_state.display_mode = "Single Character"
        else:
            st.session_state.preview_comp = c

def list_tile_click(c):
    if st.session_state.preview_comp == c:
        reset_script_filter_to_any()
        if st.session_state.selected_comp:
            st.session_state.history.append(st.session_state.selected_comp)
        st.session_state.selected_comp = c
        st.session_state.last_valid_selected_comp = c
        st.session_state.show_inputs = False
        st.session_state.preview_comp = None
        st.session_state.text_input_comp = c
        st.session_state.stroke_view_active = False
        st.session_state.display_mode = "Single Character"
    else:
        st.session_state.preview_comp = c

def go_back():
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.text_input_comp = ""
    if st.session_state.history:
        prev = st.session_state.history.pop()
        reset_script_filter_to_any()
        st.session_state.selected_comp = prev
        st.session_state.last_valid_selected_comp = prev
        st.session_state.show_inputs = False
    else:
        st.session_state.show_inputs = True

def go_to_root():
    st.session_state.history = []
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.selected_comp = ""
    st.session_state.show_inputs = True
    reset_script_filter_to_any()

def end_stroke_view():
    st.session_state.stroke_view_active = False

# --- HTML Generators ---

def generate_clean_card_html(c, usage_count=None):
    if not c: return ""
    info = component_map.get(c, {})
    meta = info.get("meta", {})
    pinyin = clean_field(meta.get("pinyin", ""))
    strokes = info.get('stroke_count')
    radical = clean_field(meta.get("radical", ""))
    decomp = format_decomposition(c)
    definition = clean_field(meta.get("definition", ""))
    etymology = get_etymology_text(meta)

    meta_items = []
    if pinyin and pinyin != "–": meta_items.append(f"<span class='meta-pinyin'>{pinyin}</span>")
    if strokes: meta_items.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    if radical and radical != "–": meta_items.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    if decomp and decomp != "–": meta_items.append(f"<span class='meta-tag'>{decomp}</span>")
    if usage_count is not None and usage_count > 0: meta_items.append(f"<span class='meta-tag'>Used in {usage_count} chars</span>")

    if cc_t2s and cc_t2s.convert(c) != c:
        meta_items.append(f"<span class='meta-tag meta-tag-trad'>Trad. → {cc_t2s.convert(c)}</span>")
    if cc_s2t and cc_s2t.convert(c) != c:
        meta_items.append(f"<span class='meta-tag meta-tag-simp'>Simp. → {cc_s2t.convert(c)}</span>")

    meta_html = f"<div class='meta-row'>{''.join(meta_items)}</div>"
    def_html = f"<div class='def-row'>{definition}</div>" if definition and definition != "–" else ""
    ety_html = f"<div class='ety-row'>{etymology}</div>" if etymology else ""
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"

# --- Rendering Components (HanziWriter, Prompt, Splash) ---

def render_stroke_order_sidebar(char: str, size: int = 110):
    char = (char or "").strip()[:1]
    if not char: return
    pinyin = clean_field(component_map.get(char, {}).get("meta", {}).get("pinyin", ""))
    st_html(f"""
        <div style="display:flex; flex-direction:column; align-items:center; margin:20px 0;">
            <div style="text-align:center; font-size:2.5rem; font-weight:bold; color:#e67e22; margin-bottom:10px;">{pinyin}</div>
            <div id="sb-hw-{hash(char)}" style="width:{size}px; height:{size}px;"></div>
        </div>
        <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js"></script>
        <script>
            HanziWriter.create('sb-hw-{hash(char)}', '{char}', {{
                width: {size}, height: {size}, padding: 8, showOutline: true, strokeAnimationSpeed: 1.3
            }}).animateCharacter();
        </script>
    """, height=size + 80)

def render_stroke_order_view(char_input: str):
    primary_char = (char_input or "").strip()[:1]
    if not primary_char: return
    st.markdown("### Stroke Order & Phrases")
    
    # Mode selection
    modes = ["2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
    new_mode = st.radio("Display Mode", options=modes, horizontal=True, key="w_display_stroke_view")
    st.session_state.display_mode = new_mode

    # Visual container for writer
    st_html(f"""
        <div id="hw-target" style="width:280px;height:280px;border:1px solid #e0e0e0;margin:0 auto;"></div>
        <script src="https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js"></script>
        <script>
            HanziWriter.create('hw-target', '{primary_char}', {{
                width: 280, height: 280, padding: 10, showOutline: true
            }}).animateCharacter();
        </script>
    """, height=300)

    # Phrase List Logic
    n = int(new_mode[0])
    meta_compounds = component_map.get(primary_char, {}).get("meta", {}).get("compounds", [])
    relevant = [w for w in meta_compounds if isinstance(w, str) and len(w) == n]
    
    if relevant:
        db_conn = get_db_connection()
        phrases_map = batch_get_phrase_details(relevant, db_conn)
        items_html = []
        for word in sorted(relevant):
            entry = phrases_map.get(word, {})
            p, m = entry.get("pinyin", ""), entry.get("meanings", "")
            items_html.append(f"<div class='compound-item'><span class='cp-word'>{word}</span><span class='cp-pinyin'>{p}</span><span class='cp-mean'>{m}</span></div>")
        
        st.markdown(f"<div style='padding:15px; background:#f1f8e9; border-radius:8px;'>{''.join(items_html)}</div>", unsafe_allow_html=True)

def build_chatgpt_prompt(char: str) -> str:
    meta = component_map.get(char, {}).get("meta", {})
    def_en = clean_field(meta.get("definition", ""))
    decomp = format_decomposition(char)
    return f"Bilingual Dictionary Task: Define '{char}'. Context: {def_en}. Decomposition: {decomp}."

def render_splash():
    st.markdown("<div class='splash-card'><div class='splash-title'>Radix 🈑</div></div>", unsafe_allow_html=True)
    if st.button("Enter Radix", use_container_width=True):
        st.session_state.onboarding_done = True
        st.rerun()

# --- Main App ---

def main():
    if not component_map:
        st.error("Dataset not found.")
        st.stop()

    apply_dynamic_css()
    if not st.session_state.onboarding_done:
        render_splash()
        st.stop()

    # Sidebar
    with st.sidebar:
        st.markdown("<h1 style='text-align:center;'>🈑 Radix</h1>", unsafe_allow_html=True)
        st.text_input("Shortcut Search", key="sb_search", on_change=sync_sidebar_text)
        
        if st.session_state.show_inputs:
            st.checkbox("Components Only", key="w_component_only", on_change=sync_component_only, value=st.session_state.component_only)
            st.slider("Strokes", 1, 30, st.session_state.stroke_range, key="w_stroke_range", on_change=sync_stroke_range)
            
            # Use indexed stats for Expander
            with st.expander("Radicals"):
                for s in sorted(stats_cache["rad_groups"].keys()):
                    rads = stats_cache["rad_groups"][s]
                    cols = st.columns(5)
                    for i, r in enumerate(rads):
                        with cols[i % 5]:
                            if st.button(r, key=f"rad_{r}"):
                                st.session_state.radical = r
                                st.rerun()
            
            if st.session_state.preview_comp:
                render_stroke_order_sidebar(st.session_state.preview_comp)
        else:
            st.button("← Back", on_click=go_back, use_container_width=True)
            st.button("🏠 Root", on_click=go_to_root, use_container_width=True)
            render_stroke_order_sidebar(st.session_state.selected_comp)

    # Main Grid View
    if st.session_state.show_inputs:
        cur_min, cur_max = st.session_state.stroke_range
        # Filtering using pre-calculated stroke_count
        filtered = [
            c for c in component_map 
            if (lambda s: s is not None and cur_min <= s <= cur_max)(component_map[c].get('stroke_count'))
            and (st.session_state.radical == "none" or component_map[c].get("meta", {}).get("radical") == st.session_state.radical)
            and (not st.session_state.component_only or c in stats_cache["used_components"])
        ]
        
        sorted_comps = sorted(filtered, key=sort_key_usage_then_zipf)
        
        # Pagination
        PAGE_SIZE = 120
        total_pages = math.ceil(len(sorted_comps) / PAGE_SIZE)
        page_idx = (st.session_state.page - 1) * PAGE_SIZE
        page_items = sorted_comps[page_idx : page_idx + PAGE_SIZE]
        
        cols = st.columns(10)
        for i, ch in enumerate(page_items):
            with cols[i % 10]:
                st.button(ch, key=f"btn_{ch}", on_click=tile_click, args=(ch,), use_container_width=True)

    # Detail View
    else:
        char = st.session_state.selected_comp
        st.markdown(f"## Exploring: {char}")
        
        # Components & Children logic
        decomp = [c for c in component_map.get(char, {}).get("meta", {}).get("decomposition", "") if c not in IDC_CHARS]
        children = [c for c in component_map.get(char, {}).get("related_characters", []) if isinstance(c, str) and len(c) == 1]
        
        merged = []
        seen = set()
        for c in (decomp + sorted(children, key=sort_key_usage_then_zipf)):
            if c in component_map and c not in seen:
                merged.append(c)
                seen.add(c)
        
        # Render list
        for c in merged[:50]:
            c1, c2 = st.columns([1, 5])
            with c1:
                st.button(c, key=f"lst_{c}", on_click=list_tile_click, args=(c,), use_container_width=True)
            with c2:
                st.markdown(generate_clean_card_html(c, usage_count=component_usage_count(c)), unsafe_allow_html=True)

if __name__ == "__main__":
    main()
