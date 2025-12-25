# app.py
# Radix — Component-first Chinese character explorer (Combined Optimized Version)

import json
import math
import html
import sqlite3
import unicodedata
import gc
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

st.set_page_config(layout="wide", page_title="Radix", page_icon="🈁")

IDC_CHARS = {"⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"}
SCRIPT_FILTERS = ["Any", "Simplified", "Traditional"]


# --- MEMORY-OPTIMIZED DATA PIPELINE WITH ZIPF ---
def zipf_commonness_raw(ch: str) -> float:
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


@st.cache_resource
def get_zipf_frequency():
    try:
        from wordfreq import zipf_frequency
        return zipf_frequency
    except Exception:
        return None


ZIPF = get_zipf_frequency()


@st.cache_resource
def load_and_augment_map():
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return {}

    # Augment in-place to minimize memory footprint
    for char, info in data.items():
        meta = info.get("meta", {})
        
        # Pre-calculate usage count
        rel = info.get("related_characters", [])
        info['usage_count'] = len({c for c in rel if isinstance(c, str) and len(c) == 1})
        
        # Pre-calculate Zipf value
        info['zipf_val'] = zipf_commonness_raw(char)
        
        # Clean stroke count
        s = meta.get("strokes")
        try:
            if isinstance(s, (int, float)) and s > 0:
                info['stroke_count'] = int(s)
            elif isinstance(s, str) and s.isdigit():
                info['stroke_count'] = int(s)
            else:
                info['stroke_count'] = None
        except:
            info['stroke_count'] = None
    
    gc.collect()
    return data


@st.cache_resource
def get_component_stats(_component_map):
    r_groups = {}
    idc_counts = {}
    used_comps = set()

    for c, data in _component_map.items():
        r = data.get("meta", {}).get("radical")
        if r:
            gs = _component_map.get(r, {}).get('stroke_count') or 999
            r_groups.setdefault(gs, []).append(r)

        d = data.get("meta", {}).get("decomposition", "")
        if d and d[0] in IDC_CHARS:
            idc = d[0]
            idc_counts[idc] = idc_counts.get(idc, 0) + 1
        
        for ch in d:
            if ch not in IDC_CHARS:
                used_comps.add(ch)

    for gs in r_groups:
        r_groups[gs] = sorted(list(set(r_groups[gs])))

    gc.collect()
    return {
        "rad_groups": r_groups,
        "idc_counts": idc_counts,
        "used_components": used_comps
    }


# --- Load Data ---
component_map = load_and_augment_map()
stats_cache = get_component_stats(component_map) if component_map else {}


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
    .char-btn-wrap button:hover { background: #f0f9ff !important; border-color: #3b82f6 !important; }
    .pen-btn-wrap button { font-size: 1.5em !important; border: 1px solid #eee !important; background: #f8f9fa !important; margin-top: 5px !important; height: 40px !important; line-height: 1 !important; color: #555 !important; }
    .pen-btn-wrap button:hover { background: #e3f2fd !important; border-color: #90caf9 !important; color: #1565c0 !important; }
    .char-static-box { font-size: 3.5em; font-weight: bold; background: #fdfdfd; color: #999; border: 2px solid #eee; border-radius: 12px; padding: 5px; min-height: 80px; display: flex; align-items: center; justify-content: center; width: 100%; cursor: default; }
    .status-line { font-size: 1.1em; font-weight: 600; color: #0f5132; background-color: #d1e7dd; border: 1px solid #badbcc; padding: 15px; border-radius: 8px; margin: 20px 0 30px 0; }
    .status-tag { background-color: #f1f3f5; color: #2c3e50; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.9em; border: 1px solid #e9ecef; display: inline-flex; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .map-path { font-family: monospace; color: #155724; margin-left: 10px; }
    .preview-count-line {font-size: 1.3em; text-align: center; color: #2c3e50; margin: 20px 0 25px 0;}
    .preview-count-line .char {font-size: 1.4em; font-weight: bold; color: #e74c3c;}
    .jump-footer {margin-top: 40px; padding: 20px; background: #f8f9fa; border-top: 1px solid #e0e0e0; text-align: center;}
    div[data-testid="stExpander"] .stButton button {font-size: 1.2rem; height: 40px; padding: 0; line-height: 1.2; border-radius: 4px; border: 1px solid #eee; transition: all 0.1s ease-in-out;}
    div[data-testid="stExpander"] .stButton button:hover {border-color: #bbb; background-color: #f0f0f0;}
    .stroke-header {font-size: 0.85em; color: #888; border-bottom: 1px solid #eee; margin: 10px 0 5px 0; padding-bottom: 2px;}
    .compound-item { display: flex; align-items: baseline; margin-bottom: 6px; padding-bottom: 6px; border-bottom: 1px solid #e0e0e0; }
    .compound-item:last-child { border-bottom: none; margin-bottom: 0; }
    .cp-word { font-weight: bold; font-size: 1.1em; color: #2c3e50; min-width: 80px; margin-right: 10px; }
    .cp-pinyin { color: #d35400; font-family: monospace; margin-right: 10px; font-weight: 500; font-size: 1.5em;}
    .cp-mean { color: #333; font-size: 0.95em; flex: 1; }
    .splash-wrap {max-width: 1100px; margin: 0 auto; padding: 34px 10px 10px 10px;}
    .splash-card {background: white; border: 1px solid #eee; border-radius: 18px; padding: 34px; box-shadow: 0 6px 22px rgba(0,0,0,0.06);}
    .splash-title {font-size: 2.3em; font-weight: 850; line-height: 1.12; color:#111;}
    .splash-sub {margin-top: 10px; font-size: 1.15em; color:#444; line-height: 1.5;}
    .splash-demo {margin-top: 18px; padding: 14px 16px; background:#fff8e1; border:1px solid #ffeeba; border-radius: 14px;}
    .splash-demo-h {font-weight: 750; color:#856404; margin-bottom: 8px;}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)


# --- Database ---
@st.cache_resource
def get_db_connection():
    try:
        conn = sqlite3.connect("phrases.db", check_same_thread=False)
        return conn
    except Exception:
        return None


def batch_get_phrase_details(words, conn):
    """Fetches details for a list of words in a SINGLE query."""
    if not conn or not words:
        return {}
    try:
        placeholders = ",".join(["?"] * len(words))
        cursor = conn.cursor()
        query = f"SELECT word, pinyin, meanings FROM phrases WHERE word IN ({placeholders})"
        cursor.execute(query, list(words))
        results = cursor.fetchall()
        return {row[0]: {"pinyin": row[1], "meanings": row[2]} for row in results}
    except Exception:
        return {}


# --- Optimized Helpers ---
def get_stroke_count(char):
    return component_map.get(char, {}).get("stroke_count")


def component_usage_count(comp: str) -> int:
    return component_map.get(comp, {}).get("usage_count", 0)


def sort_key_usage_then_zipf(ch: str):
    """Smart sorting: high-usage components by frequency, low-usage by language commonness"""
    info = component_map.get(ch, {})
    use = info.get('usage_count', 0)
    z = info.get('zipf_val', float("-inf"))
    strokes = info.get('stroke_count') or 999
    group = 0 if use >= 3 else 1
    if group == 0:
        return (group, -use, -z, strokes, ch)
    return (group, -z, strokes, ch)


def apply_script_filter(chars: list[str]) -> list[str]:
    f = st.session_state.get("script_filter", "Any")
    if f == "Any":
        return chars
    if f == "Simplified":
        return [c for c in chars if not cc_t2s or cc_t2s.convert(c) == c]
    return [c for c in chars if not cc_s2t or cc_s2t.convert(c) == c]


def clean_field(field):
    return field[0] if isinstance(field, list) and field else field or "—"


def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", ""))
    if not hint or hint.lower() == "no hint":
        hint = ""
    details = clean_field(etymology.get("details", ""))
    if details == "—":
        details = ""
    parts = [p for p in [hint, details] if p]
    return "; ".join(parts) if parts else None


def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "—" if not d or "?" in d else d


def normalize_single_hanzi(raw: str) -> str:
    if not raw:
        return ""
    s = unicodedata.normalize("NFC", raw)
    chars = [ch for ch in s.strip() if not ch.isspace() and unicodedata.category(ch) != "Cf"]
    return chars[0] if len(chars) == 1 else ""


def resolve_to_known_variant(ch: str) -> str:
    """Try to find a known variant (simplified/traditional) if the exact char isn't in the map"""
    if not ch:
        return ""
    if ch in component_map:
        return ch
    if cc_s2t:
        t = cc_s2t.convert(ch)
        if t in component_map:
            return t
    if cc_t2s:
        s = cc_t2s.convert(ch)
        if s in component_map:
            return s
    return ""


def reset_script_filter_to_any():
    st.session_state.script_filter = "Any"
    st.session_state.pop("w_script_filter", None)


# --- Session State ---
defaults = {
    "onboarding_done": False,
    "selected_comp": "",
    "stroke_range": (3, 8),
    "radical": "none",
    "component_idc": "none",
    "display_mode": "Single Character",
    "text_input_comp": "",
    "page": 1,
    "text_input_warning": None,
    "show_inputs": True,
    "last_valid_selected_comp": "",
    "preview_comp": None,
    "stroke_view_active": False,
    "stroke_view_char": "",
    "script_filter": "Any",
    "component_only": True,
    "favourites_list": [],
    "fav_cursor": 0,
    "history": [],
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# Load favourites
if not st.session_state.favourites_list:
    try:
        with open("favourites.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                valid = [c for c in data if isinstance(c, str) and len(c) == 1]
                st.session_state.favourites_list = valid[:20]
    except FileNotFoundError:
        pass


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
    st.session_state.stroke_view_char = ""
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
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None
    if st.session_state.history:
        prev = st.session_state.history.pop()
        reset_script_filter_to_any()
        st.session_state.selected_comp = prev
        st.session_state.last_valid_selected_comp = prev
        st.session_state.show_inputs = False
        st.session_state.display_mode = "Single Character"
    else:
        st.session_state.show_inputs = True


def go_to_root():
    st.session_state.history = []
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None
    st.session_state.selected_comp = ""
    st.session_state.show_inputs = True
    reset_script_filter_to_any()
    st.session_state.display_mode = "Single Character"


def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""


def toggle_favourite(char):
    is_now_checked = st.session_state.get(f"fav_chk_{char}", False)
    if is_now_checked:
        if char not in st.session_state.favourites_list:
            if len(st.session_state.favourites_list) < 20:
                st.session_state.favourites_list.append(char)
            else:
                idx = st.session_state.fav_cursor
                st.session_state.favourites_list[idx] = char
                st.session_state.fav_cursor = (idx + 1) % 20
    else:
        if char in st.session_state.favourites_list:
            st.session_state.favourites_list.remove(char)


def handle_file_upload():
    uploaded_file = st.session_state.get("fav_uploader")
    if uploaded_file is not None:
        try:
            data = json.load(uploaded_file)
            if isinstance(data, list):
                valid_chars = [c for c in data if isinstance(c, str) and len(c) == 1]
                st.session_state.favourites_list = valid_chars[:20]
                st.session_state.fav_cursor = 0
                st.toast("Favourites loaded successfully!", icon="✅")
        except Exception as e:
            st.error(f"Error loading file: {e}")


def build_chatgpt_prompt(char: str) -> str:
    char = (char or "").strip()[:1]
    meta = component_map.get(char, {}).get("meta", {})
    def_en = clean_field(meta.get("definition", ""))
    decomp = format_decomposition(char)

    return f"""You are a bilingual Chinese dictionary editor.

Task:
For the single Hanzi below, give:
1) One-line Chinese definition (≤ 22 Chinese characters, no English).
2) Pinyin with tone marks.
3) Two example sentences that BEST illustrate the meaning (prefer everyday usage unless the character is primarily literary).
   - Each example must include the target character in a common word/phrase.
   - For each example provide:
     a) Chinese sentence
     b) English translation (natural, not literal)
     c) Highlight the target word/phrase used in that sentence.

Output ONLY valid JSON (no markdown, no extra text) with this schema:
{{
  "char": "<Hanzi>",
  "pinyin": "<tone-mark pinyin>",
  "def_zh": "<one-line Traditional Chinese definition>",
  "def_zh_sim": "<one-line Simplified Chinese definition>",
  "def_en": "<one-line English definition>",
  "examples": [
    {{
      "word": "<target word/phrase containing the character>",
      "pinyin": "<tone-mark pinyin>",
      "sent_zh": "<Traditional Chinese sentence>",
      "sent_zh_sim": "<Simplified Chinese sentence>",
      "sent_en": "<English translation>",
      "note_en": "<optional short note on meaning in this context or ''>"
    }},
    {{
      "word": "<target word/phrase containing the character>",
      "pinyin": "<tone-mark pinyin>",
      "sent_zh": "<Traditional Chinese sentence>",
      "sent_zh_sim": "<Simplified Chinese sentence>",
      "sent_en": "<English translation>",
      "note_en": "<optional short note or ''>"
    }}
  ]
}}

Hanzi: {char}
Context (may be empty):
- English definition: {def_en}
- Decomposition: {decomp}
"""


def render_copy_to_clipboard(prompt_text: str, widget_id: str):
    safe_text = json.dumps(prompt_text, ensure_ascii=False)
    st_html(
        f"""
        <div style="display:flex; justify-content:center; margin:10px 0 0 0;">
          <button id="copy-btn-{widget_id}" style="
              padding:10px 14px; border-radius:10px; border:1px solid #ddd;
              background:#fff; cursor:pointer; font-weight:700;">
            Copy Prompt to Clipboard
          </button>
        </div>
        <div id="copy-msg-{widget_id}" style="text-align:center; margin-top:8px; color:#2e7d32; font-weight:600;"></div>
        <script>
          (function() {{
            const text = {safe_text};
            const btn = document.getElementById("copy-btn-{widget_id}");
            const msg = document.getElementById("copy-msg-{widget_id}");
            if (!btn) return;

            async function copy() {{
              try {{
                await navigator.clipboard.writeText(text);
                msg.textContent = "Copied. Paste into ChatGPT.";
              }} catch (e) {{
                msg.textContent = "Copy failed. Please manually select and copy from the textbox above.";
              }}
              setTimeout(() => {{ msg.textContent = ""; }}, 2500);
            }}

            btn.addEventListener("click", copy);
          }})();
        </script>
        """,
        height=90,
    )


def generate_clean_card_html(c, usage_count=None):
    if not c:
        return ""
    info = component_map.get(c, {})
    meta = info.get("meta", {})
    pinyin = clean_field(meta.get("pinyin", ""))
    strokes = info.get('stroke_count')
    radical = clean_field(meta.get("radical", ""))
    decomp = format_decomposition(c)
    definition = clean_field(meta.get("definition", ""))
    etymology = get_etymology_text(meta)

    meta_items = []
    if pinyin and pinyin != "—":
        meta_items.append(f"<span class='meta-pinyin'>{pinyin}</span>")
    if strokes:
        meta_items.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    if radical and radical != "—":
        meta_items.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    if decomp and decomp != "—":
        meta_items.append(f"<span class='meta-tag'>{decomp}</span>")
    if usage_count is not None and usage_count > 0:
        meta_items.append(f"<span class='meta-tag'>Used in {usage_count} chars</span>")

    if cc_t2s:
        simplified = cc_t2s.convert(c)
        if simplified != c:
            meta_items.append(f"<span class='meta-tag meta-tag-trad'>Trad. → {simplified}</span>")
    if cc_s2t:
        traditional = cc_s2t.convert(c)
        if traditional != c:
            meta_items.append(f"<span class='meta-tag meta-tag-simp'>Simp. → {traditional}</span>")

    meta_html = f"<div class='meta-row'>{''.join(meta_items)}</div>"
    def_html = f"<div class='def-row'>{definition}</div>" if definition and definition != "—" else ""
    ety_html = f"<div class='ety-row'>{etymology}</div>" if etymology else ""
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"


def render_stroke_order_sidebar(char: str, size: int = 110):
    char = (char or "").strip()[:1]
    if not char:
        return

    pinyin = clean_field(component_map.get(char, {}).get("meta", {}).get("pinyin", ""))

    h = size + 80
    st_html(
        f"""
        <div style="display:flex; flex-direction:column; align-items:center; margin:20px 0;">
            <div style="text-align:center; font-size:2.5rem; font-weight:bold; color:#e67e22; margin-bottom:10px;">{pinyin}</div>
            <div id="sb-hw-{hash(char)}" style="width:{size}px; height:{size}px;"></div>
        </div>
        <script>
        (function() {{
            const char = {json.dumps(char, ensure_ascii=False)};
            const target = "sb-hw-{hash(char)}";
            async function loadScript(src) {{
                return new Promise((resolve, reject) => {{
                    const s = document.createElement('script');
                    s.src = src; s.async = true; s.onload = resolve; s.onerror = reject;
                    document.head.appendChild(s);
                }});
            }}
            async function ensureLib() {{
                if (window.HanziWriter) return;
                const sources = ['https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js',
                                 'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'];
                for (const src of sources) {{ try {{ await loadScript(src); if (window.HanziWriter) return; }} catch(e) {{}} }}
            }}

            function speak(text) {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const u = new SpeechSynthesisUtterance(text);
                    u.lang = 'zh-CN';
                    const voices = window.speechSynthesis.getVoices();
                    const zhVoice = voices.find(v => v.lang.replace('_', '-').toLowerCase().startsWith('zh'));
                    if (zhVoice) u.voice = zhVoice;
                    window.speechSynthesis.speak(u);
                }}
            }}

            async function init() {{
                try {{
                    await ensureLib();
                    const writer = window.HanziWriter.create(target, char, {{
                        width: {size}, height: {size}, padding: 8, showOutline: true, showCharacter: false,
                        strokeAnimationSpeed: 1.3, delayBetweenStrokes: 100
                    }});
                    writer.showCharacter();
                    const el = document.getElementById(target);
                    el.style.cursor = 'pointer';
                    const trigger = (e) => {{
                        e.preventDefault(); 
                        speak(char);
                        writer.hideCharacter();
                        writer.animateCharacter();
                    }};
                    el.addEventListener('click', trigger);
                    el.addEventListener('touchend', trigger);
                }} catch(e) {{
                    document.getElementById(target).innerHTML = `<div style="font-size:${size*0.7}px; line-height:${size}px; text-align:center;">${{char}}</div>`;
                }}
            }}
            init();
        }})();
        </script>
        """,
        height=h,
    )


def render_stroke_order_view(char_input: str):
    primary_char = (char_input or "").strip()[:1]
    if not primary_char:
        st.info("No character selected for stroke order.")
        return

    if st.session_state.display_mode == "Single Character":
        st.session_state.display_mode = "2-Character Phrases"
        st.rerun()

    st.markdown("### Stroke Order & Phrases")
    modes = ["2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
    current_index = modes.index(st.session_state.display_mode) if st.session_state.display_mode in modes else 0
    new_mode = st.radio("Display Mode", options=modes, index=current_index, horizontal=True, key="w_display_stroke_view")
    if new_mode != st.session_state.display_mode:
        st.session_state.display_mode = new_mode
        st.rerun()

    s_char = cc_t2s.convert(primary_char) if cc_t2s else primary_char
    t_char = cc_s2t.convert(primary_char) if cc_s2t else primary_char

    chars_to_show = []
    if s_char != t_char:
        if primary_char == t_char:
            chars_to_show = [t_char, s_char]
        else:
            chars_to_show = [s_char, t_char]
    else:
        chars_to_show = [primary_char]
    chars_to_show = list(dict.fromkeys(chars_to_show))

    BOX_SIZE = 280
    container_html = ""
    for i, c in enumerate(chars_to_show):
        label_text = ""
        if s_char != t_char:
            if c == s_char:
                label_text = "Simplified"
            elif c == t_char:
                label_text = "Traditional"
        label_html = (
            f"<div style='text-align:center; font-weight:bold; color:#555; margin-bottom:5px;'>{label_text}</div>"
            if label_text
            else ""
        )

        pinyin = clean_field(component_map.get(c, {}).get("meta", {}).get("pinyin", ""))

        container_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center;">
             {label_html}
            <div style="font-size:2.5rem; color:#e67e22; font-weight:bold; margin-bottom:10px;">{pinyin}</div>
            <div id="hw-target-{i}" style="width:{BOX_SIZE}px;height:{BOX_SIZE}px;border:1px solid #e0e0e0;border-radius:12px; background:white;"></div>
        </div>
        """

    st_html(
        f"""
        <div style="display:flex; gap:15px; align-items:flex-start; flex-wrap:wrap; justify-content:center;">
            {container_html}
        </div>
        <div style="display:flex; justify-content:center; margin-top:15px; gap:8px;">
             <button id="hw-reset">Reset</button><button id="hw-animate">Replay Animation</button>
        </div>
        <div id="hw-error" style="margin-top:10px; color:#b00020; text-align:center;"></div>
        <script>
        (function() {{
            const chars = {json.dumps(chars_to_show, ensure_ascii=False)};
            const boxSize = {BOX_SIZE};
            const errEl = document.getElementById('hw-error');

            function speak(text) {{
                if ('speechSynthesis' in window) {{
                    window.speechSynthesis.cancel();
                    const u = new SpeechSynthesisUtterance(text);
                    u.lang = 'zh-CN';
                    const voices = window.speechSynthesis.getVoices();
                    const zhVoice = voices.find(v => v.lang.replace('_', '-').toLowerCase().startsWith('zh'));
                    if (zhVoice) u.voice = zhVoice;
                    window.speechSynthesis.speak(u);
                }}
            }}
            
            function loadScript(src) {{ return new Promise((resolve, reject) => {{
                const s = document.createElement('script'); s.src = src; s.async = true;
                s.onload = () => resolve(src); s.onerror = () => reject();
                document.head.appendChild(s);
            }}); }}
            
            async function ensureLibLoaded() {{
                if (window.HanziWriter) return;
                const sources = ['https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js',
                                 'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'];
                for (const src of sources) {{ try {{ await loadScript(src); if (window.HanziWriter) return; }} catch (e) {{}} }}
            }}
            
            const writers = [];
            
            async function init() {{
                try {{
                    await ensureLibLoaded();
                    for (let idx = 0; idx < chars.length; idx++) {{
                        const char = chars[idx];
                        const targetId = 'hw-target-' + idx;
                        const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,
                                          `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
                        let hasData = false;
                        for (const url of dataUrls) {{ 
                            try {{ 
                                const res = await fetch(url); 
                                if (res.ok) {{ hasData = true; break; }} 
                            }} catch (e) {{}} 
                        }}
                        if(hasData) {{
                            const writer = window.HanziWriter.create(targetId, char, {{
                                width: boxSize, height: boxSize, padding: 10, showOutline: true, showCharacter: false,
                                strokeAnimationSpeed: 1, delayBetweenStrokes: 60
                            }});
                            writers.push({{w: writer, c: char}});
                        }} else {{
                            document.getElementById(targetId).innerHTML = `<div style="line-height:${{boxSize}}px; text-align:center; font-size:${{boxSize/2}}px; color:#ddd;">${{char}}</div>`;
                        }}
                    }}
                    autoAnimateAll(true);
                }} catch (e) {{ errEl.textContent = e.message || String(e); }}
            }}
            
            async function playSequence(item, silent) {{
                const writer = item.w;
                const char = item.c;
                for (let k = 0; k < 3; k++) {{
                    if (!silent) speak(char);
                    writer.hideCharacter();
                    await writer.animateCharacter();
                    await new Promise(r => setTimeout(r, 800));
                }}
                writer.showCharacter();
            }}
            
            function autoAnimateAll(silent = false) {{
                writers.forEach(item => {{ playSequence(item, silent); }});
            }}
            
            function resetAll() {{
                writers.forEach(item => {{ item.w.hideCharacter(); }});
            }}
            
            document.getElementById('hw-reset').addEventListener('click', resetAll);
            document.getElementById('hw-animate').addEventListener('click', () => autoAnimateAll(false));
            init();
        }})();
        </script>
        """,
        height=400,
    )

    st.markdown("---")

    n = {"2-Character Phrases": 2, "3-Character Phrases": 3, "4-Character Phrases": 4}.get(st.session_state.display_mode, 0)
    meta_compounds = component_map.get(primary_char, {}).get("meta", {}).get("compounds", [])
    relevant_compounds = [w for w in meta_compounds if isinstance(w, str) and len(w) == n]

    if relevant_compounds:
        db_conn = get_db_connection()
        sorted_compounds = sorted(relevant_compounds)

        if not db_conn:
            st.warning("⚠️ 'phrases.db' not found. Please upload it to your repository to see phrases.")
        else:
            phrases_map = batch_get_phrase_details(sorted_compounds, db_conn)
            items_html = []
            for word in sorted_compounds:
                entry = phrases_map.get(word)
                pinyin = entry.get("pinyin", "") if entry else ""
                meanings = entry.get("meanings", "") if entry else ""
                display_meanings = html.escape(meanings[:100] + ("..." if len(meanings) > 100 else ""))

                if entry:
                    items_html.append(
                        f"<div class='compound-item'>"
                        f"<span class='cp-word'>{word}</span>"
                        f"<span class='cp-pinyin'>{pinyin}</span>"
                        f"<span class='cp-mean'>{display_meanings}</span>"
                        f"</div>"
                    )
                else:
                    items_html.append(f"<div class='compound-item'><span class='cp-word'>{word}</span></div>")

            full_list_html = "".join(items_html)
            st.markdown(
                f"""
                <div style='padding:15px; background:#f1f8e9; border-radius:8px; 
                     margin:10px auto; border:1px solid #dcedc8; max-width:800px; max-height:400px; overflow-y:auto;'>
                  <div style='font-weight:bold; margin-bottom:10px; color:#2e7d32; 
                       border-bottom:2px solid #a5d6a7; padding-bottom:5px; text-align:center;'>
                    {st.session_state.display_mode} containing {primary_char}
                  </div>
                  {full_list_html}
                </div>
                """,
                unsafe_allow_html=True,
            )
    elif n > 0:
        st.info(f"No {st.session_state.display_mode} found for {primary_char}.")

    st.markdown("---")
    st.markdown("### ChatGPT Prompt (Chinese definition + bilingual examples)")

    prompt_text = build_chatgpt_prompt(primary_char)
    st.text_area(
        "Copy this prompt into ChatGPT",
        value=prompt_text,
        height=320,
        key=f"prompt_area_{primary_char}",
    )

    render_copy_to_clipboard(prompt_text, widget_id=str(hash(primary_char))[-6:])


def enter_component(comp: str):
    """Helper for direct entry (e.g. from Splash)"""
    reset_script_filter_to_any()
    st.session_state.history = []
    st.session_state.selected_comp = comp
    st.session_state.last_valid_selected_comp = comp
    st.session_state.show_inputs = False
    st.session_state.preview_comp = None
    st.session_state.text_input_comp = comp
    st.session_state.text_input_warning = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.display_mode = "Single Character"


def render_splash():
    st.markdown(
        """
        <div class="splash-wrap">
          <div class="splash-card">
            <div class="splash-title">Radix 🈁 Explore Characters by Components</div>
            <div class="splash-sub">
              Learn to read and write Chinese characters by identifying <b>components</b>.
              <b>Components</b> are recurring parts that hint at meaning or pronunciation.
            </div>
            <div class="splash-demo">
              <div class="splash-demo-h">Favourites Collection</div>
              <div>This list revolves as you add new characters. Load/Save your collection below.</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    lc1, lc2, lc3 = st.columns([1, 2, 1])
    with lc2:
        with st.expander("Manage Favourites (Save/Load)"):
            c_dl, c_ul = st.columns(2)
            with c_dl:
                json_data = json.dumps(st.session_state.favourites_list, ensure_ascii=False, indent=2)
                st.download_button(
                    label="💾 Save Favourites",
                    data=json_data,
                    file_name="favourites.json",
                    mime="application/json",
                )
            with c_ul:
                st.file_uploader(
                    "Load Favourites",
                    type=["json"],
                    key="fav_uploader",
                    on_change=handle_file_upload,
                    label_visibility="collapsed",
                )

    demos = st.session_state.favourites_list
    COLS = 5
    rows = (len(demos) + COLS - 1) // COLS

    for r in range(rows):
        cols = st.columns(COLS)
        for j in range(COLS):
            idx = r * COLS + j
            if idx >= len(demos):
                continue
            ch = demos[idx]
            count = component_usage_count(ch)
            with cols[j]:
                if st.button(f"Explore {ch}", type="primary", key=f"splash_{ch}_{idx}"):
                    st.session_state.onboarding_done = True
                    enter_component(ch)
                    st.rerun()
                st.caption(f"{count} characters")

    st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([2, 1, 2])
    with c2:
        if st.button("Enter Radix"):
            st.session_state.onboarding_done = True
            st.rerun()


def main():
    if not component_map:
        st.error("Component dataset not loaded. Ensure enhanced_component_map_with_etymology.json exists.")
        st.stop()

    apply_dynamic_css()

    if not st.session_state.get("onboarding_done", False):
        render_splash()
        st.stop()

    max_s_val = max((get_stroke_count(c) for c in component_map if get_stroke_count(c) is not None), default=30)

    with st.sidebar:
        st.markdown("<h1 style='text-align:center; margin-bottom:30px;'>🈁 Radix</h1>", unsafe_allow_html=True)

        if st.button("Show Favourites"):
            go_to_root()
            st.session_state.onboarding_done = False
            st.rerun()

        st.text_input("Shortcut: Paste/Type characters", key="sb_search", on_change=sync_sidebar_text)

        current_char_for_sidebar = None

        if st.session_state.stroke_view_active:
            current_char_for_sidebar = st.session_state.stroke_view_char
            c1, c2 = st.columns(2)
            with c1:
                st.button("← Back", on_click=end_stroke_view)
            with c2:
                st.button("🏠 Root", on_click=go_to_root)

            st.markdown("---")
            st.markdown("### Character Info")

            st.markdown(
                f"<div style='font-size:2em; font-weight:bold; text-align:center; margin-bottom:10px;'>{current_char_for_sidebar}</div>",
                unsafe_allow_html=True,
            )
            st.markdown(generate_clean_card_html(current_char_for_sidebar), unsafe_allow_html=True)

            s_char = cc_t2s.convert(current_char_for_sidebar) if cc_t2s else current_char_for_sidebar
            t_char = cc_s2t.convert(current_char_for_sidebar) if cc_s2t else current_char_for_sidebar
            counterpart = None
            if current_char_for_sidebar == s_char and t_char != current_char_for_sidebar:
                counterpart = t_char
            elif current_char_for_sidebar == t_char and s_char != current_char_for_sidebar:
                counterpart = s_char

            if counterpart:
                st.markdown("---")
                st.markdown(
                    f"<div style='font-size:2em; font-weight:bold; text-align:center; margin-bottom:10px; color:#666;'>{counterpart}</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(generate_clean_card_html(counterpart), unsafe_allow_html=True)

        elif st.session_state.show_inputs:
            st.markdown("### Filters")
            st.checkbox(
                "Show Components Only",
                key="w_component_only",
                value=st.session_state.component_only,
                on_change=sync_component_only,
            )

            min_s, max_s = st.session_state.stroke_range
            s_label = f"Strokes: {min_s} — {max_s}"
            with st.expander(s_label, expanded=False):
                st.slider(
                    "Select Stroke Range",
                    min_value=1,
                    max_value=max_s_val,
                    value=st.session_state.stroke_range,
                    key="w_stroke_range",
                    on_change=sync_stroke_range,
                    label_visibility="collapsed",
                )

            r_label = f"Radical: {st.session_state.radical}" if st.session_state.radical != "none" else "Radical (Any)"
            with st.expander(r_label, expanded=False):
                for s in sorted(stats_cache["rad_groups"].keys()):
                    st.markdown(f"<div class='stroke-header'>{s if s != 999 else '?'} Strokes</div>", unsafe_allow_html=True)
                    rads = stats_cache["rad_groups"][s]
                    cols = st.columns(5)
                    for i, r in enumerate(rads):
                        with cols[i % 5]:
                            if st.button(r, key=f"rad_{r}", type="primary" if st.session_state.radical == r else "secondary"):
                                st.session_state.radical = r
                                st.session_state.page = 1
                                st.rerun()

            idc_label = (
                f"Structure: {st.session_state.component_idc}"
                if st.session_state.component_idc != "none"
                else "Structure (Any)"
            )
            with st.expander(idc_label, expanded=False):
                idc_keys = sorted(stats_cache["idc_counts"].keys())
                idc_cols = st.columns(5)
                for i, idc in enumerate(idc_keys):
                    with idc_cols[i % 5]:
                        if st.button(
                            idc,
                            key=f"idc_{idc}",
                            type="primary" if st.session_state.component_idc == idc else "secondary",
                        ):
                            st.session_state.component_idc = idc
                            st.session_state.page = 1
                            st.rerun()

            st.markdown("---")

            if st.session_state.preview_comp:
                current_char_for_sidebar = st.session_state.preview_comp
                render_stroke_order_sidebar(current_char_for_sidebar, size=110)

                is_fav = current_char_for_sidebar in st.session_state.favourites_list
                st.checkbox(
                    "Show in Favourites",
                    value=is_fav,
                    key=f"fav_chk_{current_char_for_sidebar}",
                    on_change=toggle_favourite,
                    args=(current_char_for_sidebar,),
                )

                if st.button(
                    f"Explore {current_char_for_sidebar}",
                    key="sb_select_btn",
                    type="primary",
                ):
                    reset_script_filter_to_any()
                    st.session_state.history = []
                    st.session_state.selected_comp = current_char_for_sidebar
                    st.session_state.last_valid_selected_comp = current_char_for_sidebar
                    st.session_state.show_inputs = False
                    st.session_state.preview_comp = None
                    st.session_state.text_input_comp = current_char_for_sidebar
                    st.session_state.display_mode = "Single Character"
                    st.rerun()

                related = component_map.get(current_char_for_sidebar, {}).get("related_characters", [])
                count = len(set([c for c in related if isinstance(c, str) and len(c) == 1]))
                st.markdown(
                    f"<div class='preview-count-line'>{count} characters contain <span class='char'>{current_char_for_sidebar}</span></div>",
                    unsafe_allow_html=True,
                )

        else:
            # DETAIL VIEW Sidebar
            c1, c2 = st.columns(2)
            with c1:
                st.button("← Back", on_click=go_back)
            with c2:
                st.button("🏠 Root", on_click=go_to_root)

            current_char_for_sidebar = (
                st.session_state.preview_comp if st.session_state.preview_comp else st.session_state.selected_comp
            )

            if current_char_for_sidebar:
                render_stroke_order_sidebar(current_char_for_sidebar, size=140)

                is_fav = current_char_for_sidebar in st.session_state.favourites_list
                st.checkbox(
                    "Show in Favourites",
                    value=is_fav,
                    key=f"fav_chk_{current_char_for_sidebar}",
                    on_change=toggle_favourite,
                    args=(current_char_for_sidebar,),
                )

                st.radio(
                    "Filter Results",
                    options=SCRIPT_FILTERS,
                    index=SCRIPT_FILTERS.index(st.session_state.script_filter),
                    key="w_script_filter",
                    on_change=sync_script_filter,
                )

                related = component_map.get(current_char_for_sidebar, {}).get("related_characters", [])
                chars_all = list(set([c for c in related if isinstance(c, str) and len(c) == 1]))
                chars_all = [c for c in chars_all if c in component_map]
                chars_filtered = apply_script_filter(chars_all)
                count_filtered = len(chars_filtered)

                st.markdown(
                    f"<div class='preview-count-line'>{count_filtered} characters contain <span class='char'>{current_char_for_sidebar}</span></div>",
                    unsafe_allow_html=True,
                )

    if st.session_state.stroke_view_active:
        render_stroke_order_view(st.session_state.stroke_view_char)
        st.stop()

    if st.session_state.show_inputs:
        # GRID VIEW
        filter_parts = []
        cur_min, cur_max = st.session_state.stroke_range
        if not (cur_min == 1 and cur_max == max_s_val):
            if cur_min == cur_max:
                filter_parts.append(f"<span class='status-tag'>{cur_min} strokes</span>")
            elif cur_min == 1:
                filter_parts.append(f"<span class='status-tag'>≤ {cur_max} strokes</span>")
            elif cur_max == max_s_val:
                filter_parts.append(f"<span class='status-tag'>≥ {cur_min} strokes</span>")
            else:
                filter_parts.append(f"<span class='status-tag'>{cur_min}–{cur_max} strokes</span>")
        if st.session_state.radical != "none":
            filter_parts.append(f"<span class='status-tag'>Rad. {st.session_state.radical}</span>")
        if st.session_state.component_idc != "none":
            filter_parts.append(f"<span class='status-tag'>{st.session_state.component_idc}</span>")
        if st.session_state.component_only:
            filter_parts.append("<span class='status-tag'>Components Only</span>")
        filter_summary = "".join(filter_parts) if filter_parts else "<span class='status-tag'>All characters</span>"
        
        st.markdown(
            f"<div class='status-line'>{filter_summary} <span class='status-text'>· Single-click previews. Double-click explores.</span></div>",
            unsafe_allow_html=True,
        )

        filtered = [
            c for c in component_map
            if (s := get_stroke_count(c)) is not None and cur_min <= s <= cur_max
            and (st.session_state.radical == "none" or component_map[c]["meta"].get("radical") == st.session_state.radical)
            and (st.session_state.component_idc == "none" or component_map[c]["meta"].get("decomposition", "").startswith(st.session_state.component_idc))
            and (not st.session_state.component_only or c in stats_cache["used_components"])
        ]
        
        sorted_comps = sorted(filtered, key=sort_key_usage_then_zipf)

        if not sorted_comps:
            st.info("No components match current filters.")
        else:
            PAGE_SIZE = 120
            GRID_COLS = 10
            total = len(sorted_comps)
            max_page = max(1, math.ceil(total / PAGE_SIZE))
            st.session_state.page = max(1, min(st.session_state.page, max_page))
            
            p1, p2, p3 = st.columns([1, 3, 1])
            with p1:
                if st.button("◀ Prev", disabled=st.session_state.page <= 1):
                    st.session_state.page -= 1
                    st.rerun()
            with p2:
                start = (st.session_state.page - 1) * PAGE_SIZE + 1
                end = min(st.session_state.page * PAGE_SIZE, total)
                st.markdown(
                    f"""<div style='text-align:center; padding:10px 0; color:#555;'><div style='font-size:1.1em; font-weight:bold;'>{start}–{end} of {total}</div><div style='font-size:0.85em; color:#e74c3c;'>Sorted by component-usage; low-usage uses language commonness</div></div>""",
                    unsafe_allow_html=True,
                )
            with p3:
                if st.button("Next ▶", disabled=st.session_state.page >= max_page):
                    st.session_state.page += 1
                    st.rerun()

            page = sorted_comps[(st.session_state.page - 1) * PAGE_SIZE : st.session_state.page * PAGE_SIZE]
            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            cols = st.columns(GRID_COLS)
            for i, ch in enumerate(page):
                with cols[i % GRID_COLS]:
                    is_preview = st.session_state.preview_comp == ch
                    st.button(
                        ch,
                        key=f"b_{ch}_{st.session_state.page}",
                        type="primary" if is_preview else "secondary",
                        on_click=tile_click,
                        args=(ch,),
                    )
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='jump-footer'>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.session_state.text_input_warning:
                    st.warning(st.session_state.text_input_warning)
                st.text_input(
                    "Go to component/character",
                    value=st.session_state.text_input_comp,
                    key="w_text",
                    on_change=sync_text,
                    placeholder="Type one Hanzi, e.g. 水",
                    label_visibility="collapsed",
                )
                st.caption("Enter one Chinese character to jump directly to its details")
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # DETAIL LIST VIEW
        st.session_state.display_mode = "Single Character"

        path_items = ["🏠 Root"] + st.session_state.history + [f"<b>{st.session_state.selected_comp}</b>"]
        path_str = " &nbsp;→&nbsp; ".join(path_items)

        st.markdown(
            f"""
            <div class='status-line'>
                <div style='margin-bottom:8px;'>
                    <span class='status-tag'>Location</span> 
                    <span class='map-path'>{path_str}</span>
                </div>
                <div class='status-text' style='font-size:0.85em; color:#666;'>Single-click previews. Double-click explores.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected = st.session_state.selected_comp

        # Components first
        decomp_raw = component_map.get(selected, {}).get("meta", {}).get("decomposition", "")
        components_list = [c for c in decomp_raw if c not in IDC_CHARS and c != "?" and c != "—"]

        # Children next
        related_raw = component_map.get(selected, {}).get("related_characters", [])
        children_list = [c for c in related_raw if isinstance(c, str) and len(c) == 1]
        children_sorted = sorted(children_list, key=sort_key_usage_then_zipf)

        # Merge (dedupe)
        final_chars_list = []
        seen_chars = set()
        for c in components_list:
            if c not in seen_chars and c in component_map:
                final_chars_list.append(c)
                seen_chars.add(c)
        for c in children_sorted:
            if c not in seen_chars and c in component_map:
                final_chars_list.append(c)
                seen_chars.add(c)

        chars = final_chars_list

        # Hybrid render: 120 clickable, rest static
        LIMIT = 120
        clickable_chars = chars[:LIMIT]
        static_chars = chars[LIMIT:]

        # Apply script filter
        clickable_chars = apply_script_filter(clickable_chars)
        static_chars = apply_script_filter(static_chars)

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
                usage_count = component_usage_count(c)
                st.markdown(generate_clean_card_html(c, usage_count=usage_count), unsafe_allow_html=True)

            st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

        if len(static_chars) > 0:
            st.markdown("---")
            st.markdown(
                f"<div style='text-align:center; color:#888; font-weight:bold; margin-bottom:20px;'>⬇️ {len(static_chars)} More Results (Copy & Paste into Shortcut sidebar to explore) ⬇️</div>",
                unsafe_allow_html=True,
            )

            for c in static_chars:
                col_char, col_details = st.columns([2, 10])
                with col_char:
                    st.markdown(f"<div class='char-static-box'>{c}</div>", unsafe_allow_html=True)
                with col_details:
                    usage_count = component_usage_count(c)
                    st.markdown(generate_clean_card_html(c, usage_count=usage_count), unsafe_allow_html=True)
                st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)


if __name__ == "__main__":
    main()
