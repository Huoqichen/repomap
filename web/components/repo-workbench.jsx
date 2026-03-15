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
          <h1>
            Repository architecture,
            <br />
            mapped in seconds.
          </h1>
          <BiCopy
            en="Paste any GitHub repository URL and inspect its architecture as an interactive graph. The Python backend analyzes the codebase, and the Next.js + D3 frontend turns the result into something you can actually explore."
            zh="输入任意 GitHub 仓库地址，即可用交互式图谱查看其架构。Python 后端负责分析代码仓库，Next.js + D3 前端负责把结果可视化。"
          />
        </article>

        <aside className="hero-card mini-grid">
          <div className="mini-card">
            <BiHeading en="Backend" zh="后端" />
            <BiCopy
              en="Python API powered by the existing repository analyzer and graph builder."
              zh="使用 Python API，直接复用现有仓库分析器和依赖图构建能力。"
            />
          </div>
          <div className="mini-card">
            <BiHeading en="Frontend" zh="前端" />
            <BiCopy
              en="Next.js app with D3.js force layout, zoom, drag, and clickable source nodes."
              zh="基于 Next.js 和 D3.js，支持力导图、缩放、拖拽和源码节点点击。"
            />
          </div>
          <div className="mini-card">
            <BiHeading en="Layers" zh="架构层" />
            <BiCopy
              en="Highlights Frontend, Backend, Database, Infrastructure, and Shared modules."
              zh="自动识别 Frontend、Backend、Database、Infrastructure 和 Shared 等架构层。"
            />
          </div>
          <div className="mini-card">
            <BiHeading en="Exports" zh="导出结果" />
            <BiCopy
              en="Returns folder tree, JSON graph model, Mermaid diagram, and language detection."
              zh="输出目录树、JSON 图模型、Mermaid 图以及语言识别结果。"
            />
          </div>
        </aside>
      </section>

      <section className="panel input-panel">
        <form onSubmit={onSubmit}>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="repo-url">
                <BiInline en="GitHub repository URL" zh="GitHub 仓库地址" />
              </label>
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
              <label htmlFor="branch">
                <BiInline en="Branch (optional)" zh="分支（可选）" />
              </label>
              <input
                id="branch"
                type="text"
                placeholder="main"
                value={branch}
                onChange={(event) => setBranch(event.target.value)}
              />
            </div>
            <button className="submit-button" type="submit" disabled={isPending}>
              {isPending ? "Analyzing... / 分析中..." : "Analyze repo / 开始分析"}
            </button>
          </div>
        </form>

        <div className="input-footer">
          <span>Example / 示例: {defaultUrl}</span>
          {error ? (
            <span className="status-error">{error}</span>
          ) : (
            <span>Interactive graph + JSON + Mermaid / 交互图 + JSON + Mermaid</span>
          )}
        </div>
      </section>

      {architecture ? (
        <section className="results-grid">
          <article className="panel graph-panel">
            <header className="graph-header">
              <div className="graph-title-row">
                <div>
                  <h2>Interactive architecture graph</h2>
                  <p className="copy-zh">交互式架构图</p>
                  <BiCopy
                    className="graph-note"
                    en="Drag nodes, zoom the canvas, and click a node to open the source file when a GitHub link is available."
                    zh="你可以拖动节点、缩放画布，并在存在 GitHub 链接时点击节点打开源码文件。"
                  />
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
                <span className="stat-pill">Primary / 主语言: {architecture.primary_language ?? "Unknown"}</span>
                <span className="stat-pill">Nodes / 节点: {result.stats.nodes}</span>
                <span className="stat-pill">Edges / 连线: {result.stats.edges}</span>
                <span className="stat-pill">
                  Languages / 语言: {(architecture.detected_languages ?? []).map((item) => item.name).join(", ") || "None"}
                </span>
              </div>
            </header>

            <GraphCanvas nodes={nodes} edges={edges} onSelect={setSelectedNode} selectedNodeId={selectedNode?.id} />

            <footer className="graph-toolbar">
              <span>Repository / 仓库: {architecture.repository_url}</span>
              <span>Branch / 分支: {architecture.default_branch ?? "auto-detected / 自动识别"}</span>
            </footer>
          </article>

          <aside className="sidebar">
            <section className="panel side-section">
              <h3>Architecture layers</h3>
              <p className="copy-zh">架构层</p>
              <BiCopy
                en="Top-level structure inferred from paths and dependency patterns."
                zh="根据目录路径和依赖模式推断出的顶层架构结构。"
              />
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
              <p className="copy-zh">当前选中的模块</p>
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
                        Open source file / 打开源码文件
                      </a>
                    ) : null}
                  </div>
                  <div className="module-list">
                    {modules
                      .filter((module) => module.id === selectedNode.id)
                      .map((module) => (
                        <div className="module-card" key={module.id}>
                          <h4>Dependencies / 依赖</h4>
                          <div className="module-meta">
                            <span>Internal / 内部: {module.internal_dependencies.length}</span>
                            <span>External / 外部: {module.external_dependencies.length}</span>
                          </div>
                          <p>
                            {module.external_dependencies.slice(0, 8).join(", ") || "No external dependencies detected. / 未检测到外部依赖。"}
                          </p>
                        </div>
                      ))}
                  </div>
                </>
              ) : (
                <BiCopy en="Select a node in the graph to inspect it here." zh="在图中选择一个节点，即可在这里查看详情。" />
              )}
            </section>

            <section className="panel side-section">
              <h3>Module list</h3>
              <p className="copy-zh">模块列表</p>
              <BiCopy
                en="Useful when the graph is dense and you want to jump to a module directly."
                zh="当图较密集时，可以从这里直接跳转到目标模块。"
              />
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
              <p className="copy-zh">目录树</p>
              <div className="tree-list">
                <TreeNode node={architecture.folder_tree} />
              </div>
            </section>

            <section className="panel side-section">
              <h3>Mermaid output</h3>
              <p className="copy-zh">Mermaid 输出</p>
              <BiCopy
                en="Copy this into GitHub, docs, or Markdown viewers that support Mermaid."
                zh="可以直接复制到 GitHub、文档系统或支持 Mermaid 的 Markdown 查看器中。"
              />
              <pre className="code-block">{result.mermaid}</pre>
            </section>
          </aside>
        </section>
      ) : (
        <section className="panel empty-state">
          <div>
            <h2>No architecture map yet</h2>
            <p className="copy-zh">还没有生成架构图</p>
            <BiCopy
              en="Submit a GitHub repository URL to generate the graph."
              zh="提交一个 GitHub 仓库地址，即可生成架构图。"
            />
          </div>
        </section>
      )}
    </main>
  );
}

function BiHeading({ en, zh }) {
  return (
    <strong className="copy-stack">
      <span className="copy-en">{en}</span>
      <span className="copy-zh">{zh}</span>
    </strong>
  );
}

function BiCopy({ en, zh, className = "" }) {
  return (
    <p className={`copy-stack ${className}`.trim()}>
      <span className="copy-en">{en}</span>
      <span className="copy-zh">{zh}</span>
    </p>
  );
}

function BiInline({ en, zh }) {
  return (
    <>
      {en}
      <span className="inline-zh"> / {zh}</span>
    </>
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
