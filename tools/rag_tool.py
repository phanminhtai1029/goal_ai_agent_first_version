# File: tools/rag_tool.py
from langchain.tools import tool
from langchain_google_vertexai import VertexAIEmbeddings, VertexAI
from langchain_google_firestore import FirestoreVectorStore
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from google.cloud import firestore

_rag_chain = None

def _get_rag_chain():
    """Khởi tạo RAG chain một lần."""
    global _rag_chain
    if _rag_chain:
        return _rag_chain

    # Khởi tạo mọi thứ bên trong hàm
    MODEL_REGION = "asia-southeast1"
    
    db = firestore.Client(database="vector-database-test")
    
    embeddings_model = VertexAIEmbeddings(
        model_name="text-embedding-004",
        location=MODEL_REGION
    )

    llm = VertexAI(
        model_name="gemini-2.5-flash",
        location=MODEL_REGION
    )

    vector_store = FirestoreVectorStore(
        collection="rag_documents",
        embedding_service=embeddings_model,
        client=db 
    )
    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    system_prompt = (
        "Bạn là một trợ lý RAG. Hãy trả lời câu hỏi của người dùng dựa trên"
        " context (thông tin) được cung cấp. "
        "Nếu context không chứa câu trả lời, hãy nói 'Tôi không tìm thấy thông tin này trong tài liệu đã lưu'.\n\n"
        "<context>{context}</context>"
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt), ("human", "{input}"),
    ])

    question_answer_chain = create_stuff_documents_chain(llm, prompt)
    _rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    return _rag_chain

@tool
def add_to_rag(document_text: str):
    """
    Dùng để LƯU TRỮ một mẩu thông tin, văn bản, hoặc ghi chú mới vào cơ sở tri thức (RAG).
    Input: document_text (str): Nội dung văn bản cần lưu.
    """
    try:
        # Chúng ta cần khởi tạo riêng vector_store cho hàm này
        # (Vì _get_rag_chain chỉ trả về chain)
        db = firestore.Client(database="vector-database-test")
        embeddings_model = VertexAIEmbeddings(model_name="text-embedding-004", location="asia-southeast1")
        vector_store = FirestoreVectorStore(
            collection="rag_documents",
            embedding_service=embeddings_model,
            client=db 
        )
        vector_store.add_texts([document_text])
        return "Đã lưu thông tin mới vào cơ sở tri thức."
    except Exception as e:
        return f"Lỗi khi lưu thông tin: {e}"

@tool
def ask_rag(question: str):
    """
    Dùng để HỎI các câu hỏi kiến thức, hoặc tra cứu các thông tin BẠN ĐÃ LƯU TRỮ.
    Input: question (str): Câu hỏi của người dùng.
    """
    try:
        rag_chain = _get_rag_chain() # <--- Dùng hàm get
        response = rag_chain.invoke({"input": question})
        return response.get("answer", "Không tìm thấy câu trả lời.")
    except Exception as e:
        return f"Lỗi khi tra cứu RAG: {e}"