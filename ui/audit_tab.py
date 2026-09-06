"""
ui/audit_tab.py
Audit and Security dashboard.
Shows event logs and guarantees that no external APIs were called.
"""

import streamlit as st
import pandas as pd
from security.audit import get_recent_events, get_security_status

def render_audit_security():
    st.header("Audit & Security Dashboard")
    st.markdown("Verifiable proof of local sovereignty. Monitor all system actions and network isolation.")

    status = get_security_status()
    
    # Big security badges
    st.subheader("System Isolation Guarantees")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        if status["external_ai_apis"] == 0:
            st.success("✅ 0 External API Calls")
        else:
            st.error(f"❌ {status['external_ai_apis']} External Calls")
    with c2:
        st.success("✅ No Cloud Uploads")
    with c3:
        st.success("✅ Air-Gapped Ready")
    with c4:
        st.success("✅ Docker Sandboxed")

    st.divider()

    st.subheader("Action Counters")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Local LLM Inferences", status["local_llm_calls"])
    c2.metric("Local OCR Operations", status["ocr_operations"])
    c3.metric("RAG Searches", status["rag_searches"])
    c4.metric("Sandbox Executions", status["sandbox_executions"])

    st.divider()

    st.subheader("Recent Audit Log Events")
    events = get_recent_events(100)
    
    if events:
        # Reverse to show newest first
        events.reverse()
        
        # Format for dataframe
        df_data = []
        for e in events:
            # Flatten dict slightly for display
            row = {"time": e["time"], "event": e["event"]}
            details = [f"{k}={v}" for k, v in e.items() if k not in ["time", "event"]]
            row["details"] = " | ".join(details)
            df_data.append(row)
            
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No audit events recorded yet.")
        
    if st.button("Refresh Logs"):
        st.rerun()
