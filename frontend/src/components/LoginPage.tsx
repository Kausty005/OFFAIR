"use client";

import { FormEvent, useState } from "react";
import { KeyRound, LockKeyhole, ShieldCheck, UserRound } from "lucide-react";

const API = "http://localhost:8000";
const ROLES = ["HR", "employee", "finance", "engineer", "admin"];

export interface SessionUser {
  token: string;
  username: string;
  role: string;
  details?: Record<string, string>;
}

export default function LoginPage({ onAuthenticated }: { onAuthenticated: (session: SessionUser) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("employee");
  const [name, setName] = useState("");
  const [department, setDepartment] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch(`${API}/api/auth/${mode}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role, details: { name, department } }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Authentication failed");
      if (mode === "register") {
        setMode("login"); setPassword(""); setError("Account created. Sign in with your new account.");
      } else {
        localStorage.setItem("offair_session", JSON.stringify(data)); onAuthenticated(data);
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Authentication failed");
    } finally { setBusy(false); }
  };

  return (
    <main className="auth-shell"><section className="auth-panel">
      <div className="auth-mark"><ShieldCheck size={22} /></div>
      <div className="auth-kicker">OFFAIR AI / PRIVATE WORKSPACE</div>
      <h1>{mode === "login" ? "Sign in to your workspace" : "Create a secure account"}</h1>
      <p className="auth-copy">Local identity, role-scoped documents, and air-gapped intelligence.</p>
      <form onSubmit={submit} className="auth-form">
        <label>Username<input className="input" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
        {mode === "register" && <label>Display name<input className="input" value={name} onChange={(event) => setName(event.target.value)} /></label>}
        {mode === "register" && <label>Department<input className="input" value={department} onChange={(event) => setDepartment(event.target.value)} /></label>}
        <label>Password<input className="input" type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
        <label>Role<select className="input" value={role} onChange={(event) => setRole(event.target.value)}>{ROLES.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        {error && <div className={error.startsWith("Account created") ? "auth-notice" : "auth-error"}>{error}</div>}
        <button className="btn btn-primary auth-submit" disabled={busy} type="submit">{mode === "login" ? <KeyRound size={15} /> : <UserRound size={15} />}{busy ? "Checking..." : mode === "login" ? "Enter workspace" : "Create account"}</button>
      </form>
      <button className="auth-switch" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Need an account? Create one" : "Already registered? Sign in"}</button>
      <div className="auth-foot"><LockKeyhole size={12} /> Access is enforced by your stored role.</div>
    </section></main>
  );
}