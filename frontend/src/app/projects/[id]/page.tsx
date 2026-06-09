"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { api, Project, EvaluationRun, TestCase, DriftStats } from "@/lib/api";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import { Play, Upload, List, AlertTriangle, PlayCircle, Plus, Info, Clock, DollarSign } from "lucide-react";

export default function ProjectDetails() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.id as string;

  const [project, setProject] = useState<Project | null>(null);
  const [runs, setRuns] = useState<EvaluationRun[]>([]);
  const [testCases, setTestCases] = useState<TestCase[]>([]);
  const [driftData, setDriftData] = useState<DriftStats[]>([]);
  const [loading, setLoading] = useState(true);

  // Trigger Run State
  const [modelName, setModelName] = useState("gemini/gemini-1.5-flash");
  const [temperature, setTemperature] = useState(0.0);
  const [systemPrompt, setSystemPrompt] = useState("");
  const [triggering, setTriggering] = useState(false);

  // Batch Upload State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [uploadJson, setUploadJson] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const loadProjectData = async () => {
    try {
      const proj = await api.getProject(projectId);
      setProject(proj);

      const runsData = await api.getProjectRuns(projectId);
      setRuns(runsData);

      const cases = await api.getTestCases(projectId);
      setTestCases(cases);

      const drift = await api.getDrift(projectId);
      setDriftData(drift);
    } catch (err) {
      console.error("Failed to load project details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProjectData();
    // Poll runs every 8 seconds if there are PENDING or RUNNING runs
    const hasActiveRuns = runs.some(r => r.status === "PENDING" || r.status === "RUNNING");
    let interval: any;
    if (hasActiveRuns) {
      interval = setInterval(async () => {
        const runsData = await api.getProjectRuns(projectId);
        setRuns(runsData);
      }, 8000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [runs, projectId]);

  const handleTriggerRun = async (e: React.FormEvent) => {
    e.preventDefault();
    if (testCases.length === 0) {
      alert("Please upload test cases before running a benchmark.");
      return;
    }

    setTriggering(true);
    try {
      const newRun = await api.triggerRun(projectId, modelName, temperature, systemPrompt);
      // Reload runs
      const runsData = await api.getProjectRuns(projectId);
      setRuns(runsData);
      // Clear triggering spinner
      alert(`Evaluation started on ${modelName}! It will execute in the background.`);
    } catch (err: any) {
      alert(`Failed to start evaluation run: ${err.message}`);
    } finally {
      setTriggering(false);
    }
  };

  const handleBatchUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    setUploadError(null);
    setUploading(true);

    try {
      const parsed = JSON.parse(uploadJson);
      if (!Array.isArray(parsed)) {
        throw new Error("JSON must be a list of test cases.");
      }
      
      // Verify structure
      for (const item of parsed) {
        if (!item.input_query) {
          throw new Error("Every test case object must contain 'input_query'.");
        }
      }

      await api.batchCreateTestCases(projectId, parsed);
      setUploadJson("");
      setShowUploadModal(false);
      
      // Reload cases
      const cases = await api.getTestCases(projectId);
      setTestCases(cases);
    } catch (err: any) {
      setUploadError(err.message || "Failed to upload test cases.");
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "100px 20px" }}>
        <div className="spinning" style={{ display: "inline-block", width: "40px", height: "40px", border: "4px solid var(--border-color)", borderTopColor: "var(--accent-primary)", borderRadius: "50%", marginBottom: "20px" }}></div>
        <p style={{ color: "var(--text-secondary)" }}>Fetching project specifications...</p>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="glass-card" style={{ textAlign: "center", padding: "40px" }}>
        <h3>Project Not Found</h3>
        <p>This project may have been deleted.</p>
        <Link href="/" className="btn btn-primary" style={{ marginTop: "20px" }}>Go Home</Link>
      </div>
    );
  }

  // Formatting Recharts data for drift tracking
  const chartData = driftData.map((d) => {
    const formattedDate = new Date(d.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
    const scoreMetrics = Object.keys(d.avg_scores);
    const scoreObj: Record<string, number> = {};
    scoreMetrics.forEach((m) => {
      scoreObj[m] = parseFloat((d.avg_scores[m] * 100).toFixed(1)); // Convert to %
    });

    return {
      name: formattedDate,
      model: d.model_name.split("/").pop(),
      latency: d.avg_latency,
      cost: d.avg_cost,
      ...scoreObj
    };
  });

  const allScoreKeys = Array.from(
    new Set(driftData.flatMap((d) => Object.keys(d.avg_scores)))
  );

  return (
    <div>
      <header style={{ marginBottom: "40px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <span className="badge badge-completed" style={{ background: "rgba(139, 92, 246, 0.12)", color: "var(--accent-secondary)", border: "1px solid rgba(139, 92, 246, 0.2)" }}>
              {project.benchmark_type} Domain
            </span>
            <h1 style={{ fontSize: "2.2rem", fontWeight: "700", marginTop: "10px" }}>{project.name}</h1>
            <p style={{ color: "var(--text-secondary)", marginTop: "6px" }}>{project.description || "No description."}</p>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button className="btn btn-secondary" onClick={() => setShowUploadModal(true)}>
              <Upload size={16} />
              <span>Bulk Upload ({testCases.length})</span>
            </button>
          </div>
        </div>
      </header>

      {/* Grid: Trigger Panel & Performance Drift Chart */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(400px, 1fr))", gap: "30px", marginBottom: "40px" }}>
        
        {/* Trigger Evaluation Form */}
        <div className="glass-card">
          <h3 style={{ fontSize: "1.25rem", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
            <PlayCircle size={18} color="var(--accent-primary)" />
            <span>Launch Evaluation Run</span>
          </h3>

          <form onSubmit={handleTriggerRun}>
            <div className="form-group">
              <label className="form-label">Target Model</label>
              <select
                className="form-select"
                value={modelName}
                onChange={(e) => setModelName(e.target.value)}
              >
                <option value="gemini/gemini-1.5-flash">Gemini 1.5 Flash</option>
                <option value="gemini/gemini-1.5-pro">Gemini 1.5 Pro</option>
                <option value="openai/gpt-4o">GPT-4o</option>
                <option value="openai/gpt-4o-mini">GPT-4o Mini</option>
                <option value="anthropic/claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                <option value="ollama/llama3">Local Llama 3 (Ollama)</option>
                <option value="ollama/qwen2">Local Qwen 2 (Ollama)</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Temperature: {temperature}</label>
              <input
                type="range"
                min="0.0"
                max="1.2"
                step="0.1"
                className="form-input"
                style={{ padding: "0" }}
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
              />
            </div>

            <div className="form-group">
              <label className="form-label">System Prompt / Instructions</label>
              <textarea
                className="form-textarea"
                placeholder="Instruct the model on tone, output rules, formatting constraint..."
                rows={4}
                value={systemPrompt}
                onChange={(e) => setSystemPrompt(e.target.value)}
              />
            </div>

            <button type="submit" className="btn btn-primary" style={{ width: "100%" }} disabled={triggering || testCases.length === 0}>
              <Play size={16} />
              <span>{triggering ? "Queueing Run..." : "Trigger Benchmark"}</span>
            </button>
            {testCases.length === 0 && (
              <p style={{ color: "var(--color-danger)", fontSize: "0.8rem", marginTop: "10px", textAlign: "center" }}>
                Add test cases first to enable triggering.
              </p>
            )}
          </form>
        </div>

        {/* Performance Drift Line Chart */}
        <div className="glass-card" style={{ display: "flex", flexDirection: "column" }}>
          <h3 style={{ fontSize: "1.25rem", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
            <Clock size={18} color="var(--accent-secondary)" />
            <span>Metric Drift History</span>
          </h3>

          {chartData.length < 2 ? (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", border: "1px dashed var(--border-color)", borderRadius: "12px", padding: "40px" }}>
              <Info size={36} color="var(--text-muted)" style={{ marginBottom: "12px" }} />
              <p style={{ color: "var(--text-secondary)", textAlign: "center" }}>
                Need at least 2 completed evaluation runs to render a drift trend timeline.
              </p>
            </div>
          ) : (
            <div style={{ flex: 1, minHeight: "260px" }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={11} />
                  <YAxis domain={[0, 100]} stroke="var(--text-muted)" fontSize={11} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "rgba(10,15,30,0.95)", borderColor: "var(--border-color)", borderRadius: "8px" }}
                    labelStyle={{ color: "white", fontWeight: "600" }}
                  />
                  <Legend wrapperStyle={{ fontSize: 12, paddingTop: 10 }} />
                  {allScoreKeys.map((key, i) => {
                    const colors = ["#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444"];
                    const color = colors[i % colors.length];
                    return (
                      <Line
                        key={key}
                        type="monotone"
                        dataKey={key}
                        stroke={color}
                        strokeWidth={2.5}
                        activeDot={{ r: 6 }}
                        name={`${key.replace("_", " ").toUpperCase()} (%)`}
                      />
                    );
                  })}
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      </div>

      {/* Historical Runs Table */}
      <section className="glass-card" style={{ overflowX: "auto" }}>
        <h3 style={{ fontSize: "1.25rem", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
          <List size={18} color="var(--color-info)" />
          <span>Evaluation Run History</span>
        </h3>

        {runs.length === 0 ? (
          <p style={{ color: "var(--text-muted)", textAlign: "center", padding: "30px 0" }}>No evaluation runs triggered yet.</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", minWidth: "600px", textAlign: "left" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid var(--border-color)", paddingBottom: "10px" }}>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Run Date</th>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Model</th>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Status</th>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Success Rate</th>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Cost</th>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Avg Latency</th>
                <th style={{ padding: "12px 8px", color: "var(--text-muted)", fontSize: "0.8rem", textTransform: "uppercase" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const dateStr = new Date(run.created_at).toLocaleString();
                const stats = run.summary_stats;
                
                return (
                  <tr key={run.id} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)", transition: "var(--transition-smooth)" }}>
                    <td style={{ padding: "16px 8px", fontSize: "0.9rem" }}>{dateStr}</td>
                    <td style={{ padding: "16px 8px", fontSize: "0.9rem", fontWeight: "600" }}>{run.model_config.model_name}</td>
                    <td style={{ padding: "16px 8px" }}>
                      <span className={`badge badge-${run.status.toLowerCase()}`}>
                        {run.status}
                      </span>
                    </td>
                    <td style={{ padding: "16px 8px", fontSize: "0.9rem" }}>
                      {stats ? `${(stats.success_rate * 100).toFixed(0)}%` : "-"}
                    </td>
                    <td style={{ padding: "16px 8px", fontSize: "0.9rem", color: "var(--color-success)" }}>
                      {stats ? `$${stats.total_cost?.toFixed(4)}` : "-"}
                    </td>
                    <td style={{ padding: "16px 8px", fontSize: "0.9rem" }}>
                      {stats ? `${stats.avg_latency?.toFixed(2)}s` : "-"}
                    </td>
                    <td style={{ padding: "16px 8px" }}>
                      {run.status === "COMPLETED" && (
                        <Link href={`/runs/${run.id}`} className="btn btn-secondary" style={{ padding: "5px 10px", fontSize: "0.8rem" }}>
                          Analyze Results
                        </Link>
                      )}
                      {run.status === "FAILED" && (
                        <span style={{ fontSize: "0.8rem", color: "var(--color-danger)" }} title={run.error_message || ""}>
                          Error details
                        </span>
                      )}
                      {(run.status === "RUNNING" || run.status === "PENDING") && (
                        <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Evaluating...</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>

      {/* Batch Upload Modal Overlay */}
      {showUploadModal && (
        <div style={{ position: "fixed", top: 0, left: 0, right: 0, bottom: 0, background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyItems: "center", justifyContent: "center", zIndex: 1000 }}>
          <div className="glass-card" style={{ width: "95%", maxWidth: "600px", transform: "none" }}>
            <h3 style={{ fontSize: "1.4rem", marginBottom: "15px", color: "white" }}>Batch Upload Test Cases</h3>
            <p style={{ color: "var(--text-secondary)", fontSize: "0.85rem", marginBottom: "20px" }}>
              Paste a JSON array of test cases. Every case requires an <strong>input_query</strong>. You can optionally supply <strong>expected_output</strong>, <strong>context_references</strong> (array of strings), and <strong>test_metadata</strong> (object).
            </p>

            {uploadError && (
              <div style={{ background: "var(--color-danger-bg)", border: "1px solid rgba(239,68,68,0.2)", padding: "12px", borderRadius: "8px", marginBottom: "15px", fontSize: "0.85rem", color: "#fca5a5" }}>
                {uploadError}
              </div>
            )}

            <form onSubmit={handleBatchUpload}>
              <div className="form-group">
                <label className="form-label">Test Cases JSON</label>
                <textarea
                  className="form-textarea"
                  style={{ fontFamily: "monospace", fontSize: "0.85rem" }}
                  rows={12}
                  placeholder={JSON.stringify([
                    {
                      input_query: "What is the capital of France?",
                      expected_output: "Paris is the capital of France.",
                      context_references: ["France is a country in Europe. Paris is its capital city."]
                    },
                    {
                      input_query: "Select all users older than 21",
                      expected_output: "SELECT * FROM users WHERE age > 21;",
                      test_metadata: {
                        schema_ddl: "CREATE TABLE users (id INT, age INT); INSERT INTO users VALUES (1, 25), (2, 18);"
                      }
                    }
                  ], null, 2)}
                  value={uploadJson}
                  onChange={(e) => setUploadJson(e.target.value)}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "20px" }}>
                <button type="button" className="btn btn-secondary" onClick={() => setShowUploadModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={uploading}>
                  {uploading ? "Uploading..." : "Save Test Cases"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
