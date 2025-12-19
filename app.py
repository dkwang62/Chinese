import json
import math
import streamlit as st
from streamlit.components.v1 import html as st_html
import json  # For passing data to JS

# --- IMPORT OpenCC for Traditional/Simplified Conversion ---
try:
    from opencc import OpenCC
    # Initialize converters
    cc_t2s = OpenCC('t2s') # Traditional -> Simplified
    cc_s2t = OpenCC('s2t') # Simplified -> Traditional
except ImportError:
    cc_t2s = None
    cc_s2t = None

# ------------------------------
# NEW: Robust component map loader
# ------------------------------
def load_component_map():
    """Load the component map with fallback filenames and graceful error handling."""
    possible_files = [
        "enhanced_component_map_with_etymology.json",
        "component_map.json"
    ]
    for filename in possible_files:
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                st.success(f"Loaded component data from `{filename}`")
                return data
        except FileNotFoundError:
            continue
        except json.JSONDecodeError as e:
            st.warning(f"JSON decode error in `{filename}`: {e}")
            continue
    st.error("No valid component map file found. Tried: " + ", ".join(possible_files))
    return {}

# ------------------------------
# Global CSS
# ------------------------------
st.set_page_config(page_title="汉字 Radix", layout="wide")
st.markdown(
    """
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #222;
        }
        .main-title {
            font-size: 2.6em;
            font-weight: 700;
            text-align: center;
            margin-top: 12px;
            margin-bottom: 5px;
        }
        .subtitle {
            text-align: center;
            font-size: 1em;
            color: #555;
            margin-bottom: 25px;
        }

        /* 1. MAIN GRID: The large character in each tile */
        .big-char {
            font-size: 3em;
            line-height: 1;
            text-align: center;
            margin-bottom: 0.3em;
            cursor: pointer;
        }
        .char-btn > button {
            width: 100%;
            padding: 0.5em 0;
            border-radius: 10px;
            background: #fff;
            border: 1px solid #ddd;
            transition: all 0.15s;
        }
        .char-btn > button:hover {
            border-color: #666;
            transform: translateY(-2px);
        }
        .preview-btn > button {
            border: 2px solid #888;
            background: #f8f8f8;
        }
        .selected-btn > button {
            border: 2px solid #2c3e50;
            background: #eef3ff;
        }

        .meta-tag {
            background: #f1f3f5;
            padding: 4px 8px;
            border-radius: 8px;
            font-size: 0.85em;
            color: #333;
            display: inline-block;
            margin-right: 6px;
            margin-bottom: 6px;
        }
        .char-card {
            border: 1px solid #e3e3e3;
            background: #fff;
            padding: 14px 14px;
            border-radius: 14px;
            margin-top: 12px;
            margin-bottom: 14px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05);
        }

        /* 2. SIDEBAR: The Big Red Selected Character */
        .selected-char-sidebar {
            font-size: 3em; 
            text-align: center;
            color: #e74c3c; 
            margin: 20px 0;
            font-weight: bold;
            line-height: 1.2;
        }
        .preview-count-line {
            text-align: center;
            font-size: 0.95em;
            margin-bottom: 14px;
            color: #333;
        }
        .preview-count-line span.char {
            font-weight: 700;
            color: #e74c3c;
        }

        /* 3. RESULTS LIST (RIGHT PANE) */
        .results-header {
            font-size: 1.4em;
            font-weight: bold;
            color: #2c3e50;
            margin: 20px 0 10px 0;
            text-align: center;
        }
        .count-line {
            text-align: center;
            color: #555;
            margin-bottom: 14px;
        }
        .count-line span.char {
            font-weight: 700;
            color: #2c3e50;
        }

        .phrase-card {
            padding: 10px 12px;
            border-radius: 12px;
            border: 1px solid #e6e6e6;
            background: #fff;
            margin-bottom: 8px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        }
        .phrase-title {
            font-size: 1.1em;
            font-weight: 700;
            margin-bottom: 4px;
        }
        .phrase-def {
            color: #555;
            font-size: 0.95em;
            margin-top: 2px;
        }
        .phrase-tags {
            margin-top: 6px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .tag {
            font-size: 0.8em;
            background: #f1f3f5;
            padding: 3px 8px;
            border-radius: 999px;
            color: #333;
        }

        /* 4. Stroke filter group headers */
        .stroke-header {
            font-weight: 700;
            color: #2c3e50;
            margin: 10px 0 6px 0;
            font-size: 0.95em;
        }

        /* 5. Status tags in main area */
        .status-tag {
            display: inline-block;
            background: #f1f3f5;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.85em;
            margin-right: 8px;
            margin-bottom: 8px;
            color: #333;
        }

        /* Keep button appearance consistent */
        button[kind="primary"] {
            border-radius: 10px !important;
        }
        button[kind="secondary"] {
            border-radius: 10px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

# ------------------------------
# Data Load (replaced with robust loader)
# ------------------------------
component_map = load_component_map()

# Critical early exit if no data loaded
if not component_map:
    st.error("No component data loaded. Ensure one of the following files is present in the app directory:\n"
             "- enhanced_component_map_with_etymology.json\n"
             "- component_map.json")
    st.stop()

# Precompute stroke counts and group components (for sidebar filters)
stroke_groups = {}
idc_counts = {}
for c, data in component_map.items():
    meta = data.get("meta", {})
    s = meta.get("strokes", 0)
    if s is None: s = 0
    stroke_groups.setdefault(s, []).append(c)

    idc = meta.get("idc", "none")
    if idc:
        idc_counts[idc] = idc_counts.get(idc, 0) + 1

# Sort groups
for s in stroke_groups:
    stroke_groups[s] = sorted(stroke_groups[s])

# ------------------------------
# Session State Defaults
# ------------------------------
defaults = {
    "page": 1,
    "per_page": 30,
    "stroke_count": 0,
    "radical": "none",
    "component_idc": "none",
    "selected_comp": None,
    "last_valid_selected_comp": None,
    "preview_comp": None,
    "show_inputs": True,
    "rad_groups": stroke_groups,
    "idc_counts": idc_counts,
    "stroke_view_active": False,
    "stroke_view_char": "",
    "text_input_comp": "",
    "text_input_warning": None,
    "display_mode": "Single Character",
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
    st.session_state.script_variant = "None" # Reset filter on back

def end_stroke_view():
    st.session_state.stroke_view_active = False
    st.session_state.stroke_view_char = ""

def reset_all():
    st.session_state.page = 1
    st.session_state.stroke_count = 0
    st.session_state.radical = "none"
    st.session_state.component_idc = "none"
    st.session_state.selected_comp = None
    st.session_state.last_valid_selected_comp = None
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
    strokes = clean_field(meta.get("strokes", ""))
    radical = clean_field(meta.get("radical", ""))
    structure = clean_field(meta.get("idc", ""))
    
    trad = meta.get("traditional", None)
    simp = meta.get("simplified", None)
    
    tags = []
    if pinyin: tags.append(f"<span class='meta-tag'>{pinyin}</span>")
    if strokes: tags.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    if radical: tags.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    if structure: tags.append(f"<span class='meta-tag'>⿰{structure} {get_idc_name(structure)}</span>")
    
    meta_html = "<div>" + " ".join(tags) + "</div>"
    
    trad_simp_html = ""
    if cc_t2s and cc_s2t and simp and trad and simp != trad:
        if c == trad:
            trad_simp_html = f"<span class='meta-tag' style='background:#fff7d6;border:1px solid #ffd98e;'>Trad. → {simp}</span>"
        elif c == simp:
            trad_simp_html = f"<span class='meta-tag' style='background:#fff7d6;border:1px solid #ffd98e;'>Simp. → {trad}</span>"
            
    if trad_simp_html:
        meta_html = "<div>" + " ".join(tags) + trad_simp_html + "</div>"
    
    definition = clean_field(meta.get("definition", ""))
    def_html = f"<div style='margin-top:10px;font-size:1.1em;font-weight:700;'>{definition}</div>" if definition else ""
    
    etymology = clean_field(meta.get("etymology", ""))
    ety_html = ""
    if etymology:
        ety_html = f"<div class='ety-row'>{etymology}</div>"
        
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"

def render_sidebar_preview(c):
    related = component_map.get(c, {}).get("related_characters", [])
    chars_unique = list(set([ch for ch in related if len(ch) == 1]))
    count = len(chars_unique)

    render_stroke_order_sidebar(c)
    st.markdown(
        f"<div class='preview-count-line'>{count} characters with <span class='char'>{c}</span></div>",
        unsafe_allow_html=True
    )
    st.markdown(generate_clean_card_html(c), unsafe_allow_html=True)

def render_stroke_order_sidebar(char: str, size: int = 96):
    """Render a compact, self-contained stroke-order animation for sidebar use.

    This is intentionally separate from the full-page stroke-order view and does not
    modify any stroke-view session state.
    """
    char = (char or "").strip()
    char = char[0] if char else ""
    if not char:
        return

    # Keep the sidebar footprint close to the replaced red-character glyph area.
    # No controls here; click the canvas to replay the animation.
    h = size + 16  # minimal breathing room to keep the sidebar compact

    st_html(
        f"""
        <div style="display:flex; justify-content:center; align-items:center; margin:8px 0;">
          <div id="sb-hw-target" style="width:{size}px; height:{size}px;"></div>
        </div>
        <script>
          (function() {{
            const char = {json.dumps(char, ensure_ascii=False)};

            function loadScript(src) {{
              return new Promise((resolve, reject) => {{
                const s = document.createElement('script');
                s.src = src;
                s.async = true;
                s.onload = () => resolve(src);
                s.onerror = () => {{ try {{ s.remove(); }} catch(e) {{}} reject(new Error(`Failed to load script: ${{src}}`)); }};
                document.head.appendChild(s);
              }});
            }}

            async function ensureLibLoaded() {{
              if (window.HanziWriter) return;
              const sources = [
                'https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js',
                'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'
              ];
              let lastErr = null;
              for (const src of sources) {{
                try {{
                  await loadScript(src);
                  if (window.HanziWriter) return;
                }} catch (e) {{ lastErr = e; }}
              }}
              throw lastErr || new Error('Failed to load HanziWriter');
            }}

            const dataUrls = [
              `https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,
              `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`
            ];

            async function loadCharData() {{
              for (const url of dataUrls) {{
                try {{
                  const res = await fetch(url);
                  if (!res.ok) continue;
                  return await res.json();
                }} catch (e) {{ }}
              }}
              throw new Error('Stroke data not found for this character in hanzi-writer-data.');
            }}

            let writer = null;
            async function init() {{
              try {{
                await ensureLibLoaded();
                await loadCharData(); // validate data exists; writer fetches internally
                writer = window.HanziWriter.create('sb-hw-target', char, {{
                  width: {size},
                  height: {size},
                  padding: 4,
                  showOutline: true,
                  showCharacter: false,
                  delayBetweenStrokes: 120,
                  strokeAnimationSpeed: 1.2
                }});
                // Auto-preview once on load
                writer.animateCharacter();
                // Replay on click
                const el = document.getElementById('sb-hw-target');
                if (el) {{
                  el.style.cursor = 'pointer';
                  el.addEventListener('click', () => writer && writer.animateCharacter());
                }}
              }} catch (e) {{
                // Fail silently in sidebar; the rest of the app should remain usable.
              }}
            }}

            init();
          }})();
        </script>
        """,
        height=h,
    )

def render_stroke_order_view(char: str):
    char = (char or "").strip()
    char = char[0] if char else ""

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
              <button id="hw-prev">Back</button>
              <button id="hw-next">Next</button>
              <button id="hw-reset">Reset</button>
              <button id="hw-animate">Animate</button>
            </div>
            <div id="hw-status" style="margin-top:10px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; color:#444;"></div>
            <div id="hw-error" style="margin-top:10px; color:#b00020;"></div>
          </div>
        </div>
        <script>
          (function() {{
            const char = {json.dumps(char, ensure_ascii=False)};
            
            const statusEl = document.getElementById('hw-status');
            const errEl = document.getElementById('hw-error');

            function loadScript(src) {{
              return new Promise((resolve, reject) => {{
                const s = document.createElement('script');
                s.src = src;
                s.async = true;
                s.onload = () => resolve(src);
                s.onerror = () => {{
                  try {{ s.remove(); }} catch(e) {{}}
                  reject(new Error(`Failed to load script: ${{src}}`));
                }};
                document.head.appendChild(s);
              }});
            }}

            async function ensureLibLoaded() {{
              if (window.HanziWriter) return;

              const sources = [
                'https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js',
                'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'
              ];

              let lastErr = null;
              for (const src of sources) {{
                try {{
                  await loadScript(src);
                  if (window.HanziWriter) return;
                }} catch (e) {{
                  lastErr = e;
                }}
              }}
              throw new Error('Failed to load HanziWriter library. All configured CDNs were unreachable.');
            }}

            const dataUrls = [
              `https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`,
              `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`
            ];

            async function loadCharData() {{
              for (const url of dataUrls) {{
                try {{
                  const res = await fetch(url);
                  if (!res.ok) continue;
                  return await res.json();
                }} catch (e) {{
                }}
              }}
              throw new Error('Stroke data not found for this character in hanzi-writer-data.');
            }}

            let writer = null;
            let i = -1;
            let total = 0;

            function setStatus() {{
              statusEl.textContent = `Stroke: ${{Math.max(i+1, 0)}} / ${{total}}`;
            }}

            async function init() {{
              try {{
                await ensureLibLoaded();
                const charData = await loadCharData();
                total = (charData.medians || []).length || 0;

                writer = window.HanziWriter.create('hw-target', char, {{
                  width: 420,
                  height: 420,
                  padding: 10,
                  showOutline: true,
                  showCharacter: false,
                  strokeAnimationSpeed: 1.2
                }});

                setStatus();
              }} catch (e) {{
                errEl.textContent = e.message || String(e);
              }}
            }}

            async function nextStroke() {{
              if (!writer) return;
              if (i < total - 1) {{
                i++;
                await writer.animateStroke(i);
              }}
              setStatus();
            }}

            async function prevStroke() {{
              if (!writer) return;
              if (i >= 0) {{
                i--;
                writer.hideCharacter();
                for (let k = 0; k <= i; k++) {{
                  await writer.animateStroke(k);
                }}
                setStatus();
              }}
            }}

            function resetAll() {{
              if (!writer) return;
              i = -1;
              writer.hideCharacter();
              setStatus();
            }}

            async function animateAll() {{
              if (!writer) return;
              i = -1;
              writer.hideCharacter();
              await writer.animateCharacter();
              i = total - 1;
              setStatus();
            }}

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

# Utility functions
def clean_field(x):
    if x is None: return ""
    if isinstance(x, str):
        return x.strip()
    return str(x).strip()

def get_idc_name(idc):
    mapping = {
        "⿰": "Left-Right",
        "⿱": "Top-Bottom",
        "⿲": "Left-Middle-Right",
        "⿳": "Top-Middle-Bottom",
        "⿴": "Enclosure",
        "⿵": "Enclosure (Top)",
        "⿶": "Enclosure (Bottom)",
        "⿷": "Enclosure (Left)",
        "⿸": "Enclosure (Upper-left)",
        "⿹": "Enclosure (Upper-right)",
        "⿺": "Enclosure (Lower-left)",
        "⿻": "Overlay"
    }
    return mapping.get(idc, "")

# ------------------------------
# Header
# ------------------------------
st.markdown("<div class='main-title'>汉字 Radix</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Explore Chinese characters by strokes, radicals, and structure.</div>", unsafe_allow_html=True)

# ------------------------------
# Layout
# ------------------------------
sidebar = st.sidebar

# Sidebar content
with sidebar:
    if st.session_state.show_inputs:
        st.markdown("### Filters")

        # Text input
        st.text_input("Jump to character", key="w_text", value=st.session_state.text_input_comp, on_change=sync_text)
        if st.session_state.text_input_warning:
            st.warning(st.session_state.text_input_warning)

        # Reset button
        st.button("Reset all filters", on_click=reset_all, use_container_width=True)

        st.markdown("---")

        # Stroke filter
        stroke_label = f"Strokes: {st.session_state.stroke_count}" if st.session_state.stroke_count > 0 else "Strokes (Any)"
        with st.expander(stroke_label, expanded=False):
            if st.button("Clear Strokes", use_container_width=True):
                st.session_state.stroke_count = 0
                st.session_state.page = 1
                st.rerun()
            groups = st.session_state.rad_groups
            for s in sorted(groups.keys()):
                st.markdown(f"<div class='stroke-header'>{s if s!=999 else '?'} Strokes</div>", unsafe_allow_html=True)
                chars = groups[s]
                cols = st.columns(5)
                for i, ch in enumerate(chars):
                    is_selected = (st.session_state.stroke_count == s)
                    with cols[i % 5]:
                        if st.button(str(s), key=f"stroke_{s}_{i}", type="primary" if is_selected else "secondary"):
                            st.session_state.stroke_count = s
                            st.session_state.page = 1
                            st.rerun()

        # Radical filter
        rad_label = f"Radical: {st.session_state.radical}" if st.session_state.radical != "none" else "Radical (Any)"
        with st.expander(rad_label, expanded=False):
            if st.button("Clear Radical", use_container_width=True):
                st.session_state.radical = "none"
                st.session_state.page = 1
                st.rerun()
            groups = st.session_state.rad_groups
            for s in sorted(groups.keys()):
                st.markdown(f"<div class='stroke-header'>{s if s!=999 else '?'} Strokes</div>", unsafe_allow_html=True)
                rads = groups[s]
                cols = st.columns(5)
                for i, r in enumerate(rads):
                    is_selected = (st.session_state.radical == r)
                    with cols[i % 5]:
                        if st.button(r, key=f"rad_{r}", type="primary" if is_selected else "secondary"):
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
                is_selected = (st.session_state.component_idc == idc)
                with idc_cols[i % 5]:
                    if st.button(idc, key=f"idc_{idc}", type="primary" if is_selected else "secondary"):
                        st.session_state.component_idc = idc
                        st.session_state.page = 1
                        st.rerun()
        st.markdown("---")
        if st.session_state.preview_comp:
            render_sidebar_preview(st.session_state.preview_comp)

    else:
        # RESULTS SIDEBAR
        st.button("← Back to list", on_click=back, use_container_width=True)

        so_char = (st.session_state.selected_comp or "").strip()[:1]

        render_stroke_order_sidebar(so_char)

        # --- MOVED FILTER HERE ---
        st.selectbox(
            "Filter Results",
            options=["None", "Simplified", "Traditional"],
            key="w_script",
            index=["None", "Simplified", "Traditional"].index(st.session_state.script_variant),
            on_change=sync_script
        )
        # -------------------------

        related = component_map[st.session_state.selected_comp].get("related_characters", [])
        chars_unique = list(set([c for c in related if len(c) == 1]))

        # Apply script filter
        if st.session_state.script_variant != "None" and cc_t2s and cc_s2t:
            filtered = []
            for c in chars_unique:
                if st.session_state.script_variant == "Simplified":
                    if cc_t2s.convert(c) == c and cc_s2t.convert(c) != c:
                        filtered.append(c)
                elif st.session_state.script_variant == "Traditional":
                    if cc_s2t.convert(c) == c and cc_t2s.convert(c) != c:
                        filtered.append(c)
            chars_unique = filtered

        valid_chars = [c for c in chars_unique if c in component_map]
        count = len(valid_chars)
        st.markdown(f"<div class='count-line'>{count} results for <span class='char'>{st.session_state.selected_comp}</span></div>", unsafe_allow_html=True)

        modes = ["Single Character", "2-Character Phrases", "3-Character Phrases", "4-Character Phrases"]
        st.radio("", options=modes, index=modes.index(st.session_state.display_mode), key="w_display", on_change=sync_display)

# ------------------------------
# Main Area Content
# ------------------------------
if st.session_state.stroke_view_active:
    render_stroke_order_view(st.session_state.stroke_view_char)
    st.stop()


if st.session_state.show_inputs:
    filter_parts = []
    if st.session_state.stroke_count > 0:
        filter_parts.append(f"<span class='status-tag'>{st.session_state.stroke_count} strokes</span>")
    if st.session_state.radical != "none":
        filter_parts.append(f"<span class='status-tag'>Radical {st.session_state.radical}</span>")
    if st.session_state.component_idc != "none":
        filter_parts.append(f"<span class='status-tag'>Structure {st.session_state.component_idc} ({get_idc_name(st.session_state.component_idc)})</span>")

    if filter_parts:
        st.markdown(" ".join(filter_parts), unsafe_allow_html=True)

    # Filter components list
    comps = list(component_map.keys())
    if st.session_state.stroke_count > 0:
        comps = [c for c in comps if component_map[c].get("meta", {}).get("strokes", 0) == st.session_state.stroke_count]
    if st.session_state.radical != "none":
        comps = [c for c in comps if component_map[c].get("meta", {}).get("radical", "") == st.session_state.radical]
    if st.session_state.component_idc != "none":
        comps = [c for c in comps if component_map[c].get("meta", {}).get("idc", "") == st.session_state.component_idc]

    comps = sorted(comps)

    total = len(comps)
    per_page = st.session_state.per_page
    max_page = max(1, math.ceil(total / per_page))
    page = st.session_state.page
    if page > max_page:
        st.session_state.page = max_page
        page = max_page

    start = (page - 1) * per_page
    end = start + per_page
    current = comps[start:end]

    st.markdown(f"<div class='results-header'>{total} components</div>", unsafe_allow_html=True)

    # Pagination controls
    colp1, colp2, colp3 = st.columns([1,2,1])
    with colp1:
        if st.button("Prev page", disabled=page<=1):
            st.session_state.page -= 1
            st.rerun()
    with colp2:
        st.markdown(f"<div style='text-align:center;margin-top:0.6em;'>Page {page} / {max_page}</div>", unsafe_allow_html=True)
    with colp3:
        if st.button("Next page", disabled=page>=max_page):
            st.session_state.page += 1
            st.rerun()

    # Grid display
    cols = st.columns(6)
    for i, ch in enumerate(current):
        is_preview = st.session_state.preview_comp == ch
        btn_key = f"tile_{ch}_{i}"
        with cols[i % 6]:
            classes = "char-btn"
            if is_preview:
                classes += " preview-btn"
            if st.session_state.selected_comp == ch and not st.session_state.show_inputs:
                classes += " selected-btn"
            st.markdown(f"<div class='{classes}'>", unsafe_allow_html=True)
            if st.button(ch, key=btn_key):
                tile_click(ch)
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

else:
    # Results view
    comp = st.session_state.selected_comp
    st.markdown(generate_clean_card_html(comp), unsafe_allow_html=True)

    related = component_map[comp].get("related_characters", [])
    chars_unique = list(set([c for c in related if len(c) == 1]))

    # Apply script filter
    if st.session_state.script_variant != "None" and cc_t2s and cc_s2t:
        filtered = []
        for c in chars_unique:
            if st.session_state.script_variant == "Simplified":
                if cc_t2s.convert(c) == c and cc_s2t.convert(c) != c:
                    filtered.append(c)
            elif st.session_state.script_variant == "Traditional":
                if cc_s2t.convert(c) == c and cc_t2s.convert(c) != c:
                    filtered.append(c)
        chars_unique = filtered

    # Filter by display mode
    mode = st.session_state.display_mode
    if mode == "Single Character":
        display_items = [c for c in chars_unique if c in component_map]
        st.markdown(f"<div class='results-header'>{len(display_items)} characters</div>", unsafe_allow_html=True)
        cols = st.columns(6)
        for i, c in enumerate(sorted(display_items)):
            with cols[i % 6]:
                st.markdown(f"<div class='big-char'>{c}</div>", unsafe_allow_html=True)
                if st.button("🖊️", key=f"stroke_btn_{c}", help="View stroke order"):
                    st.session_state.stroke_view_char = c
                    st.session_state.stroke_view_active = True
                    st.rerun()
    else:
        # Phrase modes
        phrases = component_map[comp].get("phrases", [])
        n = int(mode[0])  # 2, 3, 4
        phrases = [p for p in phrases if len(p.get("phrase", "")) == n]
        st.markdown(f"<div class='results-header'>{len(phrases)} phrases</div>", unsafe_allow_html=True)
        for p in phrases:
            phrase = p.get("phrase", "")
            definition = p.get("definition", "")
            tags = p.get("tags", [])
            tag_html = "".join([f"<span class='tag'>{t}</span>" for t in tags])
            st.markdown(
                f"""
                <div class='phrase-card'>
                    <div class='phrase-title'>{phrase}</div>
                    <div class='phrase-def'>{definition}</div>
                    <div class='phrase-tags'>{tag_html}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
