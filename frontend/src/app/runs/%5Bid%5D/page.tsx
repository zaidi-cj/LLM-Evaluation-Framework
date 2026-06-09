"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { api, Project, EvaluationRun, EvaluationResult, RegressionAlert } from "@/lib/api";
import { ArrowLeft, AlertTriangle, AlertCircle, DollarSign, Activity, FileText, CheckCircle2, XCircle } from "lucide-react";

export default function RunDetails() {
  const params = useParams();
  const runId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [run, setRun] = useState<EvaluationRun | null>(null);
  const [results, setResults] = useState<EvaluationResult[]>([]);
  const [regressions, setRegressions] = useState<RegressionAlert[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedResult, setExpandedResult] = useState<string | null>(null);

  useEffect(() => {
    const loadRunData = async () => {
      try {
        const runData = await api.getRun(runId);
        setRun(runData);

        const projData = await api.getProject(runData.project_id);
        setProject(projData);

        const resultsData = await api.getRunResults(runId);
        setResults(resultsData);

        const regressionsData = await api.getRegressions(runData.project_id, runId);
        setRegressions(regressionsData);
      } catch (err) {
        console.error("Failed to load run details:", err);
      } finally {
        setLoading(false);
      }
    };
    loadRunData();
  }, [runId]);

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "100px 20px" }}>
        <div className="spinning" style={{ display: "inline-block", width: "40px", height: "40px", border: "4px solid var(--border-color)", borderTopColor: "var(--accent-primary)", borderRadius: "50%", marginBottom: "20px" }}></div>
        <p style={{ color: "var(--text-secondary)" }}>Analysing benchmarks data...</p>
      </div>
    );
  }

  if (!run || !project) {
    return (
      <div className="glass-card" style={{ textAlign: "center", padding: "40px" }}>
        <h3>Run Details Not Found</h3>
        <p>This run may not exist or has been deleted.</p>
        <Link href="/" className="btn btn-primary" style={{ marginTop: "20px" }}>Go Home</Link>
      </div>
    );
  }

  const stats = run.summary_stats || {};
  const scoreKeys = stats.avg_scores ? Object.keys(stats.avg_scores) : [];

  return (
    <div>
      <header style={{ marginBottom: "30px" }}>
        <Link href={`/projects/${project.id}`} style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "0.9rem", color: "var(--text-secondary)", marginBottom: "15px" }}>
          <ArrowLeft size={16} />
          <span>Back to {project.name}</span>
        </Link>
        
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ fontSize: "2rem", fontWeight: "700" }}>Run Analysis</h1>
            <p style={{ color: "var(--text-secondary)", marginTop: "4px" }}>
              Evaluating model <strong>{run.model_config.model_name}</strong> executed on {new Date(run.created_at).toLocaleString()}
            </p>
          </div>
          <span className="badge badge-completed">COMPLETED</span>
        </div>
      </header>

      {/* Aggregate Stats Cards */}
      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "20px", marginBottom: "30px" }}>
        <div className="glass-card" style={{ padding: "20px" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Total Token Cost</span>
          <span style={{ fontSize: "1.8rem", fontWeight: "700", color: "var(--color-success)", display: "flex", alignItems: "center", marginTop: "5px" }}>
            <DollarSign size={20} />
            {stats.total_cost?.toFixed(5) || "0.00"}
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginTop: "4px" }}>
            Prompt: {stats.total_prompt_tokens?.toLocaleString()} | Comp: {stats.total_completion_tokens?.toLocaleString()}
          </span>
        </div>

        <div className="glass-card" style={{ padding: "20px" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>Average Latency</span>
          <span style={{ fontSize: "1.8rem", fontWeight: "700", color: "white", display: "flex", alignItems: "center", marginTop: "5px" }}>
            {stats.avg_latency?.toFixed(2) || "0.00"}s
          </span>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginTop: "4px" }}>
            Average response time
          </span>
        </div>

        {scoreKeys.map((key) => {
          const scoreVal = stats.avg_scores?.[key] || 0;
          return (
            <div key={key} className="glass-card" style={{ padding: "20px" }}>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>
                {key.replace("_", " ")}
              </span>
              <span style={{ fontSize: "1.8rem", fontWeight: "700", color: "var(--accent-primary)", display: "block", marginTop: "5px" }}>
                {(scoreVal * 100).toFixed(1)}%
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", display: "block", marginTop: "4px" }}>
                Average evaluation score
              </span>
            </div>
          );
        })}
      </section>

      {/* Regression Alerts Section */}
      {regressions.length > 0 && (
        <section className="glass-card" style={{ borderColor: "rgba(239, 68, 68, 0.3)", background: "rgba(239, 68, 68, 0.02)", marginBottom: "30px" }}>
          <h3 style={{ fontSize: "1.2rem", color: "#fca5a5", marginBottom: "15px", display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertTriangle size={18} color="var(--color-danger)" />
            <span>Regression Alerts ({regressions.length} detected)</span>
          </h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "20px" }}>
            The following test queries suffered score drops of <strong>&ge; 5%</strong> compared to the baseline previous run.
          </p>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {regressions.map((alert, idx) => (
              <div key={idx} style={{ background: "rgba(10,15,30,0.8)", border: "1px solid rgba(239,68,68,0.15)", padding: "15px", borderRadius: "10px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div style={{ flex: 1, paddingRight: "15px" }}>
                  <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: "600" }}>
                    Metric: <span style={{ color: "var(--accent-secondary)" }}>{alert.metric_name}</span>
                  </div>
                  <div style={{ color: "var(--text-primary)", fontSize: "0.9rem", marginTop: "4px", fontWeight: "500" }}>
                    &ldquo;{alert.input_query}&rdquo;
                  </div>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "15px", textAlign: "right" }}>
                  <div style={{ fontSize: "0.85rem", color: "var(--text-secondary)" }}>
                    {alert.previous_score * 100}% &rarr; <strong style={{ color: "var(--color-danger)" }}>{alert.current_score * 100}%</strong>
                  </div>
                  <div style={{ background: "var(--color-danger-bg)", color: "var(--color-danger)", padding: "4px 10px", borderRadius: "6px", fontSize: "0.75rem", fontWeight: "700" }}>
                    -{alert.drop_percentage}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Detailed Results Log Explorer */}
      <section className="glass-card">
        <h3 style={{ fontSize: "1.25rem", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
          <FileText size={18} color="var(--accent-primary)" />
          <span>Test Case Execution Results Explorer</span>
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "15px" }}>
          {results.map((res) => {
            const isExpanded = expandedResult === res.id;
            const hasError = !!res.error_message;
            
            return (
              <div
                key={res.id}
                style={{
                  border: "1px solid var(--border-color)",
                  borderRadius: "12px",
                  background: isExpanded ? "rgba(10, 15, 30, 0.6)" : "transparent",
                  transition: "var(--transition-smooth)",
                  overflow: "hidden"
                }}
              >
                {/* Header Row */}
                <div
                  onClick={() => setExpandedResult(isExpanded ? null : res.id)}
                  style={{
                    padding: "16px 20px",
                    cursor: "pointer",
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    flexWrap: "wrap",
                    gap: "10px"
                  }}
                >
                  <div style={{ flex: 1, minWidth: "250px" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {hasError ? (
                        <XCircle size={16} color="var(--color-danger)" />
                      ) : (
                        <CheckCircle2 size={16} color="var(--color-success)" />
                      )}
                      <span style={{ fontSize: "0.95rem", fontWeight: "600", color: "var(--text-primary)" }}>
                        {res.test_case?.input_query || "TestCase Query"}
                      </span>
                    </div>
                  </div>

                  {/* Badges / Metrics */}
                  <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      {res.latency_seconds?.toFixed(2)}s
                    </span>
                    <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>
                      ${res.token_usage?.total_cost?.toFixed(5) || "0.00"}
                    </span>
                    
                    {!hasError && res.metric_scores && (
                      <div style={{ display: "flex", gap: "6px" }}>
                        {Object.entries(res.metric_scores).map(([metric, score]) => (
                          <span
                            key={metric}
                            style={{
                              background: "rgba(59,130,246,0.08)",
                              color: "var(--accent-primary)",
                              border: "1px solid rgba(59,130,246,0.15)",
                              padding: "2px 8px",
                              borderRadius: "6px",
                              fontSize: "0.75rem",
                              fontWeight: "600"
                            }}
                          >
                            {metric.replace("_", " ")}: {score.toFixed(2)}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>

                {/* Collapsible Content Body */}
                {isExpanded && (
                  <div style={{ padding: "0 20px 20px 20px", borderTop: "1px solid var(--border-color)", background: "rgba(5, 8, 20, 0.4)", fontSize: "0.9rem" }}>
                    {hasError ? (
                      <div style={{ marginTop: "15px" }}>
                        <span style={{ color: "var(--color-danger)", fontWeight: "600", fontSize: "0.8rem", textTransform: "uppercase" }}>Error Details:</span>
                        <pre style={{ background: "rgba(239,68,68,0.05)", border: "1px solid rgba(239,68,68,0.15)", color: "#fca5a5", padding: "15px", borderRadius: "8px", marginTop: "6px", overflowX: "auto", fontFamily: "monospace" }}>
                          {res.error_message}
                        </pre>
                      </div>
                    ) : (
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px", marginTop: "15px" }}>
                        <div>
                          <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: "600", marginBottom: "6px" }}>Reference Expected Output:</div>
                          <pre style={{ background: "rgba(255,255,255,0.02)", border: "1px solid var(--border-color)", padding: "12px", borderRadius: "8px", color: "var(--text-secondary)", whiteSpace: "pre-wrap", maxHeight: "250px", overflowY: "auto" }}>
                            {res.test_case?.expected_output || "No expected output baseline defined."}
                          </pre>
                        </div>
                        <div>
                          <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: "600", marginBottom: "6px" }}>Generated Model Output:</div>
                          <pre style={{ background: "rgba(59,130,246,0.03)", border: "1px solid rgba(59,130,246,0.15)", padding: "12px", borderRadius: "8px", color: "white", whiteSpace: "pre-wrap", maxHeight: "250px", overflowY: "auto" }}>
                            {res.generated_output}
                          </pre>
                        </div>
                        {res.test_case?.context_references && res.test_case.context_references.length > 0 && (
                          <div style={{ gridColumn: "span 2", marginTop: "10px" }}>
                            <div style={{ color: "var(--text-muted)", fontSize: "0.75rem", textTransform: "uppercase", fontWeight: "600", marginBottom: "6px" }}>Retrieved Context Documents (RAG):</div>
                            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                              {res.test_case.context_references.map((doc, idx) => (
                                <div key={idx} style={{ background: "rgba(255,255,255,0.01)", border: "1px solid var(--border-color)", padding: "10px", borderRadius: "8px", color: "var(--text-secondary)", fontSize: "0.85rem" }}>
                                  <strong>[{idx + 1}]</strong> {doc}
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
