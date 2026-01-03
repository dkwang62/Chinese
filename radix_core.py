# radix_core.py
# All non-UI logic, data loading, helpers and HTML generators for Radix

import json
import math
import html
import sqlite3
import unicodedata
import gc
import base64
import json as json_module  # for dumps in HTML
from typing import List, Dict, Optional
import copy

# --- Optional: OpenCC for Traditional/Simplified Conversion ---
try:
    from opencc import OpenCC
    cc_t2s = OpenCC("t2s")
    cc_s2t = OpenCC("s2t")
except ImportError:
    cc_t2s = None
    cc_s2t = None

IDC_CHARS = {"⿰", "⿱", "⿲", "⿳", "⿴", "⿵", "⿶", "⿷", "⿸", "⿹", "⿺", "⿻"}
SCRIPT_FILTERS = ["Any", "Simplified", "Traditional"]

# --- Global SUBTLEX-CH frequency dict ---
SUBTLEX_FREQ: Dict[str, float] = {}  # simplified char -> freq per million

# --- SUBTLEX-CH Frequency Badge (Percentile-Based) ---
# Pre-defined percentile thresholds (based on distribution of SUBTLEX-CH data)
FREQ_PERCENTILES = {
    'p95': 8500,  # Top 5% of words
    'p75': 3200,  # Top 25% of words
    'p50': 800,   # Top 50% of words (median)
    'p25': 150    # Bottom 25% of words
}

def load_subtlex_freq():
    """Load SUBTLEX-CH character frequencies from SUBTLEX-CH-CHR.txt (GBK encoded)"""
    global SUBTLEX_FREQ
    try:
        with open("SUBTLEX-CH-CHR.txt", "r", encoding="gbk") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("Character") or line.startswith("Total"):
                    continue
                parts = line.split("\t")
                if len(parts) < 3:
                    continue
                char = parts[0].strip()
                try:
                    freq_per_million = float(parts[2])
                    if freq_per_million > 0:
                        SUBTLEX_FREQ[char] = freq_per_million
                except ValueError:
                    continue
        print(f"[Radix] Loaded {len(SUBTLEX_FREQ)} characters from SUBTLEX-CH frequency list")
    except FileNotFoundError:
        print("[Radix] SUBTLEX-CH-CHR.txt not found — frequency badges disabled")
    except Exception as e:
        print(f"[Radix] Error loading SUBTLEX-CH frequencies: {e}")


# --- Data Loading & Augmentation ---
def load_and_augment_map():
    try:
        filename = "enhanced_component_map_with_etymology.json"
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
            data = json.loads(content)
            
    except json.JSONDecodeError as e:
        print(f"\n[Radix Critical Error] JSON Syntax Error in {filename}")
        print(f"Error details: {e.msg}")
        print(f"Location: Line {e.lineno}, Column {e.colno}")
        return {}
    except FileNotFoundError:
        return {}

    # Load SUBTLEX frequencies first
    load_subtlex_freq()

    for char, info in data.items():
        meta = info.get("meta", {})
        rel = info.get("related_characters", [])
        info['usage_count'] = len({c for c in rel if isinstance(c, str) and len(c) == 1})

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

        # Add SUBTLEX frequency (map via simplified variant)
        lookup_char = cc_t2s.convert(char) if cc_t2s else char
        info['freq_per_million'] = SUBTLEX_FREQ.get(lookup_char, 0.0)

    gc.collect()
    return data


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


component_map = load_and_augment_map()
stats_cache = get_component_stats(component_map) if component_map else {}


# --- Database ---
def get_db_connection():
    try:
        conn = sqlite3.connect("phrases.db", check_same_thread=False)
        return conn
    except Exception:
        return None


def batch_get_phrase_details(words, conn):
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


def search_phrases_by_definition(search_term: str, conn, limit: int = 50):
    """Search phrases by English definition/meaning"""
    if not conn or not search_term:
        return []
    try:
        cursor = conn.cursor()
        query = "SELECT word, pinyin, meanings FROM phrases WHERE meanings LIKE ? LIMIT ?"
        cursor.execute(query, (f"%{search_term}%", limit))
        results = cursor.fetchall()
        return [{"word": row[0], "pinyin": row[1], "meanings": row[2]} for row in results]
    except Exception:
        return []


# --- Pure Helpers ---
def get_stroke_count(char):
    return component_map.get(char, {}).get("stroke_count")


def component_usage_count(comp: str) -> int:
    return component_map.get(comp, {}).get("usage_count", 0)


def sort_key_usage_primary(ch: str):
    """Current smart sort: usage first, then frequency"""
    info = component_map.get(ch, {})
    use = info.get('usage_count', 0)
    freq = info.get('freq_per_million', 0.0)
    strokes = info.get('stroke_count') or 999

    group = 0 if use >= 5 else 1
    if group == 0:
        return (group, -use, -freq, strokes, ch)
    else:
        return (group, -freq, strokes, ch)


def sort_key_frequency_primary(ch: str):
    """Pure frequency sort: highest SUBTLEX-CH first"""
    info = component_map.get(ch, {})
    freq = info.get('freq_per_million', 0.0)
    use = info.get('usage_count', 0)
    strokes = info.get('stroke_count') or 999

    return (-freq, -use, strokes, ch)  # Highest freq first, then usage as tiebreaker

def apply_script_filter(chars: List[str], script_filter: str) -> List[str]:
    if script_filter == "Any":
        return chars
    if script_filter == "Simplified":
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

def get_default_prompt_config() -> dict:
    """Default prompt configuration with 3 tasks (matches original design)"""
    return {
        "version": 1,
        "preamble": (
            "You are a bilingual Chinese dictionary editor and teacher.\n\n"
            "Explain a single Chinese character in depth for language learners. "
            "Focus on modern usage, and if the character is rare, show its more widely used modern equivalent while noting the original character.\n\n"
            "⸻\n\n"
        ),
        "tasks": [
            {
                "id": "task1",
                "title": "Task 1 — Character Analysis",
                "template": (
                    "Task 1 — Character Analysis\n\n"
                    "For the Hanzi below, provide:\n"
                    "\t1.\tOriginal meaning — briefly note the ancient form or origin only if it helps understand modern usage.\n"
                    "\t2.\tCore semantic concept — summarize the main idea in modern context.\n"
                    "\t3.\tWhy it is used in compound characters — explain how it contributes meaning to words in everyday or contemporary Chinese.\n"
                    "\t4.\tThree example words — include pinyin and natural English meanings, using modern common usage.\n"
                    "\t5.\tOne modern usage sentence — show the character in real-life context; if the character is rare, use the modern equivalent and note it.\n\n"
                    "⸻\n\n"
                ),
            },
            {
                "id": "task2",
                "title": "Task 2 — Example Sentences and Images",
                "template": (
                    "Task 2 — Example Sentences and Images\n\n"
                    "Provide two example sentences that best illustrate modern, everyday usage of the character (or its modern equivalent if the original is rare). For each sentence, include:\n"
                    "a) Traditional Chinese\n"
                    "b) Simplified Chinese\n"
                    "c) Natural English translation\n"
                    "d) Target word/phrase (must include the character or its modern equivalent)\n"
                    "e) Read-aloud pinyin of the full sentence (with tone marks and natural word grouping)\n\n"
                    "Images:\n"
                    "\t•\tIf the character represents a concrete object, generate a realistic image showing its material, context, and typical use.\n"
                    "\t•\tIf the character represents an abstract concept, quality, or person, do not generate an image.\n\n"
                    "Note: Only generate images in Task 2 to avoid overlap with analysis or conceptual comparisons.\n\n"
                    "⸻\n\n"
                ),
            },
            {
                "id": "task3",
                "title": "Task 3 — Conceptual Contrast",
                "template": (
                    "Task 3 — Conceptual Contrast\n\n"
                    "Compare this character with 2–3 other characters of similar meaning or usage, including pinyin. Explain:\n"
                    "\t•\tHow Chinese divides this concept into different semantic or conceptual systems in modern language usage.\n"
                    "\t•\tHow the characters differ in real-life usage, highlighting subtle distinctions learners should know.\n"
                    "\t•\tDo not repeat example sentences from Task 2; only discuss relationships and usage distinctions.\n\n"
                    "⸻\n\n"
                ),
            },
        ],
        "epilogue": "Hanzi: {char}\n- English definition: {def_en}\n",
    }


def normalize_prompt_config(cfg: dict | None) -> dict:
    base = get_default_prompt_config()
    if not isinstance(cfg, dict):
        return base

    out = {
        "version": base.get("version", 1),
        "preamble": base.get("preamble", ""),
        "epilogue": base.get("epilogue", ""),
        "tasks": list(base.get("tasks", [])),
    }

    # preamble/epilogue overrides
    if isinstance(cfg.get("preamble"), str):
        out["preamble"] = cfg["preamble"]
    if isinstance(cfg.get("epilogue"), str):
        out["epilogue"] = cfg["epilogue"]

    # tasks overrides (validated + cleaned)
    tasks = cfg.get("tasks")
    if isinstance(tasks, list):
        cleaned = []
        seen = set()
        for t in tasks:
            if not isinstance(t, dict):
                continue
            tid = str(t.get("id", "")).strip()
            if not tid or tid in seen:
                continue
            title = str(t.get("title", tid)).strip() or tid
            template = t.get("template", "")
            if not isinstance(template, str) or not template.strip():
                continue
            cleaned.append({"id": tid, "title": title, "template": template})
            seen.add(tid)

        if cleaned:
            out["tasks"] = cleaned

    return out


def get_char_definition_en(char: str) -> str:
    char = (char or "").strip()[:1]
    meta = component_map.get(char, {}).get("meta", {})
    return clean_field(meta.get("definition", ""))

def render_combined_prompt(
    char: str,
    prompt_config: dict | None,
    selected_task_ids: list[str] | None,
    definition_en: str = "",
) -> str:
    cfg = normalize_prompt_config(prompt_config)
    char = (char or "").strip()[:1]
    preamble = cfg.get("preamble", "")
    epilogue = cfg.get("epilogue", "")
    tasks = cfg.get("tasks", []) or []

    selected_set = set(selected_task_ids or [])
    parts = []
    for t in tasks:
        tid = t.get("id")
        if tid in selected_set:
            parts.append(t.get("template", ""))

    full = preamble + "".join(parts) + epilogue
    # Only replace placeholders we explicitly support.
    return full.format(char=char, def_en=definition_en or "")

def build_chatgpt_prompt(char: str) -> str:
    """Backward-compatible single-string prompt (selects ALL tasks by default)."""
    char = (char or "").strip()[:1]
    cfg = get_default_prompt_config()
    selected = [t.get("id") for t in cfg.get("tasks", []) if t.get("id")]
    def_en = get_char_definition_en(char)
    return render_combined_prompt(char, cfg, selected, definition_en=def_en)


def generate_clean_card_html(c: str, usage_count: Optional[int] = None, is_static: bool = False, minimal: bool = False) -> str:
    """
    Generate clean HTML card.
    Args:
        minimal (bool): If True, renders lightweight badges (standard browser tooltips) instead of heavy HTML tooltips.
    """
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

    # --- 1. Build Meta Items (Badges) ---
    meta_items = []
    
    # Pinyin
    if pinyin and pinyin != "—":
        meta_items.append(f"<span class='meta-pinyin'>{pinyin}</span>")
    
    # Strokes
    if strokes:
        meta_items.append(f"<span class='meta-tag'>{strokes} strokes</span>")
    
    # Radical
    if radical and radical != "—":
        meta_items.append(f"<span class='meta-tag'>Rad. {radical}</span>")
    
    # Decomposition
    if decomp and decomp != "—":
        meta_items.append(f"<span class='meta-tag'>{decomp}</span>")
    
    # --- Usage Badge ---
    if usage_count is not None and usage_count > 0:
        if minimal:
            # Lightweight version
            meta_items.append(f"<span class='meta-tag' title='Used in {usage_count} characters. Click to drill down.'>Used in {usage_count} chars</span>")
        else:
            # Full HTML tooltip version
            if is_static:
                tip_content = f"💡 <strong>Static View:</strong> Copy and paste <strong>{c}</strong> into the search box to explore related chars."
            else:
                tip_content = f"✨ <strong>Interactive Tip:</strong><br>1. Click <strong>{c}</strong> once to preview in sidebar.<br>2. Click <strong>{c}</strong> again to drill down into the {usage_count} related characters."

            meta_items.append(
                f"<div class='radix-tooltip'>"
                f"   <span class='meta-tag' style='border-bottom: 2px dotted #aaa;'>Used in {usage_count} chars</span>"
                f"   <span class='radix-tooltiptext'>{tip_content}</span>"
                f"</div>"
            )

    # --- Frequency Badge ---
    freq = info.get('freq_per_million', 0.0)
    if freq > 0:
        if freq >= FREQ_PERCENTILES['p95']:
            label, color = "Top 5%", "#2e7d32"
        elif freq >= FREQ_PERCENTILES['p75']:
            label, color = "Top 25%", "#558b2f"
        elif freq >= FREQ_PERCENTILES['p50']:
            label, color = "Above Average", "#ff8f00"
        elif freq >= FREQ_PERCENTILES['p25']:
            label, color = "Below Average", "#f57c00"
        else:
            label, color = "Bottom 25%", "#c62828"
            
        if minimal:
            # Lightweight version - standard title attribute
            meta_items.append(
                f"<span class='meta-tag' title='Frequency: {label} ({freq:,.0f}/M)' style='background: linear-gradient(135deg, {color}15 0%, {color}25 100%); color: {color}; border: 1px solid {color}40; font-weight:700; cursor: help;'>"
                f"Freq: {label}"
                f"</span>"
            )
        else:
            # Full HTML tooltip version
            legend_content = (
                "<strong>📊 Frequency Guide</strong><br><br>"
                "<strong>Top 5% (Essential):</strong> Core survival vocabulary.<br>"
                "<strong>Top 25% (Common):</strong> Standard for news & business.<br>"
                "<strong>Above Average:</strong> Topic-specific (e.g. Science).<br>"
                "<strong>Below Average:</strong> Literary & enrichment words.<br>"
                "<strong>Bottom 25%:</strong> Rare, archaic, or very specific names."
            )

            meta_items.append(
                f"<div class='radix-tooltip'>"
                f"   <span class='meta-tag' style='background: linear-gradient(135deg, {color}15 0%, {color}25 100%); "
                f"         color: {color}; border: 1px solid {color}40; font-weight:700; cursor: help;'>"
                f"     Frequency: {label} ({freq:,.0f}/M)"
                f"   </span>"
                f"   <span class='radix-tooltiptext' style='width:250px;'>{legend_content}</span>"
                f"</div>"
            )
    else:
        # No Data case
        if minimal:
             meta_items.append(f"<span class='meta-tag' style='color:#999;'>Freq: No Data</span>")
        else:
            meta_items.append(
                f"<div class='radix-tooltip'>"
                f"   <span class='meta-tag' style='color:#999;'>Freq: No Data</span>"
                f"   <span class='radix-tooltiptext'>No frequency data available in SUBTLEX-CH for this character.</span>"
                f"</div>"
            )

    # Script variant tags
    if cc_t2s:
        simplified = cc_t2s.convert(c)
        if simplified != c:
            meta_items.append(f"<span class='meta-tag meta-tag-trad'>Trad. → {simplified}</span>")
    if cc_s2t:
        traditional = cc_s2t.convert(c)
        if traditional != c:
            meta_items.append(f"<span class='meta-tag meta-tag-simp'>Simp. → {traditional}</span>")

    meta_html = f"<div class='meta-row' style='display:flex; flex-wrap:wrap; gap:8px; align-items:center;'>{''.join(meta_items)}</div>"
    def_html = f"<div class='def-row'>{definition}</div>" if definition and definition != "—" else ""
    ety_html = f"<div class='ety-row'>{etymology}</div>" if etymology else ""
    
    return f"<div class='char-card'>{meta_html}{def_html}{ety_html}</div>"


# --- iPad-Safe Download HTML ---
def render_ipad_safe_download_html(data_str: str, filename: str, label: str) -> str:
    b64 = base64.b64encode(data_str.encode()).decode()
    href = f'data:application/octet-stream;base64,{b64}'
    return f"""
    <div style="text-align:center; margin: 10px 0;">
        <a href="{href}" download="{filename}" target="_self" style="
            text-decoration: none;
            color: white;
            background-color: #d35400;
            padding: 12px 24px;
            border-radius: 12px;
            font-weight: 700;
            display: inline-block;
            box-shadow: 0 4px 12px rgba(211, 84, 0, 0.2);
            -webkit-appearance: none;
        ">
            {label}
        </a>
    </div>
    """

# --- Stroke Order Sidebar HTML ---
def get_stroke_order_sidebar_html(char: str, size: int = 140) -> tuple[str, int]:
    char = (char or "").strip()[:1]
    if not char:
        return "", 0
    pinyin = clean_field(component_map.get(char, {}).get("meta", {}).get("pinyin", ""))
    h = size + 80
    html_content = f"""
    <div style="display:flex; flex-direction:column; align-items:center; margin:20px 0;">
        <div style="text-align:center; font-size:2.5rem; font-weight:bold; color:#e67e22; margin-bottom:10px;">{pinyin}</div>
        <div id="sb-hw-{hash(char)}" style="width:{size}px; height:{size}px;"></div>
        <div style="font-size:11px; color:#666; text-align:center; margin-top:5px;">
            🔄 Continuous animation (keeps session alive)
        </div>
    </div>
    <script>
    (function() {{
        const char = {json_module.dumps(char, ensure_ascii=False)};
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
                    strokeAnimationSpeed: 1.5, delayBetweenStrokes: 80  // Slightly faster for continuous
                }});
                
                // INFINITE ANIMATION LOOP - keeps page alive
                async function continuousAnimation() {{
                    while (true) {{
                        // Animate once
                        writer.hideCharacter();
                        await writer.animateCharacter();
                        writer.showCharacter();
                        
                        // Optional: Speak every 5th animation
                        if (Math.random() < 0.2) {{  // 20% chance per cycle
                            speak(char);
                        }}
                        
                        // Wait 2 seconds before next animation
                        await new Promise(r => setTimeout(r, 2000));
                    }}
                }}
                
                // Start the infinite loop
                continuousAnimation().catch(console.error);
                
                // Keep existing click/touch functionality
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
                
                // Optional: Log to console for debugging
                console.log(`Sidebar infinite animation started for ${{char}}`);
                
            }} catch(e) {{
                console.error("HanziWriter init failed:", e);
                document.getElementById(target).innerHTML = `<div style="font-size:${{size*0.7}}px; line-height:${{size}}px; text-align:center;">${{char}}</div>`;
            }}
        }}
        init();
    }})();
    </script>
    """
    return html_content, h



# --- Full Stroke Order View HTML ---
def get_stroke_order_view_html(primary_char: str, display_mode: str) -> tuple[str, Optional[str]]:
    primary_char = (primary_char or "").strip()[:1]
    if not primary_char:
        return "<p>No character selected.</p>", None

    s_char = cc_t2s.convert(primary_char) if cc_t2s else primary_char
    t_char = cc_s2t.convert(primary_char) if cc_s2t else primary_char

    chars_to_show = list(dict.fromkeys([c for c in [s_char, t_char] if c]))

    BOX_SIZE = 280
    container_html = ""
    for i, c in enumerate(chars_to_show):
        label_text = ""
        if s_char != t_char:
            label_text = "Simplified" if c == s_char else "Traditional"
        label_html = f"<div style='text-align:center; font-weight:bold; color:#555; margin-bottom:5px;'>{label_text}</div>" if label_text else ""
        pinyin = clean_field(component_map.get(c, {}).get("meta", {}).get("pinyin", ""))
        container_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center;">
            {label_html}
            <div style="font-size:2.5rem; color:#e67e22; font-weight:bold; margin-bottom:10px;">{pinyin}</div>
            <div id="hw-target-{i}" style="width:{BOX_SIZE}px;height:{BOX_SIZE}px;border:1px solid #e0e0e0;border-radius:12px; background:white;"></div>
        </div>
        """

    # Phrases HTML — strictly 800px max-width
    phrases_html = None
    if display_mode != "Single Character" and primary_char:
        n = {"2-Characters": 2, "3-Characters": 3, "4-Characters": 4}.get(display_mode, 0)
        meta_compounds = component_map.get(primary_char, {}).get("meta", {}).get("compounds", [])
        relevant = [w for w in meta_compounds if isinstance(w, str) and len(w) == n]
        if relevant:
            db_conn = get_db_connection()
            if db_conn:
                phrases_map = batch_get_phrase_details(sorted(relevant), db_conn)
                items = []
                for word in sorted(relevant):
                    entry = phrases_map.get(word)
                    if entry:
                        pinyin = entry.get("pinyin", "")
                        meanings = html.escape(entry.get("meanings", "")[:100] + ("..." if len(entry.get("meanings", "")) > 100 else ""))
                        items.append(f"<div class='compound-item'>"
                                     f"<span class='cp-word'>{word}</span>"
                                     f"<span class='cp-pinyin'>{pinyin}</span>"
                                     f"<span class='cp-mean'>{meanings}</span>"
                                     f"</div>")
                    else:
                        items.append(f"<div class='compound-item'><span class='cp-word'>{word}</span></div>")
                phrases_html = f"""
                <div style='padding:15px; background:#f1f8e9; border-radius:8px; 
                             margin:10px auto; border:1px solid #dcedc8; max-width:800px; max-height:400px; overflow-y:auto;'>
                  <div style='font-weight:bold; margin-bottom:10px; color:#2e7d32; 
                       border-bottom:2px solid #a5d6a7; padding-bottom:5px; text-align:center;'>
                    {display_mode} containing {primary_char}
                  </div>
                  {''.join(items)}
                </div>
                """

    full_html = f"""
    <div style="display:flex; gap:15px; align-items:flex-start; flex-wrap:wrap; justify-content:center;">
        {container_html}
    </div>
    <div style="display:flex; justify-content:center; margin-top:15px; gap:8px;">
         <button id="hw-reset">Reset</button><button id="hw-animate">Replay Animation</button>
    </div>
    <div id="hw-error" style="margin-top:10px; color:#b00020; text-align:center;"></div>
    <script>
    (function() {{
        const chars = {json_module.dumps(chars_to_show, ensure_ascii=False)};
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
            for (let k = 0; k < 30; k++) {{
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
    """
    return full_html, phrases_html
