const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  description: string | null;
  benchmark_type: string;
  created_at: string;
}

export interface ModelConfiguration {
  id: string;
  model_name: string;
  temperature: number;
  system_prompt: string | null;
  parameters: any;
  created_at: string;
}

export interface EvaluationRun {
  id: string;
  project_id: string;
  model_config: ModelConfiguration;
  status: string;
  summary_stats: {
    avg_latency?: number;
    total_cost?: number;
    total_prompt_tokens?: number;
    total_completion_tokens?: number;
    avg_scores?: Record<string, number>;
    success_rate?: number;
  } | null;
  error_message: string | null;
  created_at: string;
}

export interface TestCase {
  id: string;
  project_id: string;
  input_query: string;
  expected_output: string | null;
  context_references: string[] | null;
  test_metadata: any;
  created_at: string;
}

export interface EvaluationResult {
  id: string;
  run_id: string;
  test_case_id: string;
  generated_output: string | null;
  latency_seconds: number | null;
  token_usage: {
    prompt_tokens?: number;
    completion_tokens?: number;
    total_cost?: number;
  } | null;
  metric_scores: Record<string, number> | null;
  error_message: string | null;
  created_at: string;
  test_case?: TestCase;
}

export interface RegressionAlert {
  metric_name: string;
  previous_score: number;
  current_score: number;
  drop_percentage: number;
  test_case_id: string;
  input_query: string;
}

export interface DriftStats {
  run_id: string;
  created_at: string;
  model_name: string;
  avg_latency: number;
  avg_cost: number;
  avg_scores: Record<string, number>;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {}),
    },
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`API error: ${response.status} ${response.statusText} - ${errorText}`);
  }

  if (response.status === 244) {
    return {} as T;
  }

  return response.json();
}

export const api = {
  // Projects
  getProjects: () => request<Project[]>("/projects"),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  createProject: (name: string, description: string, benchmark_type: string) =>
    request<Project>("/projects", {
      method: "POST",
      body: JSON.stringify({ name, description, benchmark_type }),
    }),
  deleteProject: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),

  // Test Cases
  getTestCases: (projectId: string) =>
    request<TestCase[]>(`/projects/${projectId}/testcases`),
  batchCreateTestCases: (projectId: string, cases: Partial<TestCase>[]) =>
    request<TestCase[]>(`/projects/${projectId}/testcases/batch`, {
      method: "POST",
      body: JSON.stringify(cases),
    }),

  // Runs
  getProjectRuns: (projectId: string) =>
    request<EvaluationRun[]>(`/projects/${projectId}/runs`),
  triggerRun: (
    projectId: string,
    modelName: string,
    temperature: number,
    systemPrompt: string,
    parameters: any = {}
  ) =>
    request<EvaluationRun>(`/projects/${projectId}/runs`, {
      method: "POST",
      body: JSON.stringify({
        model_config: {
          model_name: modelName,
          temperature,
          system_prompt: systemPrompt || null,
          parameters,
        },
      }),
    }),
  getRun: (runId: string) => request<EvaluationRun>(`/runs/${runId}`),
  getRunResults: (runId: string) =>
    request<EvaluationResult[]>(`/runs/${runId}/results`),

  // Analytics
  getDrift: (projectId: string) =>
    request<DriftStats[]>(`/projects/${projectId}/drift`),
  getRegressions: (projectId: string, runId: string, compareRunId?: string) => {
    let query = `?run_id=${runId}`;
    if (compareRunId) {
      query += `&compare_run_id=${compareRunId}`;
    }
    return request<RegressionAlert[]>(`/projects/${projectId}/regressions${query}`);
  },
};
