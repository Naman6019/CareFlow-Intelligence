"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DocumentRecord = {
  id: string;
  filename: string;
  classification: "synthetic" | "public";
  byte_size: number;
  status: string;
  page_count: number;
  chunk_count: number;
};

type Citation = {
  number: number;
  document_id: string;
  filename: string;
  chunk_id: number;
  page_number: number | null;
  excerpt: string;
  rank: number;
};

type AgentTraceStep = {
  step: number;
  type: "tool" | "answer" | "fallback";
  tool_name: string | null;
  summary: string;
  tool_input: Record<string, unknown>;
  result_count: number;
  error_type?: string | null;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  responseMode?: string;
  model?: string | null;
  agentTrace?: AgentTraceStep[];
};

const suggestions = [
  "What data does this document describe?",
  "Summarize the main safety constraints.",
  "What workflow is recommended?",
];

export default function AssistantPage() {
  const [documents, setDocuments] = useState<DocumentRecord[]>([]);
  const [selectedDocuments, setSelectedDocuments] = useState<string[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [classification, setClassification] =
    useState<"synthetic" | "public">("synthetic");
  const [confirmed, setConfirmed] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadDocuments() {
    const response = await fetch(`${apiUrl}/api/documents`);
    if (response.ok) {
      const payload = await response.json();
      setDocuments(payload.documents);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  async function uploadDocument(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    const form = event.currentTarget;
    const fileInput = form.elements.namedItem("file") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file || !confirmed) {
      setError("Select a file and confirm it contains no real patient data.");
      return;
    }

    const body = new FormData();
    body.append("file", file);
    body.append("classification", classification);
    body.append("confirm_no_real_patient_data", "true");

    setUploading(true);
    const response = await fetch(`${apiUrl}/api/documents`, {
      method: "POST",
      body,
    });
    const payload = await response.json();
    setUploading(false);

    if (!response.ok) {
      setError(payload.detail ?? "Document upload failed.");
      return;
    }

    setSelectedDocuments((current) =>
      current.includes(payload.id) ? current : [...current, payload.id],
    );
    form.reset();
    setConfirmed(false);
    await loadDocuments();
  }

  async function sendQuestion(event: FormEvent) {
    event.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      return;
    }

    setError(null);
    setMessages((current) => [
      ...current,
      { role: "user", content: trimmedQuestion, citations: [] },
    ]);
    setQuestion("");
    setSending(true);

    const response = await fetch(`${apiUrl}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question: trimmedQuestion,
        session_id: sessionId,
        document_ids: selectedDocuments,
      }),
    });
    const payload = await response.json();
    setSending(false);

    if (!response.ok) {
      setError(payload.detail ?? "The grounded assistant failed.");
      return;
    }

    setSessionId(payload.session_id);
    setMessages((current) => [
      ...current,
      {
        role: "assistant",
        content: payload.answer,
        citations: payload.citations,
        responseMode: payload.response_mode,
        model: payload.model,
        agentTrace: payload.agent_trace,
      },
    ]);
  }

  function toggleDocument(documentId: string) {
    setSelectedDocuments((current) =>
      current.includes(documentId)
        ? current.filter((id) => id !== documentId)
        : [...current, documentId],
    );
  }

  return (
    <main className="assistant-shell">
      <div className="safety-banner">
        Synthetic/public documents only — selected excerpts are sent to
        OpenRouter. Never upload real patient data.
      </div>
      <nav className="nav patient-nav" aria-label="Assistant navigation">
        <Link className="brand brand-link" href="/">
          <span className="brand-mark" aria-hidden="true">
            C
          </span>
          CareFlow Intelligence
        </Link>
        <div className="nav-links">
          <Link className="nav-link" href="/patients">
            Patients
          </Link>
          <Link className="nav-link" href="/assistant">
            Assistant
          </Link>
        </div>
      </nav>

      <header className="page-header assistant-header">
        <div>
          <p className="eyebrow">Grounded document assistant</p>
          <h1>Ask your documents.</h1>
          <p>
            Nemotron plans searches, calls read-only tools, evaluates evidence,
            and returns validated citations.
          </p>
        </div>
        <span className="mode-badge">Document RAG Agent · v1</span>
      </header>

      <div className="assistant-grid">
        <aside className="document-panel">
          <form onSubmit={uploadDocument}>
            <h2>Upload document</h2>
            <input accept=".pdf,.txt,.md,.csv" name="file" type="file" />
            <label>
              Classification
              <select
                onChange={(event) =>
                  setClassification(
                    event.target.value as "synthetic" | "public",
                  )
                }
                value={classification}
              >
                <option value="synthetic">Synthetic</option>
                <option value="public">Public</option>
              </select>
            </label>
            <label className="confirmation-row">
              <input
                checked={confirmed}
                onChange={(event) => setConfirmed(event.target.checked)}
                type="checkbox"
              />
              This file contains no real patient data.
            </label>
            <button disabled={uploading} type="submit">
              {uploading ? "Processing…" : "Upload and index"}
            </button>
          </form>

          <section className="document-list">
            <div>
              <h2>Knowledge base</h2>
              <span>{documents.length}</span>
            </div>
            {documents.length ? (
              documents.map((document) => (
                <label className="document-item" key={document.id}>
                  <input
                    checked={selectedDocuments.includes(document.id)}
                    disabled={document.status !== "ready"}
                    onChange={() => toggleDocument(document.id)}
                    type="checkbox"
                  />
                  <span>
                    <strong>{document.filename}</strong>
                    <small>
                      {document.chunk_count} chunks · {document.classification}
                    </small>
                  </span>
                </label>
              ))
            ) : (
              <p className="panel-empty">Upload a document to begin.</p>
            )}
          </section>
        </aside>

        <section className="chat-panel">
          <div className="chat-messages" aria-live="polite">
            {messages.length ? (
              messages.map((message, index) => (
                <article
                  className={`chat-message message-${message.role}`}
                  key={`${message.role}-${index}`}
                >
                  <span>{message.role === "user" ? "You" : "Assistant"}</span>
                  {message.role === "assistant" && (
                    <small className="message-mode">
                      {message.responseMode ===
                      "agentic_rag_v1"
                        ? message.model ?? "Nemotron 3 Ultra"
                        : "Grounded extractive fallback"}
                    </small>
                  )}
                  <p>{message.content}</p>
                  {message.citations.length > 0 && (
                    <div className="citation-list">
                      {message.citations.map((citation) => (
                        <details key={citation.number}>
                          <summary>
                            [{citation.number}] {citation.filename}
                            {citation.page_number
                              ? ` · page ${citation.page_number}`
                              : ""}
                          </summary>
                          <p>{citation.excerpt}</p>
                        </details>
                      ))}
                    </div>
                  )}
                  {message.agentTrace && message.agentTrace.length > 0 && (
                    <details className="agent-trace">
                      <summary>
                        Agent trace · {message.agentTrace.length} steps
                      </summary>
                      <ol>
                        {message.agentTrace.map((step) => (
                          <li key={step.step}>
                            <strong>
                              {step.tool_name ?? step.type.replace("_", " ")}
                            </strong>
                            <span>{step.summary}</span>
                          </li>
                        ))}
                      </ol>
                    </details>
                  )}
                </article>
              ))
            ) : (
              <div className="chat-empty">
                <h2>Grounded answers, visible evidence.</h2>
                <p>Select documents, then ask a question.</p>
                <div>
                  {suggestions.map((suggestion) => (
                    <button
                      key={suggestion}
                      onClick={() => setQuestion(suggestion)}
                      type="button"
                    >
                      {suggestion}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {sending && (
              <p className="assistant-thinking">
                Searching documents and synthesizing…
              </p>
            )}
          </div>

          <form className="chat-composer" onSubmit={sendQuestion}>
            <textarea
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ask a question about the selected documents…"
              rows={3}
              value={question}
            />
            <div>
              <span>
                {selectedDocuments.length
                  ? `${selectedDocuments.length} documents selected`
                  : "Searching all ready documents"}
              </span>
              <button disabled={sending} type="submit">
                Send
              </button>
            </div>
          </form>
          {error && <p className="agent-error chat-error">{error}</p>}
        </section>
      </div>
    </main>
  );
}
