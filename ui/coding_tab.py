"""
ui/coding_tab.py
Coding Agent demonstration tab.
Executes code inside the Docker sandbox.
"""

import streamlit as st
import time

from agent.agent import run_agent

def render_coding_agent():
    st.header("Coding & Sandbox Agent")
    st.markdown("Generate code locally and execute it safely inside an isolated Docker sandbox.")

    st.info("💡 **Demo Hint:** Click 'Run Demo' to automatically test the deterministic coding capabilities.")

    # Pre-filled prompt
    default_prompt = "Write a Python program that calculates pump efficiency from input power and output power. Include unittest test cases."
    
    prompt = st.text_area("Coding Request", value=default_prompt, height=100)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        run_btn = st.button("Generate & Run", type="primary")

    if run_btn:
        with st.status("Executing Coding Workflow...", expanded=True) as status:
            st.write("1. ⏳ Parsing requirements...")
            
            step_placeholder = st.empty()
            
            def step_callback(step):
                icon = "✅" if step.status == "done" else ("❌" if step.status == "error" else ("⏭️" if step.status == "skipped" else "⏳"))
                step_placeholder.text(f"{icon} {step.description}")
            
            state = run_agent(
                task=prompt,
                progress_callback=step_callback
            )
            
            if state.status == "done":
                status.update(label="✅ Workflow Complete", state="complete", expanded=False)
            else:
                status.update(label=f"❌ Workflow Failed: {state.error}", state="error", expanded=True)

        if state.status == "done":
            st.subheader("Results")
            
            sandbox_result = state.tool_results.get("sandbox_result", {})
            
            # Metrics
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.metric("Sandbox", "Docker", "Isolated")
            with c2:
                st.metric("Network", "DISABLED", "-")
            with c3:
                passed = sandbox_result.get("tests_passed", 0)
                total = sandbox_result.get("tests_total", 0)
                st.metric("Tests Passed", f"{passed}/{total}", "Verified" if passed == total and total > 0 else "Failed")
            with c4:
                st.metric("Status", "VERIFIED" if state.verified else "UNVERIFIED")

            st.divider()

            # Code display
            code = state.tool_results.get("generated_code", "")
            if code:
                st.markdown("### Generated Code")
                st.code(code, language="python")

            # Execution output
            output = sandbox_result.get("test_output", "")
            if output:
                st.markdown("### Sandbox Execution Output")
                st.text(output)

            if not state.verified:
                st.error("Verification failed. See execution trace for details.")
