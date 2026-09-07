"""
Re-ingest all knowledge_base documents with fresh start.
Deletes and recreates the vector store first.
"""
import sys
sys.path.insert(0, '.')
from rag.vector_store import delete_collection, get_collection_stats
from rag.ingest import ingest_directory

print("Deleting existing collection...")
delete_collection()
print("Collection deleted.")

print("\nStarting knowledge base re-ingestion with smaller chunks...")
result = ingest_directory("knowledge_base", progress_callback=print)
print("\n=== INGESTION RESULT ===")
print(f"Total files: {result.get('total_files')}")
print(f"Total chunks: {result.get('total_chunks')}")
for f in result.get('files', []):
    print(f"  {f['file']}: {f['chunks']} chunks, error={f.get('error')}")

print("\n=== VECTOR STORE STATS ===")
stats = get_collection_stats()
print(stats)
