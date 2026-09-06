"""
ui/sidebar.py
Sidebar component showing system status, model availability, and security mode.
"""

import streamlit as st
import time

from security.audit import get_security_status
from models.model_registry import get_model_status


def render_sidebar():
    """Render the main system sidebar."""
    with st.sidebar:
        st.title("🛡️ Sovereign AI")
        st.caption("SIH26117 | Local Air-Gapped Engine")
        
        st.divider()

        # Security Status Panel
        sec_status = get_security_status()
        st.subheader("Security Status")
        
        c1, c2 = st.columns(2)
        with c1:
            st.metric("Inference", "LOCAL", "100%")
            st.metric("Sandbox", "DOCKER", "Isolated")
        with c2:
            st.metric("RAG / OCR", "LOCAL", "Local Storage")
            st.metric("External APIs", str(sec_status["external_ai_apis"]), "Blocked" if sec_status["external_ai_apis"] == 0 else "WARNING")

        if sec_status["external_ai_apis"] == 0:
            st.success("Air-Gapped Mode: ACTIVE")
        else:
            st.error("SECURITY ALERT: External APIs detected!")

        st.divider()

        # Model Status Panel
        st.subheader("Local Models")
        models = get_model_status()
        
        for m in models:
            role_name = m["role"].upper()
            model_name = m["name"]
            
            if m["available"]:
                st.markdown(f"**{role_name}**")
                st.caption(f"🟢 {model_name}")
            else:
                st.markdown(f"**{role_name}**")
                if m["fallback_available"]:
                    st.caption(f"🟡 {m['fallback']} (Fallback)")
                else:
                    st.caption(f"🔴 {model_name} (Not found)")

        st.divider()
        
        # System metrics
        st.subheader("System Metrics")
        st.caption(f"LLM Calls: {sec_status['local_llm_calls']}")
        st.caption(f"OCR Operations: {sec_status['ocr_operations']}")
        st.caption(f"RAG Searches: {sec_status['rag_searches']}")
        st.caption(f"Sandbox Runs: {sec_status['sandbox_executions']}")
        
        st.divider()
        st.caption("First Working Prototype")
        st.caption("Not for production deployment")
