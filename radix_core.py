# radix_core.py - CLEANED VERSION
# Core logic using consolidated utilities from radix_utils

import json
import math
import html
import sqlite3
import gc
import json as json_module
from typing import List, Dict, Optional

# Import new utilities
from radix_utils import (
    normalize_stroke_count, get_char_field, get_variant_char,
    get_both_variants, clean_field as util_clean_field, deduplicate_list
)
from radix_html import build_phrase_list

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
SUBTLEX_FREQ: Dict[str, float] = {}

FREQ_PERCENTILES = {
    'p95': 8500,
    'p75': 3200,
    'p50': 800,
    'p25': 150
}

def load_subtlex_freq():
    global SUBTLEX_FREQ
    try:
        with open("SUBTLEX-CH-CHR.txt", "r", encoding="gbk") as f:
            for line in f:
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
        print(f"[Radix] Loaded {len(SUBTLEX_FREQ)} characters from SUBTLEX-CH")
    except FileNotFoundError:
        print("[Radix] SUBTLEX-CH-CHR.txt not found")
    except Exception as e:
        print(f"[Radix] Error loading frequencies: {e}")

# Standard radical order
XINHUA_RADICAL_ORDER = [
    '一', '丨', '丿', '丶', '乙', '二', '亠', '人', '儿', '入', '八', '冂', '冖', '冫', '几', '凵', '刀', '力', '勹', '匕', '匚', '卜', '卩', '厂', '厶', '又', '十', '讠', '阝', '刂',
    '口', '囗', '土', '士', '夂', '夊', '夕', '大', '女', '子', '宀', '寸', '小', '尢', '尸', '屮', '山', '川', '工', '己', '巾', '干', '幺', '广', '廴', '廾', '弋', '弓', '彐', '彡', '彳', '扌', '艹', '艸',
    '心', '戈', '戶', '手', '支', '攴', '文', '斗', '斤', '方', '无', '日', '曰', '月', '木', '欠', '止', '歹', '殳', '毋', '比', '毛', '氏', '气', '水', '火', '爪', '父', '爻', '片', '牙', '牛', '犬', '王', '玉', '田', '甘', '生', '用', '疋', '疒', '癶', '白', '皮', '皿', '目', '矛', '矢', '石', '示', '禸', '禾', '穴', '立',
    '竹', '米', '糸', '缶', '网', '羊', '羽', '老', '而', '耒', '耳', '聿', '肉', '臣', '自', '至', '臼', '舌', '舟', '艮', '色', '虍', '虫', '血', '行', '衣', '西',
    '臣', '見', '角', '言', '谷', '豆', '豕', '豸', '貝', '赤', '走', '足', '身', '車', '辛', '辰', '辵', '邑', '酉', '釆', '里',
    '金', '長', '門', '阜', '隶', '隹', '雨', '青', '非',
    '食', '首', '香', '馬', '骨', '高', '髟', '鬥', '鬯', '鬲', '鬼',
    '魚', '鳥', '鹵', '鹿', '麥', '麻',
    '黃', '黍', '黑', '黹', '黽', '鼎', '鼓', '鼠',
]

RADICAL_SORT_INDEX = {rad: idx for idx, rad in enumerate(XINHUA_RADICAL_ORDER)}

# --- Data Loading ---
def load_and_augment_map():
    try:
        filename = "enhanced_component_map_with_etymology.json"
        with open(filename, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"[Radix] Error loading {filename}: {e}")
        return {}

    load_subtlex_freq()

    for char, info in data.items():
        meta = info.get("meta", {})
        rel = info.get("related_characters", [])
        info['usage_count'] = len({c for c in rel if isinstance(c, str) and len(c) == 1})

        # Use consolidated stroke count normalizer
        info['stroke_count'] = normalize_stroke_count(meta.get("strokes"))

        # Use utility for variant conversion
        lookup_char = get_variant_char(char, prefer="simplified")
        info['freq_per_million'] = SUBTLEX_FREQ.get(lookup_char, 0.0)

    gc.collect()
    return data

def get_component_stats(_component_map):
    r_groups = {}
    idc_counts = {}
    used_comps = set()

    for c, data in _component_map.items():
        # Use utility instead of nested get()
        r = get_char_field(c, "meta", "radical")
        if r:
            gs = _component_map.get(r, {}).get('stroke_count') or 999
            r_groups.setdefault(gs, []).append(r)

        d = get_char_field(c, "meta", "decomposition", default="")
        if d and d[0] in IDC_CHARS:
            idc_counts[d[0]] = idc_counts.get(d[0], 0) + 1

        for ch in d:
            if ch not in IDC_CHARS:
                used_comps.add(ch)

    for gs in r_groups:
        # Use utility for deduplication
        r_groups[gs] = sorted(
            deduplicate_list(r_groups[gs]),
            key=lambda rad: (RADICAL_SORT_INDEX.get(rad, len(XINHUA_RADICAL_ORDER) + 1000), rad)
        )
    
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
        return sqlite3.connect("phrases.db", check_same_thread=False)
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
    """Get stroke count for character."""
    return component_map.get(char, {}).get("stroke_count")

def component_usage_count(comp: str) -> int:
    """Get usage count (how many characters use this component)."""
    return component_map.get(comp, {}).get("usage_count", 0)

def sort_key_usage_primary(ch: str):
    """Sort key prioritizing usage count."""
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
    """Sort key prioritizing frequency."""
    info = component_map.get(ch, {})
    freq = info.get('freq_per_million', 0.0)
    use = info.get('usage_count', 0)
    strokes = info.get('stroke_count') or 999
    return (-freq, -use, strokes, ch)

def apply_script_filter(chars: List[str], script_filter: str) -> List[str]:
    """Filter characters by script type."""
    if script_filter == "Any":
        return chars
    if script_filter == "Simplified":
        return [c for c in chars if not cc_t2s or cc_t2s.convert(c) == c]
    return [c for c in chars if not cc_s2t or cc_s2t.convert(c) == c]

def clean_field(field):
    """Clean field value - kept for backwards compatibility."""
    return field[0] if isinstance(field, list) and field else field or "—"

def get_etymology_text(meta):
    """Extract etymology text from metadata."""
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
    """Format decomposition string."""
    # Use utility
    d = get_char_field(char, "meta", "decomposition", default="")
    return "—" if not d or "?" in d else d

def normalize_single_hanzi(raw: str) -> str:
    """Normalize input to single hanzi character."""
    import unicodedata
    if not raw:
        return ""
    s = unicodedata.normalize("NFC", raw)
    chars = [ch for ch in s.strip() if not ch.isspace() and unicodedata.category(ch) != "Cf"]
    return chars[0] if len(chars) == 1 else ""

def resolve_to_known_variant(ch: str) -> str:
    """Resolve character to known variant in component_map."""
    if not ch:
        return ""
    if ch in component_map:
        return ch
    
    # Use utility for variant lookup
    variants = get_both_variants(ch)
    for variant in variants:
        if variant in component_map:
            return variant
    return ""

def get_char_definition_en(char: str) -> str:
    """Get English definition for character."""
    char = (char or "").strip()[:1]
    # Use utility
    return clean_field(get_char_field(char, "meta", "definition", default=""))

# --- PHONETIC & SEMANTIC ANALYSIS ---

def analyze_component_structure(char: str) -> dict:
    """
    Analyze character to identify Semantic and Phonetic components.
    Only analyzes ⿰ (Left-Right) or ⿱ (Top-Bottom) structures.
    """
    # Use utility to get decomposition
    decomp_str = get_char_field(char, "meta", "decomposition", default="")
    
    ALLOWED_IDCS = {'⿰', '⿱'}
    if not decomp_str or decomp_str[0] not in ALLOWED_IDCS:
        return {
            "char": char,
            "semantic": None,
            "phonetic": None,
            "phonetic_pinyin": None,
            "is_sound_match": False
        }
    
    # Identify Semantic (Radical)
    radical = clean_field(get_char_field(char, "meta", "radical", default=""))
    if radical == "—":
        radical = None
    
    # Identify Phonetic Candidate
    parts = [c for c in decomp_str if c not in IDC_CHARS and c != char]
    
    phonetic = None
    phonetic_pinyin = ""
    is_match = False
    
    if radical and parts:
        potential_phonetics = [p for p in parts if p != radical]
        
        if potential_phonetics:
            phonetic = potential_phonetics[0]
            
            # Check sound similarity
            char_pinyin = clean_field(get_char_field(char, "meta", "pinyin", default=""))
            phonetic_pinyin = clean_field(get_char_field(phonetic, "meta", "pinyin", default=""))
            
            if char_pinyin and phonetic_pinyin and char_pinyin != "—" and phonetic_pinyin != "—":
                import re
                cp_plain = re.sub(r'[0-9]', '', char_pinyin).lower()
                pp_plain = re.sub(r'[0-9]', '', phonetic_pinyin).lower()
                if cp_plain == pp_plain:
                    is_match = True
    
    return {
        "char": char,
        "semantic": radical,
        "phonetic": phonetic,
        "phonetic_pinyin": phonetic_pinyin,
        "is_sound_match": is_match
    }

def get_pronunciation_family(char: str, limit: int = 8) -> list:
    """Find characters sharing the same phonetic component."""
    analysis = analyze_component_structure(char)
    phonetic = analysis.get("phonetic")
    
    if not phonetic:
        return []
        
    family = []
    for c in component_map:
        if c == char:
            continue
        # Use utility
        d = get_char_field(c, "meta", "decomposition", default="")
        if phonetic in d:
            family.append(c)
            
    family.sort(key=lambda x: component_map.get(x, {}).get("freq_per_million", 0), reverse=True)
    return family[:limit]

def get_semantic_family(char: str, limit: int = 8) -> list:
    """Find characters with the same radical."""
    # Use utility
    radical = get_char_field(char, "meta", "radical")
    if not radical or radical == "—":
        return []
        
    family = []
    for c in component_map:
        if c == char:
            continue
        if get_char_field(c, "meta", "radical") == radical:
            family.append(c)
            
    family.sort(key=lambda x: component_map.get(x, {}).get("freq_per_million", 0), reverse=True)
    return family[:limit]

# --- PROMPT GENERATION ---

def get_default_prompt_config() -> dict:
    """Get default prompt configuration."""
    return {
        "version": 1,
        "preamble": "You are a bilingual Chinese dictionary editor and teacher.\n\nExplain a single Chinese character in depth for language learners.\n\n⸻\n\n",
        "tasks": [
            {
                "id": "task1",
                "title": "Task 1 — Character Analysis",
                "template": (
                    "Task 1 — Character Analysis\n\n"
                    "For the Hanzi below, provide:\n"
                    "\t1.\tOriginal meaning\n"
                    "\t2.\tCore semantic concept\n"
                    "\t3.\tWhy it is used in compound characters\n"
                    "\t4.\tThree example words\n"
                    "\t5.\tOne modern usage sentence\n\n"
                    "⸻\n\n"
                ),
            },
            {
                "id": "task2",
                "title": "Task 2 — Example Sentences and Images",
                "template": "Task 2 — Example Sentences and Images\n\nProvide two example sentences.\n\n⸻\n\n",
            },
            {
                "id": "task3",
                "title": "Task 3 — Conceptual Contrast",
                "template": "Task 3 — Conceptual Contrast\n\nCompare with 2–3 similar characters.\n\n⸻\n\n",
            },
            {
                "id": "task4",
                "title": "Task 4 — Logic & Pattern Tutor",
                "template": """Task 4 — Logic & Pattern Tutor

INPUT: char={char}, def_en={def_en}, decomposition={decomposition}, semantic={semantic}, phonetic={phonetic}, phonetic_pinyin={phonetic_pinyin}, is_sound_match={is_sound_match}, pronunciation_family={pronunciation_family}, semantic_family={semantic_family}

TASK: Explain component roles and families conservatively.

⸻
"""
            }
        ],
        "epilogue": "Hanzi: {char}\n- English definition: {def_en}\n",
    }

def normalize_prompt_config(cfg: dict | None) -> dict:
    """Normalize prompt configuration."""
    base = get_default_prompt_config()
    if not isinstance(cfg, dict):
        return base
    
    out = {
        "version": base.get("version", 1),
        "preamble": cfg.get("preamble") if isinstance(cfg.get("preamble"), str) else base.get("preamble", ""),
        "epilogue": cfg.get("epilogue") if isinstance(cfg.get("epilogue"), str) else base.get("epilogue", ""),
        "tasks": list(base.get("tasks", [])),
    }
    
    if isinstance(cfg.get("tasks"), list):
        cleaned = []
        seen = set()
        for t in cfg.get("tasks"):
            if isinstance(t, dict) and t.get("id") and t.get("id") not in seen:
                seen.add(t.get("id"))
                cleaned.append(t)
        if cleaned:
            out["tasks"] = cleaned
    
    return out

def render_combined_prompt(char: str, prompt_config: dict | None, selected_task_ids: list[str] | None, definition_en: str = "") -> str:
    """Render combined prompt for ChatGPT."""
    cfg = normalize_prompt_config(prompt_config)
    char = (char or "").strip()[:1]
    
    # Analyze
    analysis = analyze_component_structure(char)
    semantic = analysis.get("semantic") or "None"
    phonetic = analysis.get("phonetic") or "None"
    phonetic_pinyin = analysis.get("phonetic_pinyin") or "None"
    is_sound_match = str(analysis.get("is_sound_match", False))
    # Use utility
    decomposition = get_char_field(char, "meta", "decomposition", default="None")
    
    p_fam = get_pronunciation_family(char)
    p_fam_str = ", ".join(p_fam) if p_fam else "None"
    
    s_fam = get_semantic_family(char)
    s_fam_str = ", ".join(s_fam) if s_fam else "None"

    # Build prompt
    parts = []
    selected_set = set(selected_task_ids or [])
    for t in cfg.get("tasks", []):
        if t.get("id") in selected_set:
            parts.append(t.get("template", ""))

    full = cfg.get("preamble", "") + "".join(parts) + cfg.get("epilogue", "")
    
    return full.format(
        char=char,
        def_en=definition_en or "",
        decomposition=decomposition,
        semantic=semantic,
        phonetic=phonetic,
        phonetic_pinyin=phonetic_pinyin,
        is_sound_match=is_sound_match,
        pronunciation_family=p_fam_str,
        semantic_family=s_fam_str
    )

def build_chatgpt_prompt(char: str) -> str:
    """Build default ChatGPT prompt for character."""
    char = (char or "").strip()[:1]
    cfg = get_default_prompt_config()
    selected = [t.get("id") for t in cfg.get("tasks", []) if t.get("id")]
    def_en = get_char_definition_en(char)
    return render_combined_prompt(char, cfg, selected, definition_en=def_en)

# --- Stroke Order & HTML ---

def get_stroke_order_view_html(primary_char: str, display_mode: str) -> tuple[str, Optional[str]]:
    """Generate stroke order animation HTML."""
    primary_char = (primary_char or "").strip()[:1]
    if not primary_char:
        return "<p>No character selected.</p>", None

    # Use utility for variants
    chars_to_show = deduplicate_list(get_both_variants(primary_char))
    BOX_SIZE = 280
    
    s_char = chars_to_show[0] if chars_to_show else primary_char
    t_char = chars_to_show[1] if len(chars_to_show) > 1 else s_char
    
    container_html = ""
    for i, c in enumerate(chars_to_show):
        label_text = ""
        if s_char != t_char:
            label_text = "Simplified" if c == s_char else "Traditional"
        label_html = f"<div style='text-align:center; font-weight:bold; color:#555; margin-bottom:5px;'>{label_text}</div>" if label_text else ""
        # Use utility
        pinyin = clean_field(get_char_field(c, "meta", "pinyin", default=""))
        container_html += f"""
        <div style="display:flex; flex-direction:column; align-items:center;">
            {label_html}
            <div style="font-size:2.5rem; color:#e67e22; font-weight:bold; margin-bottom:10px;">{pinyin}</div>
            <div id="hw-target-{i}" style="width:{BOX_SIZE}px;height:{BOX_SIZE}px;border:1px solid #e0e0e0;border-radius:12px; background:white;"></div>
        </div>
        """

    phrases_html = None
    if display_mode != "Single Character" and primary_char:
        n = {"2-Characters": 2, "3-Characters": 3, "4-Characters": 4}.get(display_mode, 0)
        
        # Get compounds - use utility
        meta_compounds = get_char_field(primary_char, "meta", "compounds", default=[])
        
        # Fallback to simplified
        if not meta_compounds:
            s_char = get_variant_char(primary_char, prefer="simplified")
            if s_char != primary_char:
                meta_compounds = get_char_field(s_char, "meta", "compounds", default=[])

        relevant = [w for w in (meta_compounds or []) if isinstance(w, str) and len(w) == n]
        if relevant and (db_conn := get_db_connection()):
            phrases_map = batch_get_phrase_details(sorted(relevant), db_conn)
            phrase_list = []
            for word in sorted(relevant):
                entry = phrases_map.get(word)
                if entry:
                    phrase_list.append({
                        'word': word,
                        'pinyin': entry.get("pinyin", ""),
                        'meanings': entry.get("meanings", "")
                    })
            
            if phrase_list:
                # Use consolidated HTML builder
                title = f"{display_mode} containing {primary_char}"
                phrases_html = build_phrase_list(phrase_list, title)

    full_html = f"""
    <div style="display:flex; gap:15px; align-items:flex-start; flex-wrap:wrap; justify-content:center;">{container_html}</div>
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
                const u = new SpeechSynthesisUtterance(text); u.lang = 'zh-CN';
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
            const sources = ['https://cdn.jsdelivr.net/npm/hanzi-writer@3/dist/hanzi-writer.min.js', 'https://unpkg.com/hanzi-writer@3/dist/hanzi-writer.min.js'];
            for (const src of sources) {{ try {{ await loadScript(src); if (window.HanziWriter) return; }} catch (e) {{}} }}
        }}
        const writers = [];
        async function init() {{
            try {{
                await ensureLibLoaded();
                for (let idx = 0; idx < chars.length; idx++) {{
                    const char = chars[idx]; const targetId = 'hw-target-' + idx;
                    const dataUrls = [`https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/${{char}}.json`, `https://unpkg.com/hanzi-writer-data@2.0.1/${{char}}.json`];
                    let hasData = false;
                    for (const url of dataUrls) {{ try {{ const res = await fetch(url); if (res.ok) {{ hasData = true; break; }} }} catch (e) {{}} }}
                    if(hasData) {{
                        const writer = window.HanziWriter.create(targetId, char, {{ width: boxSize, height: boxSize, padding: 10, showOutline: true, showCharacter: false, strokeAnimationSpeed: 1, delayBetweenStrokes: 60 }});
                        writers.push({{w: writer, c: char}});
                    }} else {{ document.getElementById(targetId).innerHTML = `<div style="line-height:${{boxSize}}px; text-align:center; font-size:${{boxSize/2}}px; color:#ddd;">${{char}}</div>`; }}
                }}
                autoAnimateAll(true);
            }} catch (e) {{ errEl.textContent = e.message || String(e); }}
        }}
        async function playSequence(item, silent) {{ const writer = item.w; const char = item.c; for (let k = 0; k < 30; k++) {{ if (!silent) speak(char); writer.hideCharacter(); await writer.animateCharacter(); await new Promise(r => setTimeout(r, 800)); }} writer.showCharacter(); }}
        function autoAnimateAll(silent = false) {{ writers.forEach(item => {{ playSequence(item, silent); }}); }}
        function resetAll() {{ writers.forEach(item => {{ item.w.hideCharacter(); }}); }}
        document.getElementById('hw-reset').addEventListener('click', resetAll);
        document.getElementById('hw-animate').addEventListener('click', () => autoAnimateAll(false));
        init();
    }})();
    </script>
    """
    return full_html, phrases_html
