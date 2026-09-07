"use client";

import { useState, useRef } from "react";
import { PageHeader } from "@/components/common/page-header";
import { GlassCard } from "@/components/common/glass-card";
import { documentService, DocumentProcessResult } from "@/lib/services/document";
import { Upload, FileText, CheckCircle2, AlertCircle, Loader2, File, Play } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/utils";

export default function DocumentToolsPage() {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [results, setResults] = useState<DocumentProcessResult[]>([]);
  const [selectedResult, setSelectedResult] = useState<DocumentProcessResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
      setResults([]);
      setSelectedResult(null);
    }
  };

  const handleProcess = async () => {
    if (selectedFiles.length === 0) return;
    
    setIsProcessing(true);
    setResults([]);
    setSelectedResult(null);
    
    try {
      const res = await documentService.batchProcess(selectedFiles);
      setResults(res);
    } catch (err) {
      console.error(err);
    } finally {
      setIsProcessing(false);
    }
  };

  const hasFiles = selectedFiles.length > 0;

  return (
    <div className="max-w-6xl mx-auto px-4 lg:px-8 py-8 h-full flex flex-col gap-8">
      <PageHeader
        title="Document Tools Suite"
        description="Batch process documents, run local OCR, and extract text securely."
        action={
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex items-center gap-2 bg-white/[0.04] hover:bg-white/[0.08] border border-white/[0.06] px-4 py-2.5 rounded-xl text-[12px] font-semibold tracking-wide text-gray-300 transition-all"
          >
            <Upload className="w-4 h-4" />
            Select Files
          </button>
        }
      />

      <input 
        type="file" 
        multiple 
        ref={fileInputRef} 
        onChange={handleFileChange}
        className="hidden" 
        accept=".pdf,.jpg,.jpeg,.png,.bmp"
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-200px)]">
        {/* Left Column: File List & Actions */}
        <div className="lg:col-span-1 flex flex-col gap-4 overflow-y-auto">
          <GlassCard className="p-5 flex flex-col gap-4 bg-surface/30">
            <div className="flex justify-between items-center">
              <h3 className="font-semibold text-white">Batch Queue ({selectedFiles.length})</h3>
              {hasFiles && !isProcessing && (
                <button 
                  onClick={handleProcess}
                  className="flex items-center gap-2 bg-accent/20 hover:bg-accent/30 border border-accent/40 px-3 py-1.5 rounded-lg text-xs font-bold text-accent transition-all"
                >
                  <Play className="w-3.5 h-3.5" /> Run OCR/Extract
                </button>
              )}
            </div>

            {!hasFiles && (
              <div 
                className="border-2 border-dashed border-white/10 rounded-xl p-8 flex flex-col items-center justify-center text-center cursor-pointer hover:bg-white/[0.02] transition-colors"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="w-8 h-8 text-gray-500 mb-3" />
                <p className="text-sm text-gray-400">Click or drag files here to begin</p>
                <p className="text-xs text-gray-600 mt-1">Supports PDF and Images</p>
              </div>
            )}

            {isProcessing && (
              <div className="flex flex-col items-center justify-center p-8 text-center text-gray-400">
                <Loader2 className="w-8 h-8 animate-spin text-accent mb-4" />
                <p className="text-sm font-medium">Processing {selectedFiles.length} documents...</p>
                <p className="text-xs text-gray-500 mt-1">Running local OCR & parsing text.</p>
              </div>
            )}

            {!isProcessing && selectedFiles.map((file, i) => {
              const res = results.find(r => r.filename === file.name);
              
              return (
                <div 
                  key={i} 
                  onClick={() => res && setSelectedResult(res)}
                  className={cn(
                    "flex items-center justify-between p-3 rounded-xl border border-white/[0.04] transition-all cursor-pointer",
                    res ? "bg-surface/50 hover:border-white/10" : "bg-white/[0.02]",
                    selectedResult?.filename === file.name && "border-accent/40 bg-accent/5"
                  )}
                >
                  <div className="flex items-center gap-3 overflow-hidden">
                    <File className="w-4 h-4 text-gray-400 shrink-0" />
                    <span className="text-sm text-gray-300 truncate" title={file.name}>{file.name}</span>
                  </div>
                  {res && (
                    res.status === "success" ? <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" /> : <AlertCircle className="w-4 h-4 text-red-400 shrink-0" />
                  )}
                </div>
              );
            })}
          </GlassCard>
        </div>

        {/* Right Column: Result Viewer */}
        <div className="lg:col-span-2 flex flex-col">
          <GlassCard className="flex-1 p-0 flex flex-col overflow-hidden bg-surface/30">
            {selectedResult ? (
              <div className="flex flex-col h-full">
                <div className="p-4 border-b border-white/[0.04] flex items-center justify-between bg-surface/50 shrink-0">
                  <div className="flex items-center gap-3">
                    <FileText className="w-5 h-5 text-accent" />
                    <h3 className="font-semibold text-white truncate max-w-sm">{selectedResult.filename}</h3>
                  </div>
                  <div className="flex items-center gap-2">
                    {selectedResult.status === "success" && selectedResult.data && (
                      <>
                        <span className="text-xs font-medium px-2 py-1 rounded bg-white/[0.04] text-gray-400">
                          {selectedResult.data.total_pages} pages
                        </span>
                        {selectedResult.data.needs_ocr ? (
                          <span className="text-xs font-medium px-2 py-1 rounded bg-orange-500/10 text-orange-400 border border-orange-500/20">Scanned / OCR Applied</span>
                        ) : (
                          <span className="text-xs font-medium px-2 py-1 rounded bg-blue-500/10 text-blue-400 border border-blue-500/20">Digital PDF</span>
                        )}
                      </>
                    )}
                  </div>
                </div>
                
                <div className="flex-1 overflow-y-auto p-5 relative">
                  {selectedResult.status === "success" && selectedResult.data ? (
                    <pre className="font-mono text-[13px] text-gray-300 whitespace-pre-wrap leading-relaxed">
                      {selectedResult.data.full_text || "No text could be extracted."}
                    </pre>
                  ) : (
                    <div className="text-center text-red-400 mt-10">
                      <AlertCircle className="w-8 h-8 mx-auto mb-3" />
                      <p>Error processing document.</p>
                      <p className="text-xs mt-1 text-red-400/70">{selectedResult.error}</p>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center opacity-30 select-none p-8">
                <FileText className="w-16 h-16 text-gray-500 mb-4" />
                <p className="text-lg font-medium text-gray-400">No Document Selected</p>
                <p className="text-sm text-gray-500 text-center mt-2 max-w-sm">
                  Run a batch process and click on a document in the queue to view the extracted text here.
                </p>
              </div>
            )}
          </GlassCard>
        </div>
      </div>
    </div>
  );
}
