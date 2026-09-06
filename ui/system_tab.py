"""
ui/system_tab.py
System health check and status tab.
"""

import streamlit as st
import sys

from models.ollama_client import ping as ollama_ping
from tools.sandbox import docker_available
from document.ocr import get_ocr_status
from rag.retriever import get_kb_status

def render_system_status():
    st.header("System Health Check")
    st.markdown("Ensure all required local dependencies are running.")

    # 1. Python Environment
    st.subheader("1. Runtime Environment")
    c1, c2 = st.columns(2)
    c1.metric("Python", sys.version.split()[0])
    c2.metric("Streamlit", st.__version__)
    
    st.divider()

    # 2. Ollama Status
    st.subheader("2. Local Inference Server (Ollama)")
    ollama_ok = ollama_ping()
    if ollama_ok:
        st.success("✅ Ollama is running and accessible on localhost:11434")
    else:
        st.error("❌ Ollama is NOT reachable. Please start Ollama before using AI features.")
        st.code("ollama serve", language="bash")
        
    st.divider()

    # 3. Docker Sandbox
    st.subheader("3. Docker Sandbox (Coding Agent)")
    docker_ok = docker_available()
    if docker_ok:
        st.success("✅ Docker daemon is running")
    else:
        st.error("❌ Docker is NOT available. Coding agent sandbox will fail.")
        st.info("Please start Docker Desktop.")

    st.divider()

    # 4. OCR Engine
    st.subheader("4. Local OCR Engine")
    ocr_stat = get_ocr_status()
    if ocr_stat["available"]:
        st.success(f"✅ OCR Engine Ready: {ocr_stat['engine']}")
    else:
        st.warning(f"⚠️ OCR Engine Unavailable: {ocr_stat['message']}")
        st.info("Scanned PDFs will be processed via Vision model instead.")

    st.divider()

    # 5. Knowledge Base
    st.subheader("5. Vector Database")
    kb = get_kb_status()
    if kb["available"]:
        st.success(f"✅ ChromaDB Ready (Collection: {kb['collection']})")
    else:
        st.error("❌ ChromaDB unavailable. Check Python 3.14 compatibility.")

    st.divider()
    
    if st.button("Re-run Health Check"):
        st.rerun()
