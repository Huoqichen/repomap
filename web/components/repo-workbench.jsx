"use client";

import { startTransition, useEffect, useState } from "react";
import { GraphCanvas } from "./graph-canvas";
import { fetchArchitecture } from "../lib/api";

const layerColors = {
  Frontend: "#93c5fd",
  Backend: "#86efac",
  Database: "#fdba74",
  Infrastructure: "#c4b5fd",
  Shared: "#d1d5db"
};

const defaultUrl = "https://github.com/vercel/next.js";

export function RepoWorkbench() {
  const [repoUrl, setRepoUrl] = useState(defaultUrl);
  const [branch, setBranch] = useState("");
  const [result, setResult] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);
  const [error, setError] = useState("");
  const [isPending, setIsPending] = useState(false);

  useEffect(() => {
    void handleAnalyze(defaultUrl, "");
  }, []);

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
      setError(requestError.message);
    } finally {
      setIsPending(false);
    }
  }

  function onSubmit(event) {
    event.preventDefault();
    void handleAnalyze();
  }

  const architecture = result?.architecture_map;
  const nodes = architecture?.graph?.nodes ?? [];
  const edges = architecture?.graph?.edges ?? [];
  const layers = architecture?.architecture_layers ?? [];
  const modules = architecture?.modules ?? [];

  return (
    <main className="page-shell">
      <section className="hero">
        <article className="hero-card hero-copy">
          <span className="eyebrow">repomap.vercel.app</span>
          <h1>Repository architecture, mapped in seconds.</h1>
          <p>
            Paste any GitHub repository URL and inspect its architecture as an interactive graph.
            The Python backend analyzes the codebase, and the Next.js + D3 frontend turns the
            result into something you can actually explore.
          </p>
        </article>

        <aside className="hero-card mini-grid">
          <div className="mini-card">
            <strong>Backend</strong>
            <p>Python API powered by the existing repository analyzer and graph builder.</p>
          </div>
          <div className="mini-card">
            <strong>Frontend</strong>
            <p>Next.js app with D3.js force layout, zoom, drag, and clickable source nodes.</p>
          </div>
          <div className="mini-card">
            <strong>Layers</strong>
            <p>Highlights Frontend, Backend, Database, Infrastructure, and Shared modules.</p>
          </div>
          <div className="mini-card">
            <strong>Exports</strong>
            <p>Returns folder tree, JSON graph model, Mermaid diagram, and language detection.</p>
          </div>
        </aside>
      </section>

      <section className="panel input-panel">
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="repo-url">GitHub repository URL</label>
              <input
                id="repo-url"
                type="url"
                placeholder="https://github.com/user/repo"
                value={repoUrl}
                onChange={(event) => setRepoUrl(event.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="branch">Branch (optional)</label>
              <input
                id="branch"
                type="text"
                placeholder="main"
                value={branch}
                onChange={(event) => setBranch(event.target.value)}
              />
            </div>
            <button className="submit-button" type="submit" disabled={isPending}>
              {isPending ? "Analyzing..." : "Analyze repo"}
            </button>
          </div>
        </form>

        <div className="input-footer">
          <span>Example: {defaultUrl}</span>
          {error ? <span className="status-error">{error}</span> : <span>Interactive graph + JSON + Mermaid</span>}
        </div>
      </section>

      {architecture ? (
        <section className="results-grid">
          <article className="panel graph-panel">
            <header className="graph-header">
              <div className="graph-title-row">
                <div>
                  <h2>Interactive architecture graph</h2>
                  <p className="graph-note">
                    Drag nodes, zoom the canvas, and click a node to open the source file when a
                    GitHub link is available.
                  </p>
                </div>
                <div className="legend">
                  {Object.entries(layerColors).map(([layer, color]) => (
                    <span key={layer}>
                      <i style={{ background: color }} />
                      {layer}
                    </span>
                  ))}
                </div>
              </div>

              <div className="stat-row">
                <span className="stat-pill">Primary: {architecture.primary_language ?? "Unknown"}</span>
                <span className="stat-pill">Nodes: {result.stats.nodes}</span>
                <span className="stat-pill">Edges: {result.stats.edges}</span>
                <span className="stat-pill">
                  Languages: {(architecture.detected_languages ?? []).map((item) => item.name).join(", ") || "None"}
                </span>
              </div>
            </header>

            <GraphCanvas nodes={nodes} edges={edges} onSelect={setSelectedNode} selectedNodeId={selectedNode?.id} />

            <footer className="graph-toolbar">
              <span>Repository: {architecture.repository_url}</span>
              <span>Branch: {architecture.default_branch ?? "auto-detected"}</span>
            </footer>
          </article>

          <aside className="sidebar">
            <section className="panel side-section">
              <h3>Architecture layers</h3>
              <p>Top-level structure inferred from paths and dependency patterns.</p>
              <div className="layers-grid">
                {layers.map((layer) => (
                  <span className="layer-pill" key={layer.name}>
                    {layer.name} · {layer.module_count}
                  </span>
                ))}
              </div>
            </section>

            <section className="panel side-section">
              <h3>Selected module</h3>
              {selectedNode ? (
                <>
                  <div className="module-card" data-active="true">
                    <h4>{selectedNode.label}</h4>
                    <div className="module-meta">
                      <span>{selectedNode.language}</span>
                      <span>{selectedNode.layer}</span>
                      <span>{selectedNode.path}</span>
                    </div>
                    {selectedNode.url ? (
                      <a href={selectedNode.url} target="_blank" rel="noreferrer">
                        Open source file
                      </a>
                    ) : null}
                  </div>
                  <div className="module-list">
                    {modules
                      .filter((module) => module.id === selectedNode.id)
                      .map((module) => (
                        <div className="module-card" key={module.id}>
                          <h4>Dependencies</h4>
                          <div className="module-meta">
                            <span>Internal: {module.internal_dependencies.length}</span>
                            <span>External: {module.external_dependencies.length}</span>
                          </div>
                          <p>
                            {module.external_dependencies.slice(0, 8).join(", ") || "No external dependencies detected."}
                          </p>
                        </div>
                      ))}
                  </div>
                </>
              ) : (
                <p>Select a node in the graph to inspect it here.</p>
              )}
            </section>

            <section className="panel side-section">
              <h3>Module list</h3>
              <p>Useful when the graph is dense and you want to jump to a module directly.</p>
              <div className="module-list">
                {nodes.slice(0, 14).map((node) => (
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
              <h3>Folder tree</h3>
              <div className="tree-list">
                <TreeNode node={architecture.folder_tree} />
              </div>
            </section>

            <section className="panel side-section">
              <h3>Mermaid output</h3>
              <p>Copy this into GitHub, docs, or Markdown viewers that support Mermaid.</p>
              <pre className="code-block">{result.mermaid}</pre>
            </section>
          </aside>
        </section>
      ) : (
        <section className="panel empty-state">
          <div>
            <h2>No architecture map yet</h2>
            <p>Submit a GitHub repository URL to generate the graph.</p>
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
