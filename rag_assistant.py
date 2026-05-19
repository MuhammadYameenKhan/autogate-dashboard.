import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA

# Yahan apni free Google Gemini ki API key paste karein
os.environ["GOOGLE_API_KEY"] = "AIzaSyDQHWnifMfECcCs22Dz14c4dCTB04oMRTs"

def setup_qa_chain():
    print("Vectoor B is loading(Using Google Gemini)...")
    
    # 1. PDF load karein
    loader = PyPDFLoader("autogate_knowledge_base.pdf")
    documents = loader.load()

    # 2. PDF ko chunks mein torein
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    texts = text_splitter.split_documents(documents)

    # 3. Vector Database (FAISS) banayen - Gemini Embeddings ke sath
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vectorstore = FAISS.from_documents(texts, embeddings)

    # 4. LLM (Google Gemini) ko connect karein
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.3)
    
    # 5. Chain banayen
    qa_chain = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=vectorstore.as_retriever(search_kwargs={"k": 2})
    )
    return qa_chain

# Global variable mein chain save kar lein
qa_system = setup_qa_chain()

def ask_custom_bot(query: str) -> str:
    """Yeh function Flask use karega"""
    try:
        result = qa_system.invoke({"query": query})
        return result['result']
    except Exception as e:
        print("LangChain Error:", e)
        return "⚠️ not connecting too logic base."