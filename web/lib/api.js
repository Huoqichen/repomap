export async function fetchArchitecture(repoUrl, branch) {
  if (!repoUrl.includes("github.com/")) {
    throw new Error("Please enter a valid GitHub repository URL. / 请输入有效的 GitHub 仓库地址。");
  }

  const response = await fetch("/api/analyze", {
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
    throw new Error(payload.detail || "Failed to analyze repository. / 仓库分析失败。");
  }

  return payload;
}

export async function fetchBranches(repoUrl) {
  if (!repoUrl.includes("github.com/")) {
    return { default_branch: null, branches: [] };
  }

  const params = new URLSearchParams({ repo_url: repoUrl });
  const response = await fetch(`/api/branches?${params.toString()}`, {
    cache: "no-store"
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.detail || "Failed to load branches. / 分支加载失败。");
  }

  return payload;
}
