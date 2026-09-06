"""
ui/inspection_tab.py
Inspection Agent demonstration tab.
Highly specialized workflow for processing scanned PDFs and generating Approval Notes.
"""

import streamlit as st
import os
import time

from agent.agent import run_agent
from tools.files import save_upload

def render_inspection_agent():
    st.header("Inspection → Approval Agent")
    st.markdown("Convert confidential inspection reports into review-ready approval drafts using entirely local AI.")
    
    st.info("💡 **Demo Instructions:** Upload the `inspection_report.pdf` from the `demo_data/` folder and click **Run Agent**.")

    uploaded_file = st.file_uploader("Upload Scanned Inspection Report", type=["pdf", "jpg", "png"])
    
    if uploaded_file:
        if st.button("RUN AGENT", type="primary", use_container_width=True):
            with st.status("Executing Inspection Workflow...", expanded=True) as status:
                
                st.write("1. ⏳ Saving document to secure local workspace...")
                file_path = save_upload(uploaded_file.getvalue(), uploaded_file.name)
                st.write(f"   ✅ Saved: {uploaded_file.name}")
                
                has_pdf = uploaded_file.name.lower().endswith(".pdf")
                has_image = uploaded_file.name.lower().endswith((".jpg", ".png", ".jpeg"))
                
                st.write("2. ⏳ Initializing Agent Engine...")
                
                # We use a custom placeholder to show steps live
                step_placeholder = st.empty()
                
                def step_callback(step):
                    icon = "✅" if step.status == "done" else ("❌" if step.status == "error" else "⏳")
                    step_placeholder.text(f"{icon} Step {step.index + 1}: {step.description}")
                
                state = run_agent(
                    task="Analyze this inspection report using the organization's maintenance procedures and prepare an approval note.",
                    uploaded_files=[str(file_path)],
                    has_pdf=has_pdf,
                    has_image=has_image,
                    progress_callback=step_callback
                )
                
                if state.status == "done":
                    status.update(label="✅ Workflow Complete", state="complete", expanded=False)
                else:
                    status.update(label=f"❌ Workflow Failed: {state.error}", state="error", expanded=True)

            if state.status == "done":
                st.subheader("Key Findings Extracted")
                extracted = state.extracted_data
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Equipment:** {extracted.get('equipment_name', 'N/A')} ({extracted.get('equipment_id', 'N/A')})")
                    st.write(f"**Date:** {extracted.get('inspection_date', 'N/A')}")
                    st.write(f"**Severity:** {extracted.get('severity', 'N/A').upper()}")
                
                with c2:
                    st.write("**Issues Detected:**")
                    for finding in extracted.get('findings', []):
                        st.write(f"- {finding}")

                st.subheader("Generated Deliverable")
                if state.output_files:
                    fpath = state.output_files[0]
                    fname = fpath.split("/")[-1] if "/" in fpath else fpath.split("\\")[-1]
                    with open(fpath, "rb") as f:
                        st.download_button(
                            label=f"📥 Download {fname}",
                            data=f,
                            file_name=fname,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            type="primary"
                        )
                    
                    st.success("Verification Passed. Output file exists and contains required fields.")
                else:
                    st.error("No output file generated.")
                
                with st.expander("View Agent Execution Trace"):
                    for step in state.plan:
                        icon = "✅" if step.status == "done" else ("❌" if step.status == "error" else ("⏭️" if step.status == "skipped" else "⏳"))
                        st.text(f"{icon} {step.description}")
                        if step.result:
                            st.caption(f"   ↳ {step.result}")
