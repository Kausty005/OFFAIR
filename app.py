"""
app.py
Main Streamlit entry point for SIH26117 Sovereign AI Workbench.
"""

import streamlit as st

# Configure page before any other Streamlit commands
st.set_page_config(
    page_title="Sovereign AI Workbench",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Imports
from ui.sidebar import render_sidebar
from ui.workbench_tab import render_workbench
from ui.inspection_tab import render_inspection_agent
from ui.coding_tab import render_coding_agent
from ui.knowledge_tab import render_knowledge_base
from ui.audit_tab import render_audit_security
from ui.system_tab import render_system_status

def main():
    # Render Sidebar
    render_sidebar()
    
    # Render Main Tabs
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "🧠 AI Workbench", 
        "🏭 Inspection Agent", 
        "💻 Coding Agent", 
        "📚 Knowledge Base", 
        "🛡️ Audit & Security",
        "⚙️ System"
    ])
    
    with tab1:
        render_workbench()
        
    with tab2:
        render_inspection_agent()
        
    with tab3:
        render_coding_agent()
        
    with tab4:
        render_knowledge_base()
        
    with tab5:
        render_audit_security()
        
    with tab6:
        render_system_status()


if __name__ == "__main__":
    main()
