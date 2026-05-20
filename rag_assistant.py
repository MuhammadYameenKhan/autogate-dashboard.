"""
AutoGate RAG assistant — LangChain + Gemini with a strict prompt to avoid dumping full context.
Set GOOGLE_API_KEY in .env. Uses data/autogate_knowledge_base.txt (or .pdf if present).
"""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# PromptTemplate import (langchain 1.x may use langchain_core)
try:
    from langchain.prompts import PromptTemplate
except ImportError:
    from langchain_core.prompts import PromptTemplate

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS

try:
    from langchain.chains import RetrievalQA
except ImportError:
    from langchain_classic.chains import RetrievalQA

_BASE_DIR = Path(__file__).resolve().parent
_KB_TXT = _BASE_DIR / 'data' / 'autogate_knowledge_base.txt'
_KB_PDF = _BASE_DIR / 'data' / 'autogate_knowledge_base.pdf'

_qa_system = None
_init_error = None


def _load_documents():
    """Load knowledge base from PDF or text file."""
    if _KB_PDF.is_file():
        loader = PyPDFLoader(str(_KB_PDF))
        return loader.load()
    if _KB_TXT.is_file():
        loader = TextLoader(str(_KB_TXT), encoding='utf-8')
        return loader.load()
    raise FileNotFoundError(
        f'Knowledge base not found. Add {_KB_TXT} or {_KB_PDF}.'
    )


def setup_qa_chain():
    """Build RetrievalQA with a strict prompt — answers only the specific question."""
    api_key = os.getenv('GOOGLE_API_KEY', '').strip()
    if not api_key:
        raise RuntimeError('GOOGLE_API_KEY is not set in .env')

    os.environ['GOOGLE_API_KEY'] = api_key

    print('Vector DB loading (Google Gemini + strict prompt)...')

    documents = _load_documents()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    embeddings = GoogleGenerativeAIEmbeddings(model='models/gemini-embedding-001')
    vectorstore = FAISS.from_documents(texts, embeddings)

    llm = ChatGoogleGenerativeAI(model='gemini-2.0-flash', temperature=0.3)

    prompt_template = """
You are the AutoGate AI Assistant. Use the following context to answer the user's question.
Only answer the specific question asked. DO NOT output the whole architecture or policies unless asked.
If the context does not contain the answer, just say "I don't have this information in my knowledge base."

Context: {context}

Question: {question}
Answer:"""

    PROMPT = PromptTemplate(template=prompt_template, input_variables=['context', 'question'])

    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type='stuff',
        retriever=vectorstore.as_retriever(search_kwargs={'k': 2}),
        chain_type_kwargs={'prompt': PROMPT},
        return_source_documents=False,
    )
    return qa_chain


def _get_qa_system():
    """Lazy-init the QA chain once."""
    global _qa_system, _init_error
    if _qa_system is not None:
        return _qa_system
    if _init_error is not None:
        raise RuntimeError(_init_error)
    try:
        _qa_system = setup_qa_chain()
        return _qa_system
    except Exception as exc:
        _init_error = str(exc)
        raise


def ask_custom_bot(query: str) -> str:
    """Answer a single question using RAG + strict prompt."""
    try:
        chain = _get_qa_system()
        result = chain.invoke({'query': query})
        if isinstance(result, dict):
            return (result.get('result') or '').strip()
        return str(result).strip()
    except Exception as exc:
        print('LangChain RAG error:', exc)
        return (
            "I couldn't reach the knowledge base right now. "
            'Please check GOOGLE_API_KEY and try again.'
        )
