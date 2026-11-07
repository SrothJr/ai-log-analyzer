import { useEffect, useState } from "react";
import { getFindings, getJob, startJob, uploadLog } from "./api";

const severityOrder = ["Critical", "High", "Medium", "Low"];

function FindingCard({ finding }) {
  return (
    <article className={`finding ${finding.severity.toLowerCase()}`}>
      <header>
        <strong>{finding.attack_type.replaceAll("_", " ")}</strong>
        <span className="severity">{finding.severity}</span>
      </header>
      <p><b>Actor:</b> {finding.actor_id}</p>
      <p>{finding.reason}</p>
      <p><b>Suggested action:</b> {finding.suggested_action}</p>
      <details>
        <summary>Evidence ({finding.evidence.length})</summary>
        <ul>{finding.evidence.map((item) => <li key={`${item.line}-${item.summary}`}><b>Line {item.line}:</b> {item.summary}</li>)}</ul>
      </details>
    </article>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [job, setJob] = useState(null);
  const [findings, setFindings] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!job || !["queued", "running"].includes(job.status)) return undefined;
    const timer = setTimeout(async () => {
      try {
        const current = await getJob(job.id);
        setJob(current);
        if (current.status === "completed" || current.status === "failed") {
          setFindings(await getFindings(job.id));
          setBusy(false);
        }
      } catch (requestError) {
        setError(requestError.message);
        setBusy(false);
      }
    }, 1500);
    return () => clearTimeout(timer);
  }, [job]);

  async function handleSubmit(event) {
    event.preventDefault();
    if (!file) return;
    setBusy(true);
    setError("");
    setFindings([]);
    try {
      const created = await uploadLog(file);
      setJob(await startJob(created.id));
    } catch (requestError) {
      setError(requestError.message);
      setBusy(false);
    }
  }

  const grouped = severityOrder.map((severity) => ({ severity, items: findings.filter((item) => item.severity === severity) })).filter((group) => group.items.length);

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">Offline defensive analysis</p>
        <h1>Security Log Analyzer</h1>
        <p>Upload a log file and analyze it with the local Qwen model through llama.cpp.</p>
      </section>
      <section className="panel">
        <form onSubmit={handleSubmit}>
          <label htmlFor="log-file">Log file (.log or .txt)</label>
          <input id="log-file" type="file" accept=".log,.txt,text/plain" onChange={(event) => setFile(event.target.files?.[0] || null)} />
          <button type="submit" disabled={!file || busy}>{busy ? "Analyzing…" : "Start analysis"}</button>
        </form>
        {error && <p className="error">{error}</p>}
      </section>
      {job && <section className="panel status-panel">
        <div className="status-line"><b>{job.filename}</b><span className={`status ${job.status}`}>{job.status}</span></div>
        <p>{job.completed_chunks} of {job.total_chunks || "?"} chunks processed{job.total_lines ? ` · ${job.total_lines} lines` : ""}</p>
        {job.error_message && <p className="error">{job.error_message}</p>}
      </section>}
      {findings.length > 0 && <section className="results">
        <div className="results-heading"><h2>Final report</h2><span>{findings.length} finding{findings.length === 1 ? "" : "s"}</span></div>
        {grouped.map((group) => <div key={group.severity}><h3>{group.severity}</h3>{group.items.map((finding, index) => <FindingCard key={`${finding.actor_id}-${finding.attack_type}-${index}`} finding={finding} />)}</div>)}
      </section>}
      {job?.status === "completed" && findings.length === 0 && <section className="panel success">Analysis completed with no evidence-backed findings.</section>}
    </main>
  );
}
