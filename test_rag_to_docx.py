import os
import sys

sys.path.insert(0, ".")

from tools.search import ask_knowledge_base, search_knowledge_base
from tools.docx_generator import create_document_from_markdown

def run_rag_to_docx():
    print("1. Querying Local Knowledge Base (RAG)...")
    query = "What are the standard operating procedures and safety rules for high pressure pump maintenance?"
    
    # Perform RAG retrieval + LLM synthesis
    rag_result = ask_knowledge_base(query)
    
    answer = rag_result.get("answer", "No answer generated.")
    sources = rag_result.get("sources", [])
    
    print(f"\nRetrieved {len(sources)} sources from Knowledge Base.")
    print("Answer snippet:", answer[:150], "...\n")
    
    # Compile RAG output into Markdown document format
    md_content = f"# RAG KNOWLEDGE BASE REPORT\n\n"
    md_content += f"## Query\n{query}\n\n"
    md_content += f"## Synthesized RAG Summary\n{answer}\n\n"
    md_content += f"## Reference Sources & SOP Citations\n"
    
    for i, s in enumerate(sources, 1):
        doc_name = s.get("document", "Unknown Document")
        page = s.get("page", 1)
        snippet = s.get("text", "")[:200].strip()
        md_content += f"- **Source {i}**: `{doc_name}` (Page {page})\n  - *Excerpt*: \"{snippet}...\"\n"
        
    print("2. Generating Word (.docx) Document from RAG results...")
    doc_res = create_document_from_markdown(md_content, title="RAG_Pump_Safety_Approval_Report")
    
    print("\n=== DOCUMENT GENERATION RESULT ===")
    print("Success:", doc_res["success"])
    print("Output Path:", doc_res["path"])
    print("File Size:", doc_res["size"], "bytes")

if __name__ == "__main__":
    run_rag_to_docx()
