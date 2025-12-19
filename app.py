import json
import math
import streamlit as st
from streamlit.components.v1 import html as st_html

# --- IMPORT OpenCC for Traditional/Simplified Conversion ---
try:
    from opencc import OpenCC
    cc_t2s = OpenCC('t2s')
    cc_s2t = OpenCC('s2t')
except ImportError:
    cc_t2s = None
    cc_s2t = None

st.set_page_config(layout="wide")

IDC_CHARS = {'⿰', '⿱', '⿲', '⿳', '⿴', '⿵', '⿶', '⿷', '⿸', '⿹', '⿺', '⿻'}

def apply_dynamic_css():
    css = """
    <style>
        .results-header-sidebar {font-size: 1.4em; font-weight: bold; color: #2c3e50; margin: 20px 0 10px 0; text-align: center;}
        .selected-char-sidebar {font-size: 3em; text-align: center; color: #e74c3c; margin: 20px 0; font-weight: bold; line-height: 1.2;}
        .char-card {background: white; padding: 20px; border-radius: 10px; margin-bottom: 0px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);}
        .meta-row {font-size: 0.95em; color: #555; margin-bottom: 8px; display: flex; align-items: center; flex-wrap: wrap; gap: 10px;}
        .meta-pinyin {font-weight: bold; font-size: 1.1em; color: #2c3e50;}
        .meta-tag {background: #f1f3f5; padding: 2px 8px; border-radius: 4px; font-size: 0.85em; color: #495057;}
        .meta-tag-trad {background: #fff8e1; color: #856404; border: 1px solid #ffeeba;}
        .def-row {font-size: 1.1em; line-height: 1.4; color: #2c3e50; margin-bottom: 8px;}
        .ety-row {font-size: 0.9em; color: #666; font-style: italic; border-top: 1px solid #eee; padding-top: 8px; margin-top: 4px;}
        .comp-grid .stButton button {font-size: 2em; height: 80px; background: white; border: 1px solid #e0e0e0; border-radius: 12px; box-shadow: 0 2px 6px rgba(0,0,0,0.08); padding: 0; line-height: 80px;}
        .comp-grid .stButton button:hover {background: #fff5f5; border-color: #f2c6c6; color: #c0392b;}
        .status-line {font-size: 1.1em; font-weight: 600; color: #0f5132; background-color: #d1e7dd; border: 1px solid #badbcc; padding: 15px; border-radius: 8px; margin: 20px 0 30px 0; text-align: center;}
        .status-tag {background-color: #f1f3f5; color: #2c3e50; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 0.9em; border: 1px solid #e9ecef; display: inline-flex; align-items: center; box-shadow: 0 1px 2px rgba(0,0,0,0.05);}
        .status-text {color: #0f5132; font-size: 0.95em; margin-left: 10px;}
        .preview-count-line {font-size: 1.3em; text-align: center; color: #2c3e50; margin: 20px 0 25px 0;}
        .preview-count-line .char {font-size: 1.4em; font-weight: bold; color: #2c3e50;}
        .count-line {font-size: 1.2em; text-align: center; color: #333; margin: 15px 0;}
        .count-line .char {font-weight: bold; color: #e74c3c;}
        .jump-footer {margin-top: 40px; padding: 20px; background: #f8f9fa; border-top: 1px solid #e0e0e0; text-align: center;}
        div[data-testid="stExpander"] .stButton button {font-size: 1.2rem; height: 40px; padding: 0; line-height: 1.2; border-radius: 4px; border: 1px solid #eee; transition: all 0.1s ease-in-out;}
        div[data-testid="stExpander"] .stButton button:hover {border-color: #bbb; background-color: #f0f0f0;}
        .stroke-header {font-size: 0.85em; color: #888; border-bottom: 1px solid #eee; margin: 10px 0 5px 0; padding-bottom: 2px;}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

@st.cache_data
def load_component_map():
    try:
        with open("enhanced_component_map_with_etymology.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

try:
    component_map = load_component_map()
except Exception as e:
    component_map = {}
    st.error(f"Failed to load data: {e}")

def clean_field(field):
    # Check if field is a list and has elements
    if isinstance(field, list) and field:
        return field,[object Object],  # Return the first element of the list
    return field or "—"  # Return the field or "—" if field is None or empty

def get_stroke_count(char):
    strokes = component_map.get(char, {}).get("meta", {}).get("strokes", None)
    try:
        if isinstance(strokes, (int, float)) and strokes > 0: return int(strokes)
        if isinstance(strokes, str) and strokes.isdigit(): return int(strokes)
    except: pass
    return None

def get_etymology_text(meta):
    etymology = meta.get("etymology", {})
    hint = clean_field(etymology.get("hint", ""))
    if not hint or hint.lower() == "no hint": hint = ""
    details = clean_field(etymology.get("details", ""))
    if details == "—": details = ""
    parts = [p for p in [hint, details] if p]
    return "; ".join(parts) if parts else None

def format_decomposition(char):
    d = component_map.get(char, {}).get("meta", {}).get("decomposition", "")
    return "—" if not d or '?' in d else d

# State init
defaults = {
    "selected_comp": "", "stroke_count": 0, "radical": "none", "component_idc": "none",
    "display_mode": "Single Character", "text_input_comp": "", "page": 1, "text_input_warning": None,
    "show_inputs": True, "last_valid_selected_comp": "", "preview_comp": None,
    "stroke_view_active": False, "stroke_view_char": "",
    "script_variant": "None"
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# Callbacks
def sync_stroke():
    val = st.session_state.w_stroke
    st.session_state.stroke_count = int(val) if val != 0 else 0
    st.session_state.page = 1

def sync_idc():
    st.session_state.component_idc = st.session_state.w_idc
    st.session_state.page = 1

def sync_script():
    st.session_state.script_variant = st.session_state.w_script
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
        st.session_state.preview_comp = None
    else:
        st.session_state.text_input_warning = "Not found"

def tile_click(c):
    if st.session_state.show_inputs:
        if st.session_state.preview_comp == c:
            st.session_state.selected_comp = c
            st.session_state.last_valid_selected_comp = c
            st.session_state.show_inputs = False
            st.session_state.preview_comp = None
            st.session_state.text_input_comp = c
        else:
            st.session_state.preview_comp = c

def back():
    st.session_state.show_inputs = True
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None
    st.session_state.script_variant = "None"

def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def reset():
    st.session_state.stroke_count = 0
    st.session_state.radical = "none"
    st.session_state.component_idc = "none"
    st.session_state.script_variant = "None"
    st.session_state.page = 1
    st.session_state.show_inputs = True
    st.session_state.preview_comp = None
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""
    st.session_state.text_input_comp = ""
    st.session_state.text_input_warning = None

def generate_clean_card_html(c):
    if not c or c not in component_map:
        return ""
    meta = component_map.get(c, {}).get("meta", {})
    pinyin = clean_field(meta.get("pinyin", ""))
    strokes = get_stroke_count(c)
    radical = clean_field(meta.get("radical", ""))
    decomp = format_decomposition(c)
    definition = clean_field(meta.get("definition", ""))
    etymology = get_etymology_text(meta)
    
    meta_items = []
    if pinyin and pinyin != "—": meta_items.append(f"<span class='meta-pinyin'>{pinyin}</span>")
    if strokes: meta_items.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    if radical and radical != "—": meta_items.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    if decomp and decomp != "—": meta_items.append(f"<span class='meta-tag'>{decomp}</span>")
    if cc_t2s:
        simplified = cc_t2s.convert(c)
        if simplified != c:
            meta_items.append(f"<span class='meta-tag meta-tag-trad'>Trad. → {simplified}</span>")
    
    meta_html = f"<div class='meta-row'>{''.join(meta_items)}</div>"
    def_html = f"<div class='def-row'>{definition}</div>" if definition and definition != "—" else ""
    ety_html = f"<div class='ety-row'>{etymology}</div>" if etymology else ""
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"

# Compact animated stroke order for sidebar
def render_stroke_order_sidebar(char: str, size: int = 110):
    char = (char or "").strip()[:1]
    if not char:
        return
    h = size + 40
    st_html(
        f"""
        <div style="display:flex; justify-content:center; margin:20px 0;">
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
            const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,
                              `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
            async function loadData() {{
              for (const url of dataUrls) {{ try {{ const res = await fetch(url); if (res.ok) return await res.json(); }} catch(e) {{}} }}
              throw new Error('No data');
            }}
            async function init() {{
              try {{
                await ensureLib();
                const charData = await loadData();
                const writer = window.HanziWriter.create(target, char, {{
                  width: {size}, height: {size}, padding: 8, showOutline: true, showCharacter: false,
                  strokeAnimationSpeed: 1.3, delayBetweenStrokes: 100
                }});
                writer.animateCharacter();
                const el = document.getElementById(target);
                el.style.cursor = 'pointer';
                el.addEventListener('click', () => writer.animateCharacter());
              }} catch(e) {{
                document.getElementById(target).innerHTML = `<div style="font-size:${size*0.7}px; line-height:${size}px; text-align:center;">${{char}}</div>`;
              }}
            }}
            init();
          }})();
        </script>
        """,
        height=h
    )

def render_stroke_order_view(char: str):
    char = (char or "").strip()[:1]
    if not char:
        st.info("No character selected for stroke order.")
        return
    st.markdown(f"## Stroke order — {char}")
    st_html(
        f"""
        <div style="display:flex; gap:24px; align-items:flex-start; flex-wrap:wrap;">
          <div>
            <div id="hw-target" style="width:420px;height:420px;border:1px solid #e0e0e0;border-radius:12px;"></div>
            <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
              <button id="hw-prev">Back</button><button id="hw-next">Next</button>
              <button id="hw-reset">Reset</button><button id="hw-animate">Animate</button>
            </div>
            <div id="hw-status" style="margin-top:10px; font-family: ui-monospace; color:#444;"></div>
            <div id="hw-error" style="margin-top:10px; color:#b00020;"></div>
          </div>
        </div>
        <script>
          (function() {{
            const char = {json.dumps(char, ensure_ascii=False)};
            const statusEl = document.getElementById('hw-status');
            const errEl = document.getElementById('hw-error');
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
            const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,
                              `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
            async function loadCharData() {{
              for (const url of dataUrls) {{ try {{ const res = await fetch(url); if (!res.ok) continue; return await res.json(); }} catch (e) {{}} }}
              throw new Error('Stroke data not found.');
            }}
            let writer = null; let i = -1; let total = 0;
            function setStatus() {{ statusEl.textContent = `Stroke: ${{Math.max(i+1, 0)}} / ${{total}}`; }}
            async function init() {{
              try {{
                await ensureLibLoaded();
                const charData = await loadCharData();
                total = (charData.medians || []).length || 0;
                writer = window.HanziWriter.create('hw-target', char, {{
                  width: 420, height: 420, padding: 14, showOutline: true, showCharacter: false,
                  strokeAnimationSpeed: 1, delayBetweenStrokes: 120
                }});
                i = -1; writer.hideCharacter(); setStatus();
              }} catch (e) {{ errEl.textContent = e.message || String(e); }}
            }}
            async function nextStroke() {{ if (!writer || i + 1 >= total) return; i += 1; await writer.animateStroke(i); setStatus(); }}
            async function prevStroke() {{ if (!writer || i <= -1) return; i -= 1; writer.hideCharacter(); for (let k = 0; k <= i; k++) await writer.animateStroke(k); setStatus(); }}
            function resetAll() {{ if (!writer) return; i = -1; writer.hideCharacter(); setStatus(); }}
            async function animateAll() {{ if (!writer) return; i = -1; writer.hideCharacter(); await writer.animateCharacter(); i = total - 1; setStatus(); }}
            document.getElementById('hw-next').addEventListener('click', nextStroke);
            document.getElementById('hw-prev').addEventListener('click', prevStroke);
            document.getElementById('hw-reset').addEventListener('click', resetAll);
            document.getElementById('hw-animate').addEventListener('click', animateAll);
            init();
          }})();
        </script>
        """,
        height=560,
    )

def main():
    if not component_map:
        st.stop()

    apply_dynamic_css()

    with st.sidebar:
        st.markdown("<h1 style='text-align:center; margin-bottom:30px;'>🈑 Radix</h1>", unsafe_allow_html=True)

        if st.button("🔄 Reset All Filters & Selection", use_container_width=True, type="primary"):
            reset()
            st.rerun()

        if st.session_state.stroke_view_active:
            st.button("← Back", on_click=end_stroke_view, use_container_width=True)
            st.button("← Back to list", on_click=back, use_container_width=True)

        elif st.session_state.show_inputs:
            st.markdown("### Filters")

            # === FULL ORIGINAL FILTERS RESTORED ===
            if "rad_groups" not in st.session_state:
                r_counts = {}
                s_counts = {}
                idc_counts = {}
                for c, data in component_map.items():
                    r = data.get("meta", {}).get("radical")
                    if r: r_counts[r] = r_counts.get(r, 0) + 1
                    s = get_stroke_count(c)
                    if s: s_counts[s] = s_counts.get(s, 0) + 1
                    d = data.get("meta", {}).get("decomposition", "")
                    if d and d[0] in IDC_CHARS:
                        idc = d[0]
                        idc_counts[idc] = idc_counts.get(idc, 0) + 1
                r_groups = {}
                for r in r_counts:
                    gs = get_stroke_count(r) or 999
                    r_groups.setdefault(gs, []).append(r)
                for gs in r_groups: r_groups[gs].sort()
                st.session_state.rad_groups = r_groups
                st.session_state.rad_counts = r_counts
                st.session_state.stroke_counts = s_counts
                st.session_state.idc_counts = idc_counts

            # Stroke filter
            s_label = f"Total Strokes: {st.session_state.stroke_count}" if st.session_state.stroke_count > 0 else "Total Strokes (Any)"
            with st.expander(s_label, expanded=False):
                if st.button("Clear Strokes", use_container_width=True):
                    st.session_state.stroke_count = 0
                    st.session_state.page = 1
                    st.rerun()
                s_keys = sorted(st.session_state.stroke_counts.keys())
                s_cols = st.columns(6)
                for i, s in enumerate(s_keys):
                    with s_cols[i % 6]:
                        if st.button(str(s), key=f"str_{s}", type="primary" if st.session_state.stroke_count == s else "secondary"):
                            st.session_state.stroke_count = s
                            st.session_state.page = 1
                            st.rerun()

            # Radical filter
            r_label = f"Radical: {st.session_state.radical}" if st.session_state.radical != "none" else "Radical (Any)"
            with st.expander(r_label, expanded=False):
                if st.button("Clear Radical", use_container_width=True):
                    st.session_state.radical = "none"
                    st.session_state.page = 1
                    st.rerun()
                for s in sorted(st.session_state.rad_groups.keys()):
                    st.markdown(f"<div class='stroke-header'>{s if s!=999 else '?'} Strokes</div>", unsafe_allow_html=True)
                    rads = st.session_state.rad_groups[s]
                    cols = st.columns(5)
                    for i, r in enumerate(rads):
                        with cols[i % 5]:
                            if st.button(r, key=f"rad_{r}", type="primary" if st.session_state.radical == r else "secondary"):
                                st.session_state.radical = r
                                st.session_state.page = 1
                                st.rerun()

            # Structure filter
            idc_label = f"Structure: {st.session_state.component_idc}" if st.session_state.component_idc != "none" else "Structure (Any)"
            with st.expander(idc_label, expanded=False):
                if st.button("Clear Structure", use_container_width=True):
                    st.session_state.component_idc = "none"
                    st.session_state.page = 1
                    st.rerun()
                idc_keys = sorted(st.session_state.idc_counts.keys())
                idc_cols = st.columns(5)
                for i, idc in enumerate(idc_keys):
                    with idc_cols[i % 5]:
                        if st.button(idc, key=f"idc_{idc}", type="primary" if st.session_state.component_idc == idc else "secondary"):
                            st.session_state.component_idc = idc
                            st.session_state.page = 1
                            st.rerun()

            st.markdown("---")
            # PREVIEW WITH ANIMATED STROKE ORDER
            if st.session_state.preview_comp:
                preview_char = st.session_state.preview_comp
                st.markdown(f"<div style='text-align:center; font-size:1.6em; font-weight:bold; color:#e74c3c; margin-bottom:8px;'>{preview_char}</div>", unsafe_allow_html=True)
                render_stroke_order_sidebar(preview_char, size=110)
                related = component_map.get(preview_char, {}).get("related_characters", [])
                count = len(set([c for c in related if len(c) == 1]))
                st.markdown(f"<div class='preview-count-line'>{count} characters with <span class='char'>{preview_char}</span></div>", unsafe_allow_html=True)
                st.markdown(generate_clean_card_html(preview_char), unsafe_allow_html=True)

        else:
            # SELECTED VIEW WITH ANIMATED STROKE ORDER
            st.button("← Back to list", on_click=back, use_container_width=True)
            selected_char = st.session_state.selected_comp
            if selected_char:
                if st.button("View full stroke order", use_container_width=True):
                    st.session_state.stroke_view_char = selected_char
                    st.session_state.stroke_view_active = True
                    st.rerun()
                render_stroke_order_sidebar(selected_char, size=140)
                st.selectbox("Filter Results", ["None", "Simplified", "Traditional"],
                             key="w_script", index=["None", "Simplified", "Traditional"].index(st.session_state.script_variant),
                             on_change=sync_script)
                related = component_map.get(selected_char, {}).get("related_characters", [])
                chars_unique = list(set([c for c in related if len(c) == 1]))
                if st.session_state.script_variant != "None" and cc_t2s and cc_s2t:
                    filtered = []
                    for c in chars_unique:
                        if st.session_state.script_variant == "Simplified":
                            if cc_t2s.convert(c) == c and cc_s2t.convert(c) != c: filtered.append(c)
                        elif st.session_state.script_variant == "Traditional":
                            if cc_s2t.convert(c) == c and cc_t2s.convert(c) != c: filtered.append(c)
                    chars_unique = filtered
                count = len([c for c in chars_unique if c in component_map])
                st.markdown(f"<div class='count-line'>{count} characters with <span class='char'>{selected_char}</span></div>", unsafe_allow_html=True)
                modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
                st.radio("", options=modes, index=modes.index(st.session_state.display_mode), key="w_display", on_change=sync_display)

    # Full stroke view
    if st.session_state.stroke_view_active:
        render_stroke_order_view(st.session_state.stroke_view_char)
        st.stop()

    # Main content (your original grid and results — unchanged)
    if st.session_state.show_inputs:
        filter_parts = []
        if st.session_state.stroke_count > 0: filter_parts.append(f"<span class='status-tag'>{st.session_state.stroke_count} strokes</span>")
        if st.session_state.radical != "none": filter_parts.append(f"<span class='status-tag'>Rad. {st.session_state.radical}</span>")
        if st.session_state.component_idc != "none": filter_parts.append(f"<span class='status-tag'>{st.session_state.component_idc}</span>")
        filter_summary = "".join(filter_parts) if filter_parts else "<span class='status-tag'>All characters</span>"
        st.markdown(f"<div class='status-line'>{filter_summary} <span class='status-text'>· 🖱to preview in sidebar · 🖱🖱 to select</span></div>", unsafe_allow_html=True)

        filtered = [c for c in component_map if
            (st.session_state.stroke_count == 0 or get_stroke_count(c) == st.session_state.stroke_count) and
            (st.session_state.radical == "none" or component_map.get(c, {}).get("meta", {}).get("radical") == st.session_state.radical) and
            (st.session_state.component_idc == "none" or component_map.get(c, {}).get("meta", {}).get("decomposition", "").startswith(st.session_state.component_idc))
        ]

        def _result_count(comp: str) -> int:
            rel = component_map.get(comp, {}).get("related_characters", [])
            return len({x for x in rel if isinstance(x, str) and len(x) == 1})

        _counts = {c: _result_count(c) for c in filtered}
        sorted_comps = sorted(filtered, key=lambda c: (-_counts.get(c, 0), get_stroke_count(c) or 999, c))

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
                if st.button("◀ Prev", disabled=st.session_state.page<=1):
                    st.session_state.page -= 1
                    st.rerun()
            with p2:
                start = (st.session_state.page-1)*PAGE_SIZE + 1
                end = min(st.session_state.page*PAGE_SIZE, total)
                st.markdown(f"<div style='text-align:center; padding:10px 0; font-size:1.1em; color:#555;'>{start}–{end} of {total}</div>", unsafe_allow_html=True)
            with p3:
                if st.button("Next ▶", disabled=st.session_state.page>=max_page):
                    st.session_state.page += 1
                    st.rerun()

            page = sorted_comps[(st.session_state.page-1)*PAGE_SIZE : st.session_state.page*PAGE_SIZE]
            st.markdown("<div class='comp-grid'>", unsafe_allow_html=True)
            cols = st.columns(GRID_COLS)
            for i, ch in enumerate(page):
                with cols[i % GRID_COLS]:
                    is_preview = st.session_state.preview_comp == ch
                    st.button(ch, key=f"b_{ch}_{st.session_state.page}", use_container_width=True,
                              type="primary" if is_preview else "secondary", on_click=tile_click, args=(ch,))
            st.markdown("</div>", unsafe_allow_html=True)

            st.markdown("<div class='jump-footer'>", unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.session_state.text_input_warning: st.warning(st.session_state.text_input_warning)
                st.text_input("Jump", value=st.session_state.text_input_comp, key="w_text", on_change=sync_text,
                              placeholder="Type a single Hanzi, e.g. 水", label_visibility="collapsed")
                st.caption("Enter one Chinese character to jump directly to its details")
            st.markdown("</div>", unsafe_allow_html=True)

    else:
        # Results view (unchanged)
        related = component_map[st.session_state.selected_comp].get("related_characters", [])
        chars = list(set([c for c in related if len(c)==1]))
        n = int(st.session_state.display_mode[0]) if st.session_state.display_mode != "Single Character" else 0
        compounds = {c: [w for w in component_map.get(c, {}).get("meta", {}).get("compounds", []) if len(w)==n] for c in chars} if n else {c:[] for c in chars}
        chars = [c for c in chars if n==0 or compounds[c]]
        chars = sorted(chars, key=lambda x: get_stroke_count(x) or 999)

        if st.session_state.script_variant == "Simplified":
            chars = [c for c in chars if not cc_t2s or cc_t2s.convert(c) == c]
        elif st.session_state.script_variant == "Traditional":
            chars = [c for c in chars if not cc_s2t or cc_s2t.convert(c) == c]

        for c in chars:
            col_btn, col_char, col_details = st.columns([1, 2, 12])
            with col_btn:
                st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)
                if st.button("🖊️", key=f"stroke_btn_{c}", help="View stroke order"):
                    st.session_state.stroke_view_char = c
                    st.session_state.stroke_view_active = True
                    st.rerun()
            with col_char:
                st.markdown(f"<div style='font-size: 3.5em; font-weight: bold; text-align: center; color: #111; line-height: 1.2;'>{c}</div>", unsafe_allow_html=True)
            with col_details:
                st.markdown(generate_clean_card_html(c), unsafe_allow_html=True)
                if compounds.get(c):
                    st.markdown(f"<div style='padding:10px; background:#f1f8e9; border-radius:8px; margin-top:5px;'><strong>{st.session_state.display_mode}:</strong> {' '.join(sorted(compounds[c]))}</div>", unsafe_allow_html=True)
            st.markdown("<div style='height: 15px'></div>", unsafe_allow_html=True)

        if chars and n:
            with st.expander("Export Compounds"):
                st.text_area("Copy list", "\n".join(w for c in chars for w in compounds[c]), height=150)

if __name__ == "__main__":
    main()
