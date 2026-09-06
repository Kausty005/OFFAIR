"""
ui/knowledge_tab.py
Knowledge Base management tab.
Handles document ingestion and test searches.
"""

import streamlit as st
import os

from rag.ingest import ingest_pdf, ingest_docx, ingest_text
from rag.retriever import get_kb_status, retrieve
from tools.files import save_upload, get_workspace_summary
from pathlib import Path

def render_knowledge_base():
    st.header("Local Knowledge Base")
    st.markdown("Manage documents for RAG (Retrieval-Augmented Generation). All embeddings and vectors are stored locally.")

    kb_status = get_kb_status()
    
    # Metrics
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Vector DB", "ChromaDB", "Local")
    with c2:
        st.metric("Status", "READY" if kb_status["available"] else "OFFLINE")
    with c3:
        st.metric("Document Chunks", str(kb_status["document_chunks"]))
    with c4:
        st.metric("Cloud Dependency", "NONE", "Secure")
        
    st.divider()

    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("Ingest New Document")
        uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT", type=["pdf", "docx", "txt"])
        
        if uploaded_file:
            if st.button("INGEST DOCUMENT", type="primary"):
                with st.status("Ingesting into vector database...", expanded=True) as status:
                    st.write(f"1. Saving {uploaded_file.name} to secure workspace...")
                    file_path = save_upload(uploaded_file.getvalue(), uploaded_file.name)
                    
                    st.write("2. Processing and chunking document...")
                    progress_placeholder = st.empty()
                    def _prog(msg):
                        progress_placeholder.text(f"⏳ {msg}")
                    
                    if uploaded_file.name.lower().endswith(".pdf"):
                        result = ingest_pdf(file_path, progress_callback=_prog)
                    elif uploaded_file.name.lower().endswith(".docx"):
                        result = ingest_docx(file_path, progress_callback=_prog)
                    else:
                        text = Path(file_path).read_text(encoding="utf-8", errors="replace")
                        result = ingest_text(text, uploaded_file.name, progress_callback=_prog)
                        
                    if result.get("error"):
                        status.update(label=f"❌ Ingestion Failed: {result['error']}", state="error")
                    else:
                        status.update(label="✅ Document Ingested", state="complete")
                        st.success(f"Successfully processed and embedded {result['chunks']} chunks.")
                        time.sleep(1)
                        st.rerun()

    with col2:
        st.subheader("Test RAG Search")
        query = st.text_input("Enter search query...")
        if st.button("SEARCH"):
            if query:
                with st.spinner("Searching local vector space..."):
                    results = retrieve(query, top_k=3)
                
                if results:
                    for i, r in enumerate(results):
                        st.markdown(f"**[{i+1}] {r.get('document')}** (Score: {r.get('score', 0):.2f})")
                        if r.get("page"):
                            st.caption(f"Page: {r.get('page')}")
                        st.text(r["text"][:300] + "...")
                        st.divider()
                else:
                    st.warning("No relevant results found.")
            else:
                st.info("Enter a query to test retrieval.")

    st.divider()
    st.subheader("Existing Documents")
    workspace = get_workspace_summary()
    st.write(f"Uploads Directory: {workspace['uploads']} files")
