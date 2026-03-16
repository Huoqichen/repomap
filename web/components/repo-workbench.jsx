"use client";

import { startTransition, useEffect, useMemo, useState } from "react";
import { GraphCanvas } from "./graph-canvas";
import { fetchArchitecture } from "../lib/api";

const defaultUrl = "https://github.com/vercel/next.js";

const copy = {
  zh: {
    brand: "repomap.vercel.app",
    title: "仓库架构，一眼看清。",
    subtitle: "输入 GitHub 仓库地址，立即生成可交互的架构图。",
    repoLabel: "GitHub 仓库地址",
    branchLabel: "分支（可选）",
    repoPlaceholder: "https://github.com/user/repo",
    branchPlaceholder: "main",
    submit: "开始分析",
    loading: "分析中",
    example: "示例",
    emptyTitle: "等待分析",
    emptyBody: "输入仓库地址后即可查看架构图。",
    graphTitle: "架构图",
    graphHint: "拖动、缩放、点击节点查看源码。",
    graphRepo: "仓库",
    graphBranch: "分支",
    autoBranch: "自动识别",
    summaryTitle: "概览",
    primary: "主语言",
    nodes: "节点",
    edges: "连线",
    layers: "架构层",
    detailsTitle: "选中模块",
    detailsEmpty: "点击图中的节点查看详细信息。",
    openSource: "打开源码",
    internal: "内部依赖",
    external: "外部依赖",
    none: "无",
    listTitle: "模块",
    mermaidTitle: "Mermaid",
    treeTitle: "目录树",
    languageZh: "中文",
    languageEn: "EN",
    invalidRepo: "请输入有效的 GitHub 仓库地址。",
    backendUnreachable: "后端 API 无法访问，请先启动 Python API。",
    analyzeFailed: "仓库分析失败。"
  },
  en: {
    brand: "repomap.vercel.app",
    title: "Repository architecture, at a glance.",
    subtitle: "Paste a GitHub repository URL and generate an interactive architecture graph.",
    repoLabel: "GitHub repository URL",
    branchLabel: "Branch (optional)",
    repoPlaceholder: "https://github.com/user/repo",
    branchPlaceholder: "main",
    submit: "Analyze",
    loading: "Analyzing",
    example: "Example",
    emptyTitle: "Ready to analyze",
    emptyBody: "Enter a repository URL to see the architecture graph.",
    graphTitle: "Architecture graph",
    graphHint: "Drag, zoom, and click nodes to open source files.",
    graphRepo: "Repository",
    graphBranch: "Branch",
    autoBranch: "Auto-detected",
    summaryTitle: "Overview",
    primary: "Primary language",
    nodes: "Nodes",
    edges: "Edges",
    layers: "Layers",
    detailsTitle: "Selected module",
    detailsEmpty: "Select a node in the graph to inspect it.",
    openSource: "Open source",
    internal: "Internal deps",
    external: "External deps",
    none: "None",
    listTitle: "Modules",
    mermaidTitle: "Mermaid",
    treeTitle: "Tree",
    languageZh: "中文",
    languageEn: "EN",
    invalidRepo: "Please enter a valid GitHub repository URL.",
    backendUnreachable: "Backend API is unreachable. Start the Python API first.",
    analyzeFailed: "Repository analysis failed."
  }
};

export function RepoWorkbench() {
  const [locale, setLocale] = useState("zh");
  const [repoUrl, setRepoUrl] = useState(defaultUrl);
  const [branch, setBranch] = useState("");
  const [result, setResult] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [error, setError] = useState("");
  const [isPending, setIsPending] = useState(false);

  const t = copy[locale];

  useEffect(() => {
    void handleAnalyze(defaultUrl, "");
  }, []);

  const architecture = result?.architecture_map;
  const nodes = architecture?.graph?.nodes ?? [];
  const edges = architecture?.graph?.edges ?? [];
  const layers = architecture?.architecture_layers ?? [];
  const modules = architecture?.modules ?? [];

  const selectedModule = useMemo(
    () => modules.find((module) => module.id === selectedNode?.id) ?? null,
    [modules, selectedNode]
  );

  async function handleAnalyze(nextRepoUrl = repoUrl, nextBranch = branch) {
    setIsPending(true);
    setError("");

    try {
      const response = await fetchArchitecture(nextRepoUrl, nextBranch || undefined);
      startTransition(() => {
        setResult(response);
        setSelectedNode(response.architecture_map.graph.nodes[0] ?? null);
      });
    } catch (requestError) {
      setError(localizeError(requestError, locale));
    } finally {
      setIsPending(false);
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    void handleAnalyze();
  }

  return (
    <main className="page-shell">
      <header className="topbar">
        <span className="brand-chip">{t.brand}</span>
        <div className="lang-switch" role="tablist" aria-label="Language switch">
          <button
            type="button"
            className={locale === "zh" ? "lang-button is-active" : "lang-button"}
            onClick={() => setLocale("zh")}
          >
            {copy.zh.languageZh}
          </button>
          <button
            type="button"
            className={locale === "en" ? "lang-button is-active" : "lang-button"}
            onClick={() => setLocale("en")}
          >
            {copy.en.languageEn}
          </button>
        </div>
      </header>

      <section className="hero-panel">
        <h1>{t.title}</h1>
        <p>{t.subtitle}</p>
      </section>

      <section className="panel input-panel">
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="field field-wide">
              <label htmlFor="repo-url">{t.repoLabel}</label>
              <input
                id="repo-url"
                type="url"
                placeholder={t.repoPlaceholder}
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                required
              />
            </div>
            <div className="field field-branch">
              <label htmlFor="branch">{t.branchLabel}</label>
              <input
                id="branch"
                type="text"
                placeholder={t.branchPlaceholder}
                value={branch}
                onChange={(event) => setBranch(event.target.value)}
              />
            </div>
            <button className="submit-button" type="submit" disabled={isPending}>
              {isPending ? t.loading : t.submit}
            </button>
          </div>
        </form>

        <div className="input-footer">
          <span>
            {t.example}: {defaultUrl}
          </span>
          {error ? <span className="status-error">{error}</span> : null}
        </div>
      </section>

      {architecture ? (
        <section className="results-grid">
          <article className="panel graph-panel">
            <header className="graph-header">
              <div className="graph-title-row">
                <div>
                  <h2>{t.graphTitle}</h2>
                  <p className="graph-note">{t.graphHint}</p>
                </div>
                <div className="stat-row">
                  <span className="stat-pill">
                    {t.primary}: {architecture.primary_language ?? t.none}
                  </span>
                  <span className="stat-pill">
                    {t.nodes}: {result.stats.nodes}
                  </span>
                  <span className="stat-pill">
                    {t.edges}: {result.stats.edges}
                  </span>
                </div>
              </div>
            </header>

            <GraphCanvas nodes={nodes} edges={edges} onSelect={setSelectedNode} selectedNodeId={selectedNode?.id} />

            <footer className="graph-toolbar">
              <span>
                {t.graphRepo}: {architecture.repository_url}
              </span>
              <span>
                {t.graphBranch}: {architecture.default_branch ?? t.autoBranch}
              </span>
            </footer>
          </article>

          <aside className="sidebar">
            <section className="panel side-section">
              <h3>{t.summaryTitle}</h3>
              <div className="summary-grid">
                <div className="summary-card">
                  <span>{t.layers}</span>
                  <strong>{layers.length}</strong>
                </div>
                <div className="summary-card">
                  <span>{t.nodes}</span>
                  <strong>{result.stats.nodes}</strong>
                </div>
                <div className="summary-card">
                  <span>{t.edges}</span>
                  <strong>{result.stats.edges}</strong>
                </div>
              </div>
              <div className="layers-grid">
                {layers.map((layer) => (
                  <span className="layer-pill" key={layer.name}>
                    {layer.name} · {layer.module_count}
                  </span>
                ))}
              </div>
            </section>

            <section className="panel side-section">
              <h3>{t.detailsTitle}</h3>
              {selectedNode && selectedModule ? (
                <div className="module-card" data-active="true">
                  <h4>{selectedNode.label}</h4>
                  <div className="module-meta">
                    <span>{selectedNode.language}</span>
                    <span>{selectedNode.layer}</span>
                  </div>
                  <div className="detail-pairs">
                    <span>
                      {t.internal}: {selectedModule.internal_dependencies.length}
                    </span>
                    <span>
                      {t.external}: {selectedModule.external_dependencies.length}
                    </span>
                  </div>
                  {selectedNode.url ? (
                    <a href={selectedNode.url} target="_blank" rel="noreferrer">
                      {t.openSource}
                    </a>
                  ) : null}
                </div>
              ) : (
                <p>{t.detailsEmpty}</p>
              )}
            </section>

            <section className="panel side-section">
              <h3>{t.listTitle}</h3>
              <div className="module-list">
                {nodes.slice(0, 12).map((node) => (
                  <div className="module-card" data-active={selectedNode?.id === node.id} key={node.id}>
                    <button type="button" onClick={() => setSelectedNode(node)}>
                      <h4>{node.label}</h4>
                      <div className="module-meta">
                        <span>{node.language}</span>
                        <span>{node.layer}</span>
                      </div>
                    </button>
                  </div>
                ))}
              </div>
            </section>

            <section className="panel side-section">
              <h3>{t.treeTitle}</h3>
              <div className="tree-list">
                <TreeNode node={architecture.folder_tree} />
              </div>
            </section>

            <section className="panel side-section">
              <h3>{t.mermaidTitle}</h3>
              <pre className="code-block">{result.mermaid}</pre>
            </section>
          </aside>
        </section>
      ) : (
        <section className="panel empty-state">
          <div>
            <h2>{t.emptyTitle}</h2>
            <p>{t.emptyBody}</p>
          </div>
        </section>
      )}
    </main>
  );
}

function TreeNode({ node }) {
  if (!node) {
    return null;
  }

  const children = node.children ?? [];
  return (
    <div className="tree-node">
      <strong>{node.name}</strong>
      {children.length ? (
        <ul>
          {children.slice(0, 24).map((child) => (
            <li key={`${node.name}-${child.name}`}>
              {child.type === "directory" ? <TreeNode node={child} /> : <span>{child.name}</span>}
            </li>
          ))}
          {children.length > 24 ? <li>… {children.length - 24} more</li> : null}
        </ul>
      ) : null}
    </div>
  );
}

function localizeError(error, locale) {
  const message = error instanceof Error ? error.message : "";
  if (message.includes("valid GitHub")) {
    return copy[locale].invalidRepo;
  }
  if (message.includes("Backend API is unreachable") || message.includes("后端 API 无法访问")) {
    return copy[locale].backendUnreachable;
  }
  return message || copy[locale].analyzeFailed;
}
