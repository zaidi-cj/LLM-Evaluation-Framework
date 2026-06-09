"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { api, Project } from "@/lib/api";
import "@/styles/globals.css";
import { FolderKanban, BarChart3, PlusCircle, Activity, Award } from "lucide-react";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchProjects = async () => {
    try {
      const data = await api.getProjects();
      setProjects(data);
    } catch (err) {
      console.error("Failed to fetch projects in layout:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    // Poll project list every 15s to keep sidebar sync
    const interval = setInterval(fetchProjects, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <html lang="en">
      <head>
        <title>LLM Evaluation Framework & Analytics Dashboard</title>
        <meta name="description" content="Custom LLM benchmark runner, regression analysis tracking, and performance drift visualization." />
      </head>
      <body>
        <div className="app-container">
          <aside className="sidebar">
            <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "35px" }}>
              <div style={{
                background: "linear-gradient(135deg, var(--accent-primary) 0%, var(--accent-secondary) 100%)",
                width: "35px",
                height: "35px",
                borderRadius: "8px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                boxShadow: "0 0 10px rgba(59, 130, 246, 0.4)"
              }}>
                <Award size={20} color="white" />
              </div>
              <h2 style={{ fontSize: "1.25rem", fontWeight: "700" }}>Antigravity Eval</h2>
            </div>

            <nav style={{ display: "flex", flexDirection: "column", gap: "8px", flex: 1 }}>
              <Link
                href="/"
                className={`btn ${pathname === "/" ? "btn-primary" : "btn-secondary"}`}
                style={{ justifyContent: "flex-start", width: "100%" }}
              >
                <BarChart3 size={18} />
                <span>Dashboard Home</span>
              </Link>

              <div style={{ margin: "20px 0 10px 5px", fontSize: "0.75rem", fontWeight: "600", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                Active Benchmarks
              </div>

              {loading ? (
                <div style={{ padding: "10px 5px", fontSize: "0.85rem", color: "var(--text-muted)" }}>Loading projects...</div>
              ) : projects.length === 0 ? (
                <div style={{ padding: "10px 5px", fontSize: "0.85rem", color: "var(--text-muted)" }}>No benchmarks created yet.</div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "50vh", overflowY: "auto" }}>
                  {projects.map((proj) => {
                    const isActive = pathname.startsWith(`/projects/${proj.id}`);
                    return (
                      <Link
                        key={proj.id}
                        href={`/projects/${proj.id}`}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "10px",
                          padding: "10px 12px",
                          borderRadius: "8px",
                          fontSize: "0.9rem",
                          color: isActive ? "var(--text-primary)" : "var(--text-secondary)",
                          background: isActive ? "rgba(59, 130, 246, 0.12)" : "transparent",
                          border: isActive ? "1px solid rgba(59, 130, 246, 0.25)" : "1px solid transparent",
                          transition: "var(--transition-smooth)"
                        }}
                      >
                        <FolderKanban size={16} style={{ color: isActive ? "var(--accent-primary)" : "var(--text-muted)" }} />
                        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{proj.name}</span>
                      </Link>
                    );
                  })}
                </div>
              )}
            </nav>

            <div style={{ borderTop: "1px solid var(--border-color)", paddingTop: "20px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", fontSize: "0.75rem", color: "var(--text-muted)" }}>
                <Activity size={12} color="var(--color-success)" />
                <span>System Connected</span>
              </div>
            </div>
          </aside>

          <main className="main-content">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
