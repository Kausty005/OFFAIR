"""
ui/workbench_tab.py
General AI Workbench tab.
Allows free-form prompts, handles routing dynamically.
"""

import streamlit as st
import time

from agent.agent import run_agent, AgentState, AgentStep
from router.model_router import classify, get_routing_display
from tools.files import save_upload, get_temp_path

def render_workbench():
    st.header("General AI Workbench")
    st.markdown("Ask general questions, upload documents, or request calculations. The Sovereign Engine will automatically route your request to the appropriate local model.")

    # Chat history initialization
    if "workbench_chat" not in st.session_state:
        st.session_state.workbench_chat = []

    # File uploader
    uploaded_files = st.file_uploader(
        "Upload reference documents (Optional)", 
        accept_multiple_files=True,
        type=["pdf", "txt", "jpg", "jpeg", "png"]
    )

    # Prompt input
    prompt = st.chat_input("Enter your request...")

    # Display chat history
    for msg in st.session_state.workbench_chat:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "routing" in msg:
                with st.expander("Routing Decision"):
                    st.json(msg["routing"])
            if "agent_state" in msg:
                with st.expander("Execution Trace"):
                    state_summary = msg["agent_state"]
                    for step in state_summary.get("steps", []):
                        icon = "✅" if step["status"] == "done" else ("❌" if step["status"] == "error" else "⏳")
                        st.text(f"{icon} {step['desc']}")
            if "file" in msg:
                st.download_button("Download Output", data=open(msg["file"], "rb"), file_name=msg["filename"])

    if prompt:
        with st.chat_message("user"):
            st.markdown(prompt)
            if uploaded_files:
                st.caption(f"Attached: {', '.join(f.name for f in uploaded_files)}")
        
        st.session_state.workbench_chat.append({"role": "user", "content": prompt})

        with st.chat_message("assistant"):
            status_container = st.container()
            
            # Save files
            saved_paths = []
            has_image = False
            has_pdf = False
            
            with status_container:
                if uploaded_files:
                    with st.spinner("Saving uploads to secure workspace..."):
                        for f in uploaded_files:
                            path = save_upload(f.getvalue(), f.name)
                            saved_paths.append(str(path))
                            if f.name.lower().endswith((".jpg", ".jpeg", ".png")):
                                has_image = True
                            if f.name.lower().endswith(".pdf"):
                                has_pdf = True

                # Routing
                with st.spinner("Analyzing task..."):
                    decision = classify(prompt, has_image=has_image, has_pdf=has_pdf)
                    routing_disp = get_routing_display(decision)
                    
                st.info(f"**Task Detected:** {routing_disp['icon']} {routing_disp['task_type']} | **Model:** {routing_disp['selected_model']} | **Network:** {routing_disp['inference']}")
                
                # Agent execution
                steps_container = st.empty()
                progress_bar = st.progress(0)
                
                def on_step(step: AgentStep):
                    # Format current step trace
                    pass # Handled by the agent state returned at the end, but we could update UI live here

                with st.spinner(f"Executing local {routing_disp['task_type']} agent..."):
                    state = run_agent(
                        task=prompt,
                        uploaded_files=saved_paths,
                        has_image=has_image,
                        has_pdf=has_pdf,
                        # progress_callback=on_step
                    )

            if state.status == "done":
                st.markdown(state.final_output)
                
                msg_data = {
                    "role": "assistant",
                    "content": state.final_output,
                    "routing": routing_disp,
                    "agent_state": {
                        "steps": [{"desc": s.description, "status": s.status} for s in state.plan]
                    }
                }
                
                if state.output_files:
                    fpath = state.output_files[0]
                    fname = fpath.split("/")[-1] if "/" in fpath else fpath.split("\\")[-1]
                    with open(fpath, "rb") as f:
                        st.download_button(
                            label=f"Download {fname}",
                            data=f,
                            file_name=fname,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        )
                    msg_data["file"] = fpath
                    msg_data["filename"] = fname
                
                st.session_state.workbench_chat.append(msg_data)
            else:
                st.error(f"Agent execution failed: {state.error}")
