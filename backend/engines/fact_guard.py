"""
engines/fact_guard.py — keeps facts exact when a reply is turned into Kannada (2026-10-29).

Why: a Kannada reply is written in English from the database, then translated
(Sarvam) and polished (Groq 120B). Both steps rebuild the sentence, and in one
test the label "KCET" ended up next to the COMEDK amount. Telling the AI to
"keep numbers exactly" is a request, not a guarantee — so this file checks.

Three steps (used by response_engine._localize):

  1. protect(english)   facts -> numbered tags  "the CSE fee is [4] through [6]"
                        so translation and polish never touch the facts.
  2. restore(kannada)   tags -> the exact original values.
  3. verify(english, kannada)
        a) every value (amount, rank, year, name, phone, email...) from the
           English answer is in the Kannada one, and no number was invented;
        b) RELATIONSHIPS: a label (KCET, COMEDK, CSE, ECE, Management quota...)
           must not end up next to a value it was never next to in English.
           E.g. English pairs KCET with 1,20,000; Kannada pairing KCET with
           1,40,000 fails, even though every number is still present.

If verify fails, response_engine tries the next way of making the Kannada,
and in the end shows the (correct) English answer rather than a wrong one.

Limits (honest): this protects facts and their pairing. It cannot judge
Kannada grammar, and it cannot catch a wrong fact that is already in the
English answer. Representative questions from every topic must still be
tried by a person before the expo (check_demo.py does a first pass).
"""

import re

# ── What is a fact ─────────────────────────────────────────────────────────
# VALUES must survive exactly. LABELS say what a value belongs to.
_KN_DIGITS = str.maketrans("೦೧೨೩೪೫೬೭೮೯", "0123456789")
# 2026-10-29: the AI sometimes writes "2026‑27" or "080‑2846‑8191" with a
# special hyphen (U+2011 etc.) or a special space. They look normal but are
# different characters, so "2026‑27" was read as two numbers and a correct
# Kannada reply was rejected. Every such character becomes a plain one
# (one character for one, so positions in the text do not move).
_PLAIN = str.maketrans({c: "-" for c in "\u2010\u2011\u2012\u2013\u2014\u2015\u2212"}
                       | {c: " " for c in "\u00a0\u2007\u2009\u200a\u202f"})


def plain_text(text: str) -> str:
    """Special hyphens/spaces -> plain '-' and ' ' (same length)."""
    return (text or "").translate(_PLAIN)

# Boundaries are ASCII-only on purpose: Kannada endings stick to English words
# ("CSEಗೆ", "2026-27ರಲ್ಲಿ") and must not hide the fact.
_L = r"(?<![A-Za-z0-9])"
_R = r"(?![A-Za-z0-9])"
_FACT = re.compile(rf"""
  (?P<email>[\w.+-]+@[\w-]+(?:\.[\w-]+)+)
| (?P<url>(?:https?://)?(?:www\.)?[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.(?:ac\.in|edu|com|in|org)(?:/[\w./-]*)?{_R})
| (?P<phone>(?:\+91[\s-]?)?(?:\d{{5}}[\s-]?\d{{5}}|\d{{3,4}}[\s-]\d{{3,4}}[\s-]\d{{4}}){_R})
| (?P<yearrange>{_L}20\d\d\s?[-–]\s?\d\d(?:\d\d)?(?!\d))
| (?P<time>{_L}\d{{1,2}}[:.]\d{{2}}\s?(?:am|pm|AM|PM)?{_R})
| (?P<number>(?:₹|Rs\.?\s?|INR\s?)?(?<![\d,.])\d+(?:,\d+)*(?:\.\d+)?(?:\s?(?:LPA|lpa|lakhs?|crores?|%|percent))?(?!\d))
| (?P<person>{_L}(?:Dr|Prof|Mr|Mrs|Ms|Shri|Smt)\.?\s+[A-Z][A-Za-z]*(?:\.?\s?[A-Z](?:[a-z]+)?(?![A-Za-z])\.?)*)
| (?P<quota>{_L}(?i:Management|Government|NRI|SNQ)(?:\s+(?i:quota))?{_R})
| (?P<branch>{_L}(?i:Civil|Mechanical){_R})
| (?P<code>{_L}[A-Z][A-Z]+(?:[-&][A-Za-z]+)*{_R})
""", re.X)

VALUE_KINDS = {"email", "url", "phone", "yearrange", "time", "number", "person"}
LABEL_KINDS = {"quota", "code", "branch"}
# Labels compete only inside their own family: KCET vs COMEDK, CSE vs ECE.
# ("CSE ... COMEDK ... 1,40,000" is fine: CSE is the branch, COMEDK the route.)
_ROUTE_LABELS = {"kcet", "comedk", "pgcet", "management", "government", "nri", "snq"}
_BRANCH_HINT = re.compile(r"^(cse|ise|ece|eee|aiml|aids|mba|mca|me|cv|cs|ai|ds|civil|mechanical)([-&].*)?$")


def _family(label: str):
    if label in _ROUTE_LABELS:
        return "route"
    if _BRANCH_HINT.match(label):
        return "branch"
    return None
# Labels that describe a role or the college itself, not which item a value belongs to.
_GENERIC_LABELS = {"hod", "hods", "svit", "lpa", "pdf", "ok", "am", "pm", "rs", "inr", "i", "a"}


def _clean(value: str) -> str:
    return value.strip().rstrip(".,;:")


def _norm(kind: str, value: str) -> str:
    v = _clean(value).translate(_KN_DIGITS)
    if kind in {"number"}:
        unit = re.search(r"(lpa|lakh|crore|%|percent)", v, re.I)
        digits = re.sub(r"[^\d.]", "", v).rstrip(".")
        if "." in digits:
            digits = digits.rstrip("0").rstrip(".")
        return digits + ((unit.group(1).lower().replace("percent", "%").replace("lakhs", "lakh")) if unit else "")
    if kind in {"phone"}:
        return re.sub(r"\D", "", v)[-10:]
    if kind == "yearrange":
        return re.sub(r"\s", "", v).replace("–", "-")
    if kind == "person":
        return re.sub(r"[^a-z]", "", v.lower())
    if kind == "quota":
        return v.split()[0].lower()            # "Management quota" == "Management"
    if kind == "time":
        return re.sub(r"\s", "", v.lower()).replace(".", ":")
    return re.sub(r"\s+", " ", v.lower())


def find_facts(text: str) -> list:
    """[(kind, original_text, normalized, start, end)] in reading order."""
    out = []
    for m in _FACT.finditer(plain_text(text).translate(_KN_DIGITS)):
        kind = m.lastgroup
        raw = _clean(m.group())
        if not raw:
            continue
        if kind == "number":
            digits = re.sub(r"\D", "", raw)
            if not digits:
                continue
        norm = _norm(kind, raw)
        if kind == "code" and norm in _GENERIC_LABELS:
            continue
        out.append((kind, raw, norm, m.start(), m.start() + len(raw)))
    return out


def _is_soft_number(kind: str, norm: str) -> bool:
    """Single-digit numbers ('2 instalments') may be written as Kannada words — not enforced."""
    return kind == "number" and norm.isdigit() and len(norm) == 1


# ── 1 + 2. protect / restore ──────────────────────────────────────────────
_TAG = re.compile(r"\[\s*([0-9೦-೯]{1,3})\s*\]")


def protect(text: str) -> tuple:
    """Replaces every fact with a tag like [3]. Returns (tagged_text, {"3": "₹1,20,000", ...})."""
    facts = find_facts(text)
    if not facts:
        return text, {}
    table, by_value, pieces, last = {}, {}, [], 0
    for kind, raw, norm, start, end in facts:
        key = (kind, norm)
        if key not in by_value:
            by_value[key] = str(len(by_value) + 1)
            table[by_value[key]] = raw
        pieces.append(text[last:start])
        pieces.append(f"[{by_value[key]}]")
        last = end
    pieces.append(text[last:])
    return "".join(pieces), table


def restore(text: str, table: dict):
    """Tags back to the exact values. None if a tag was lost, invented or broken."""
    if not table:
        return text
    seen = set()

    def put_back(m):
        key = m.group(1).translate(_KN_DIGITS)
        seen.add(key)
        return table.get(key, m.group(0))

    restored = _TAG.sub(put_back, text)
    if seen != set(table) or _TAG.search(restored) or re.search(r"[\[\]]", restored):
        return None
    return restored


# ── 3. verify ─────────────────────────────────────────────────────────────
_CLAUSE_SPLIT = re.compile(r"[;:!?।\n]|\.\s|,\s| and | or | ಮತ್ತು | ಹಾಗೂ | ಅಥವಾ ")


_ABBREV = re.compile(r"(?<![A-Za-z])(Dr|Prof|Mr|Mrs|Ms|Shri|Smt|Rs|No|St|[A-Z])\.(?=\s)")


def _clauses(text: str) -> list:
    # "Dr. Ramesh K" and "Rs. 500" are not sentence ends: hide their dots while splitting
    hidden = _ABBREV.sub(lambda m: m.group(1) + "§", text or "")
    return [c.replace("§", ".") for c in _CLAUSE_SPLIT.split(hidden) if c and c.strip()]


def _pairs(text: str) -> set:
    """(label, value) pairs that sit in the same clause."""
    pairs = set()
    for clause in _clauses(text):
        facts = find_facts(clause)
        labels = {f[2] for f in facts if f[0] in LABEL_KINDS}
        values = {(f[0], f[2]) for f in facts if f[0] in VALUE_KINDS and not _is_soft_number(f[0], f[2])}
        pairs |= {(l, v) for l in labels for v in values}
    return pairs


def verify(english: str, kannada: str, user_query: str = "") -> tuple:
    """(True, 'ok') or (False, reason). See the module note for the rules."""
    en = find_facts(english)
    kn = find_facts(kannada)
    en_values = {(f[0], f[2]) for f in en if f[0] in VALUE_KINDS and not _is_soft_number(f[0], f[2])}
    kn_values = {(f[0], f[2]) for f in kn if f[0] in VALUE_KINDS and not _is_soft_number(f[0], f[2])}

    # a) nothing lost, nothing invented
    missing = en_values - kn_values
    if missing:
        return False, "missing: " + ", ".join(v for _, v in sorted(missing))
    query_values = {(f[0], f[2]) for f in find_facts(user_query)}
    invented = {v for v in kn_values - en_values - query_values if v[0] != "yearrange"}
    if invented:
        return False, "added: " + ", ".join(v for _, v in sorted(invented))

    # labels that tie values to something (KCET, CSE, Management quota...) must stay
    en_pairs = _pairs(english)
    binding_labels = {l for l, _ in en_pairs}
    kn_labels = {f[2] for f in kn if f[0] in LABEL_KINDS}
    lost_labels = binding_labels - kn_labels
    if lost_labels:
        return False, "label lost: " + ", ".join(sorted(lost_labels)).upper()

    # b) relationships: a label next to a value it never had in English = a swap
    en_by_label = {}
    for l, v in en_pairs:
        en_by_label.setdefault(l, set()).add(v)
    for l, v in _pairs(kannada):
        if l in en_by_label and v not in en_by_label[l] and v in en_values:
            # Only a conflict if, in English, this value belonged to a DIFFERENT label
            # of the same set (e.g. 1,40,000 belonged to COMEDK, not KCET).
            fam = _family(l)
            owners = {ol for ol, ov in en_pairs if ov == v and _family(ol) == fam}
            if fam and owners and l not in owners:
                return False, f"{l.upper()} paired with {v[1]} (in English {v[1]} belongs to {', '.join(sorted(o.upper() for o in owners))})"
    return True, "ok"
