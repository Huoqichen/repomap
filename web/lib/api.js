const API_BASE_URL = process.env.NEXT_PUBLIC_REPOMAP_API_URL || "http://localhost:8000";

export async function fetchArchitecture(repoUrl, branch) {
  if (!repoUrl.includes("github.com/")) {
    throw new Error("Please enter a valid GitHub repository URL.");
  }

  const response = await fetch(`${API_BASE_URL}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      repo_url: repoUrl,
      branch: branch || null
    })
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Failed to analyze repository.");
  }

  return payload;
}
