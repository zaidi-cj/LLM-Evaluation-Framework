"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, Project, EvaluationRun } from "@/lib/api";
import { Plus, FolderKanban, Cpu, HelpCircle, Layers, ArrowRight, DollarSign, Database, Code } from "lucide-react";

export default function DashboardHome() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [loading, setLoading] = useState(true);

  // New Project Form State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [projName, setProjName] = useState("");
  const [projDesc, setProjDesc] = useState("");
  const [benchmarkType, setBenchmarkType] = useState("RAG");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    try {
      const projs = await api.getProjects();
      setProjects(projs);

      // Fetch runs for all projects to calculate global stats
      const allRuns: EvaluationRun[] = [];
      for (const p of projs) {
        try {
          const projectRuns = await api.getProjectRuns(p.id);
          allRuns.push(...projectRuns);
        } catch (e) {
          console.error(`Error loading runs for project ${p.id}:`, e);
        }
      }
      setRuns(allRuns);
    } catch (err) {
      console.error("Failed to load dashboard data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!projName.trim()) return;

    setSubmitting(true);
    setError(null);
    try {
      await api.createProject(projName, projDesc, benchmarkType);
      setProjName("");
      setProjDesc("");
      setShowCreateModal(false);
      // Reload projects
      await loadData();
      // Force reload layout sidebar
      window.location.reload();
    } catch (err: any) {
      setError(err.message || "Failed to create project");
    } finally {
      setSubmitting(false);
    }
  };

  // Global Stat Calculations
  const completedRuns = runs.filter(r => r.status === "COMPLETED");
  const runningRuns = runs.filter(r => r.status === "RUNNING");
  
  const totalCost = completedRuns.reduce((sum, r) => sum + (r.summary_stats?.total_cost || 0), 0);
  const totalTokens = completedRuns.reduce((sum, r) => 
    sum + (r.summary_stats?.total_prompt_tokens || 0) + (r.summary_stats?.total_completion_tokens || 0), 0
  );
  
  const getIconForType = (type: string) => {
    switch (type) {
      case "RAG": return <Layers size={18} color="var(--color-info)" />;
      case "SQL": return <Database size={18} color="var(--accent-primary)" />;
      case "CODE": return <Code size={18} color="var(--accent-secondary)" />;
      default: return <HelpCircle size={18} color="var(--text-muted)" />;
    }
  };

  return (
    <div>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "40px" }}>
        <div>
          <h1 style={{ fontSize: "2.2rem", fontWeight: "700", background: "linear-gradient(135deg, #fff 0%, #a5b4fc 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
            LLM Evaluation Hub
          </h1>
          <p style={{ color: "var(--text-secondary)", marginTop: "6px" }}>
            Benchmark performance, track regressions, and monitor prompt drift.
          </p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={18} />
          <span>New Benchmark</span>
        </button>
      </header>

      {/* Global Stat Cards */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "20px", marginBottom: "40px" }}>
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Total Benchmarks</span>
          <span style={{ fontSize: "2rem", fontWeight: "700" }}>{projects.length}</span>
          <span style={{ fontSize: "0.8rem", color: "var(--color-info)" }}>Configured Domains</span>
        </div>
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Runs Executed</span>
          <span style={{ fontSize: "2rem", fontWeight: "700" }}>{runs.length}</span>
          <span style={{ fontSize: "0.8rem", color: "var(--text-secondary)" }}>
            {runningRuns.length > 0 ? `${runningRuns.length} Running Now` : "0 Active Jobs"}
          </span>
        </div>
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Cumulative LLM Cost</span>
          <span style={{ fontSize: "2rem", fontWeight: "700", color: "var(--color-success)", display: "flex", alignItems: "center" }}>
            <DollarSign size={24} style={{ marginRight: "-2px" }} />
            {totalCost.toFixed(4)}
          </span>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {totalTokens.toLocaleString()} Total Tokens
          </span>
        </div>
        <div className="glass-card" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Avg Success Rate</span>
          <span style={{ fontSize: "2rem", fontWeight: "700", color: "var(--color-info)" }}>
            {completedRuns.length > 0 
              ? `${(completedRuns.reduce((sum, r) => sum + (r.summary_stats?.success_rate || 0), 0) / completedRuns.length * 100).toFixed(1)}%`
              : "0.0%"}
          </span>
          <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Test executions</span>
        </div>
      </section>

      {/* Main Grid: Projects */}
      <h2 style={{ fontSize: "1.5rem", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
        <FolderKanban size={20} color="var(--accent-primary)" />
        <span>Active Projects</span>
      </h2>

      {loading ? (
        <div className="glass-card" style={{ textAlign: "center", padding: "60px 20px" }}>
          <div className="spinning" style={{ display: "inline-block", width: "30px", height: "30px", border: "3px solid var(--border-color)", borderTopColor: "var(--accent-primary)", borderRadius: "50%", marginBottom: "15px" }}></div>
          <p style={{ color: "var(--text-secondary)" }}>Loading benchmark statistics...</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-card" style={{ textAlign: "center", padding: "60px 20px" }}>
          <HelpCircle size={48} style={{ color: "var(--text-muted)", marginBottom: "15px" }} />
          <h3 style={{ fontSize: "1.2rem", marginBottom: "8px" }}>No Projects Found</h3>
          <p style={{ color: "var(--text-secondary)", maxWidth: "450px", margin: "0 auto 20px auto" }}>
            Get started by creating your first evaluation project. You can define test cases and run automated regressions across multiple models.
          </p>
          <button className="btn btn-primary" onClick={() => setShowCreateModal(true)}>
            Create Project
          </button>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))", gap: "25px" }}>
          {projects.map((proj) => {
            const projRuns = runs.filter(r => r.project_id === proj.id);
            const latestRun = projRuns.length > 0 ? projRuns[0] : null; // Already sorted in desc in API or local
            
            return (
              <div key={proj.id} className="glass-card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                <div>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "15px" }}>
                    <span className="badge badge-completed" style={{ background: "rgba(59, 130, 246, 0.1)", color: "var(--accent-primary)", border: "1px solid rgba(59, 130, 246, 0.2)" }}>
                      {proj.benchmark_type} Evaluation
                    </span>
                    {getIconForType(proj.benchmark_type)}
                  </div>
                  
                  <h3 style={{ fontSize: "1.25rem", marginBottom: "8px" }}>{proj.name}</h3>
                  <p style={{ color: "var(--text-secondary)", fontSize: "0.9rem", minHeight: "48px", overflow: "hidden", textOverflow: "ellipsis", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical" }}>
                    {proj.description || "No description provided."}
                  </p>
                </div>

                <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "15px", marginTop: "20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                    {projRuns.length} runs executed
                  </div>
                  <Link href={`/projects/${proj.id}`} className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: "0.85rem" }}>
                    <span>View Benchmark</span>
                    <ArrowRight size={14} />
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Create Modal overlay */}
      {showCreateModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="glass-card" style={{ width: "90%", maxWidth: "500px", transform: "none" }} onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontSize: "1.4rem", marginBottom: "20px", color: "white" }}>Create Evaluation Project</h3>
            
            {error && (
              <div style={{ background: "var(--color-danger-bg)", border: "1px solid rgba(239,68,68,0.2)", padding: "12px", borderRadius: "8px", marginBottom: "15px", fontSize: "0.85rem", color: "#fca5a5" }}>
                {error}
              </div>
            )}

            <form onSubmit={handleCreateProject}>
              <div className="form-group">
                <label className="form-label">Project Name</label>
                <input
                  type="text"
                  className="form-input"
                  placeholder="e.g. RAG Customer Support Bot"
                  value={projName}
                  onChange={(e) => setProjName(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  className="form-textarea"
                  placeholder="Summarize what queries this benchmark covers..."
                  value={projDesc}
                  onChange={(e) => setProjDesc(e.target.value)}
                  rows={3}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Benchmark Type & Evaluator</label>
                <select
                  className="form-select"
                  value={benchmarkType}
                  onChange={(e) => setBenchmarkType(e.target.value)}
                >
                  <option value="RAG">RAG (Retrieval Grounding & Relevance)</option>
                  <option value="SQL">SQL (In-memory DB Execution Check)</option>
                  <option value="CODE">CODE (Restricted Sandbox Testcases)</option>
                  <option value="SUMMARIZATION">SUMMARIZATION (Text Overlap & LLM Judge)</option>
                  <option value="GENERAL">GENERAL (General Instruction-Following)</option>
                </select>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "30px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submitting}>
                  {submitting ? "Creating..." : "Create Project"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
