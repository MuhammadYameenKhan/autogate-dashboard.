"""
Knowledge-base Q&A for the AutoGate chatbot.
Returns focused answers from the most relevant KB section only.
"""
import os
import re
from pathlib import Path

_KB_FILE = Path(__file__).resolve().parents[2] / 'data' / 'autogate_knowledge_base.txt'
_gemini_model = None
_gemini_error = None

# Common words to ignore when matching
_STOPWORDS = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'what', 'how', 'why', 'when',
    'where', 'who', 'does', 'do', 'can', 'could', 'would', 'should', 'about',
    'explain', 'describe', 'tell', 'me', 'for', 'and', 'or', 'of', 'in', 'on',
    'to', 'with', 'from', 'this', 'that', 'autogate', 'system', 'please', 'work',
})

# Map query terms to KB section titles (boost routing accuracy)
_TOPIC_ALIASES: dict[str, list[str]] = {
    'architecture': ['SYSTEM ARCHITECTURE', 'OVERVIEW'],
    'architectural': ['SYSTEM ARCHITECTURE'],
    'lpr': ['LICENSE PLATE RECOGNITION (LPR)'],
    'plate': ['LICENSE PLATE RECOGNITION (LPR)', 'PARKING POLICY'],
    'ocr': ['LICENSE PLATE RECOGNITION (LPR)', 'OCR OFFLINE IMPORT'],
    'policy': ['PARKING POLICY'],
    'parking': ['PARKING POLICY', 'BOOKING'],
    'faculty': ['PARKING POLICY', 'USER ROLES'],
    'student': ['PARKING POLICY', 'USER ROLES', 'BOOKING'],
    'role': ['USER ROLES'],
    'roles': ['USER ROLES'],
    'admin': ['USER ROLES'],
    'gate': ['GATE OPERATIONS'],
    'barrier': ['GATE OPERATIONS'],
    'anomaly': ['ANOMALY DETECTION'],
    'anomalies': ['ANOMALY DETECTION'],
    'forecast': ['FORECASTING'],
    'booking': ['BOOKING'],
    'chatbot': ['CHATBOT / AI ASSISTANT'],
    'assistant': ['CHATBOT / AI ASSISTANT'],
}


def _load_kb_text() -> str:
    if _KB_FILE.is_file():
        return _KB_FILE.read_text(encoding='utf-8')
    return ''


def _query_terms(query: str) -> list[str]:
    words = re.findall(r'\w+', query.lower())
    return [w for w in words if len(w) > 2 and w not in _STOPWORDS]


def _parse_sections(kb_text: str) -> list[tuple[str, str]]:
    """Split KB into titled sections (e.g. PARKING POLICY, SYSTEM ARCHITECTURE)."""
    sections: list[tuple[str, str]] = []
    current_title = 'General'
    current_lines: list[str] = []

    for line in kb_text.split('\n'):
        stripped = line.strip()
        is_header = (
            stripped
            and stripped == stripped.upper()
            and re.match(r'^[A-Z][A-Z0-9\s/&\-\(\)]+$', stripped)
            and len(stripped) >= 4
            and not stripped.startswith('-')
        )
        if is_header:
            if current_lines:
                body = '\n'.join(current_lines).strip()
                if body:
                    sections.append((current_title, body))
            current_title = stripped
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        body = '\n'.join(current_lines).strip()
        if body:
            sections.append((current_title, body))

    if not sections:
        sections.append(('General', kb_text.strip()))
    return sections


def _score_section(title: str, body: str, terms: list[str]) -> float:
    if not terms:
        return 0.0
    title_l = title.lower()
    # Skip example/menu lines when scoring body
    body_lines = [
        ln for ln in body.split('\n')
        if 'example question' not in ln.lower()
    ]
    body_l = '\n'.join(body_lines).lower()
    score = 0.0
    for term in terms:
        if term in title_l:
            score += 5.0
        for alias_title in _TOPIC_ALIASES.get(term, []):
            if alias_title.lower() in title_l or title.upper() == alias_title:
                score += 6.0
        if term in body_l:
            score += 1.0 + body_l.count(term) * 0.25
    return score


def _retrieve_context(query: str, kb_text: str, max_sections: int = 1) -> tuple[str, str]:
    """Return (section_title, context_text) for the best-matching section(s) only."""
    terms = _query_terms(query)
    sections = _parse_sections(kb_text)

    if not terms:
        title, body = sections[0]
        return title, body[:800]

    ranked = sorted(
        ((_score_section(t, b, terms), t, b) for t, b in sections),
        key=lambda x: -x[0],
    )
    best_score, best_title, best_body = ranked[0]

    if best_score <= 0 and len(ranked) > 1:
        _, best_title, best_body = ranked[1]

    # Within section: prefer bullet lines that match query terms
    focused = _focus_section_body(best_body, terms, query)
    return best_title, focused


def _is_list_query(query: str) -> bool:
    return bool(re.search(
        r'\b(what are|what is|list|types of|all|roles|features|kinds)\b',
        query.lower(),
    ))


def _focus_section_body(body: str, terms: list[str], query: str = '') -> str:
    """Keep only lines that relate to the question; cap length."""
    lines = [ln.strip() for ln in body.split('\n') if ln.strip()]
    if not lines:
        return ''

    # Broad questions (e.g. "what are user roles") → short list from that section
    if _is_list_query(query):
        return '\n'.join(lines[:4])

    if not terms:
        return '\n'.join(lines[:3])

    matched = []
    for line in lines:
        lower = line.lower()
        hits = sum(1 for t in terms if t in lower)
        if hits:
            matched.append((hits, line))

    if matched:
        matched.sort(key=lambda x: -x[0])
        picked = [ln for _, ln in matched[:3]]
        return '\n'.join(picked)

    return '\n'.join(lines[:2])


def _simple_search(query: str, kb_text: str) -> str:
    """Concise answer from the best section without calling Gemini."""
    title, context = _retrieve_context(query, kb_text)
    terms = _query_terms(query)

    lines = [ln.strip() for ln in context.split('\n') if ln.strip()]
    if not lines:
        return (
            'I do not have specific information on that in the knowledge base. '
            'Try asking about parking policy, LPR, gate operations, or user roles.'
        )

    # Short direct answer: section title + top 1–3 relevant bullets
    max_lines = 4 if _is_list_query(query) else 3
    answer_lines = [f'**{title}**']
    for line in lines[:max_lines]:
        clean = line.lstrip('- ').strip()
        if clean:
            answer_lines.append(f"• {clean}" if not clean.startswith('•') else clean)

    return '\n'.join(answer_lines)


def _ask_gemini(query: str, context: str, section_title: str) -> str:
    global _gemini_model, _gemini_error
    api_key = os.getenv('GOOGLE_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('GOOGLE_API_KEY is not set')

    import google.generativeai as genai

    if _gemini_model is None and _gemini_error is None:
        genai.configure(api_key=api_key)
        _gemini_model = genai.GenerativeModel('gemini-1.5-flash')

    if _gemini_model is None:
        raise RuntimeError(_gemini_error or 'Gemini model unavailable')

    prompt = (
        'You are AutoGate AI. Answer the user question using ONLY the excerpt below.\n'
        'Rules:\n'
        '- Answer ONLY what was asked; do not mention unrelated topics.\n'
        '- Use 2 to 4 short sentences maximum (or up to 3 bullet points if listing).\n'
        '- Do not copy the entire excerpt; summarize the specific facts needed.\n'
        '- If the excerpt does not contain the answer, say: '
        '"I do not have that specific information in the knowledge base."\n\n'
        f'TOPIC: {section_title}\n'
        f'EXCERPT:\n{context}\n\n'
        f'QUESTION: {query}\n\n'
        'Focused answer:'
    )
    response = _gemini_model.generate_content(prompt)
    text = getattr(response, 'text', None) or str(response)
    return text.strip()


def _ask_rag_assistant(query: str) -> str | None:
    """Use LangChain RAG + strict PromptTemplate when available."""
    try:
        from rag_assistant import ask_custom_bot
        answer = ask_custom_bot(query)
        if answer and 'couldn\'t reach' not in answer.lower():
            return answer
    except Exception as exc:
        print(f'RAG assistant unavailable, using local KB: {exc}')
    return None


def ask_knowledge_base(query: str) -> str:
    kb_text = _load_kb_text()
    if not kb_text:
        return (
            '⚠️ Knowledge base file is missing. '
            f'Expected at: {_KB_FILE}'
        )

    # Prefer LangChain RAG with strict prompt (rag_assistant.py)
    rag_answer = _ask_rag_assistant(query)
    if rag_answer:
        return rag_answer

    section_title, context = _retrieve_context(query, kb_text)

    try:
        return _ask_gemini(query, context, section_title)
    except Exception as exc:
        print(f'Knowledge base (Gemini) fallback to local search: {exc}')
        return _simple_search(query, kb_text)


def is_knowledge_query(message: str) -> bool:
    """Detect documentation / policy questions for knowledge-base routing."""
    msg = message.lower().strip()
    patterns = [
        r'\b(what|how|why|when|where|who|explain|describe|tell me about)\b',
        r'\b(knowledge|policy|policies|architecture|system|autogate|lpr|anomaly|forecast)\b',
        r'\b(faculty|student|staff|booking|register|documentation|manual)\b',
        r'\?$',
    ]
    return any(re.search(p, msg) for p in patterns)
