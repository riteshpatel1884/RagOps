"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Database, FlaskRound, Workflow, ArrowRight } from "lucide-react";
import { api } from "@/lib/api";

export default function DashboardPage() {
  const [docs, setDocs] = useState([]);
  const [pipelines, setPipelines] = useState([]);

  useEffect(() => {
    api.listDocuments().then(setDocs).catch(() => {});
    api.listPipelines().then(setPipelines).catch(() => {});
  }, []);

  const ready = docs.filter((d) => d.status === "ready").length;

  return (
    <div className="mx-auto max-w-4xl px-8 py-10">
      <h1 className="text-lg font-medium text-text">Overview</h1>
      <p className="mt-1 text-sm text-muted">
        RAGOps — Phase 0/2: configurable RAG pipelines. Evaluation, automated experiments,
        and comparison arrive in later phases.
      </p>

      <div className="mt-8 grid grid-cols-3 gap-4">
        <div className="rounded-md border border-border bg-surface p-5">
          <div className="text-2xl text-text">{docs.length}</div>
          <div className="mt-1 text-sm text-muted">documents uploaded</div>
        </div>
        <div className="rounded-md border border-border bg-surface p-5">
          <div className="text-2xl text-text">{ready}</div>
          <div className="mt-1 text-sm text-muted">indexed &amp; ready</div>
        </div>
        <div className="rounded-md border border-border bg-surface p-5">
          <div className="text-2xl text-text">{pipelines.length}</div>
          <div className="mt-1 text-sm text-muted">saved pipelines</div>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-3 gap-4">
        <Link
          href="/pipelines"
          className="group flex items-center justify-between rounded-md border border-border bg-surface p-5 transition-colors hover:bg-surfaceHover"
        >
          <span className="flex items-center gap-3 text-sm text-text">
            <Workflow size={16} className="text-accent" />
            Build a pipeline
          </span>
          <ArrowRight size={14} className="text-muted transition-transform group-hover:translate-x-0.5" />
        </Link>
        <Link
          href="/datasets"
          className="group flex items-center justify-between rounded-md border border-border bg-surface p-5 transition-colors hover:bg-surfaceHover"
        >
          <span className="flex items-center gap-3 text-sm text-text">
            <Database size={16} className="text-accent" />
            Upload a document
          </span>
          <ArrowRight size={14} className="text-muted transition-transform group-hover:translate-x-0.5" />
        </Link>
        <Link
          href="/playground"
          className="group flex items-center justify-between rounded-md border border-border bg-surface p-5 transition-colors hover:bg-surfaceHover"
        >
          <span className="flex items-center gap-3 text-sm text-text">
            <FlaskRound size={16} className="text-accent" />
            Open the playground
          </span>
          <ArrowRight size={14} className="text-muted transition-transform group-hover:translate-x-0.5" />
        </Link>
      </div>
    </div>
  );
}
