"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ChevronDown, KeyRound, LockKeyhole, UserRound } from "lucide-react";

const API = "";
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
  const [roleOpen, setRoleOpen] = useState(false);
  const roleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const closeRoleMenu = (event: MouseEvent) => {
      if (!roleRef.current?.contains(event.target as Node)) setRoleOpen(false);
    };
    document.addEventListener("mousedown", closeRoleMenu);
    return () => document.removeEventListener("mousedown", closeRoleMenu);
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch(`${API}/api/auth/${mode}`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password, role, details: { name, department } }),
      });
      const responseText = await response.text();
      let data: Partial<SessionUser> & { detail?: string } = {};
      try {
        data = responseText ? JSON.parse(responseText) : {};
      } catch {
        throw new Error(response.status >= 500
          ? "Backend unavailable. Start the API server on port 8000 and try again."
          : "The server returned an invalid response.");
      }
      if (!response.ok) throw new Error(data.detail || "Authentication failed");
      if (mode === "register") {
        setMode("login"); setPassword(""); setError("Account created. Sign in with your new account.");
      } else {
        localStorage.setItem("offair_session", JSON.stringify(data)); onAuthenticated(data as SessionUser);
      }
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "Authentication failed");
    } finally { setBusy(false); }
  };

  return (
    <main className="auth-shell"><section className="auth-panel">
      <div className="auth-mark"><img src="/favicon.png" alt="OffAir AI" /></div>
      <div className="auth-kicker">OFFAIR AI / PRIVATE WORKSPACE</div>
      <h1>{mode === "login" ? "Sign in to your workspace" : "Create a secure account"}</h1>
      <p className="auth-copy">Secure offline AI for company documents and PDFs.</p>
      <form onSubmit={submit} className="auth-form">
        <label>Username<input className="input" value={username} onChange={(event) => setUsername(event.target.value)} required /></label>
        {mode === "register" && <label>Display name<input className="input" value={name} onChange={(event) => setName(event.target.value)} /></label>}
        {mode === "register" && <label>Department<input className="input" value={department} onChange={(event) => setDepartment(event.target.value)} /></label>}
        <label>Password<input className="input" type="password" minLength={8} value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
        <label>Role
          <div className={`role-select ${roleOpen ? "is-open" : ""}`} ref={roleRef}>
            <button
              type="button"
              className="role-select-trigger"
              aria-haspopup="listbox"
              aria-expanded={roleOpen}
              onClick={() => setRoleOpen((open) => !open)}
            >
              <span>{role}</span><ChevronDown size={18} className="role-select-chevron" />
            </button>
            {roleOpen && (
              <div className="role-select-menu" role="listbox" aria-label="Role">
                {ROLES.map((item) => (
                  <button
                    type="button"
                    role="option"
                    aria-selected={role === item}
                    className={`role-option ${role === item ? "is-selected" : ""}`}
                    key={item}
                    onClick={() => { setRole(item); setRoleOpen(false); }}
                  >
                    <span className="role-option-marker" />{item}
                  </button>
                ))}
              </div>
            )}
          </div>
        </label>
        {error && <div className={error.startsWith("Account created") ? "auth-notice" : "auth-error"}>{error}</div>}
        <button className="btn btn-primary auth-submit" disabled={busy} type="submit">{mode === "login" ? <KeyRound size={15} /> : <UserRound size={15} />}{busy ? "Checking..." : mode === "login" ? "Enter workspace" : "Create account"}</button>
      </form>
      <button className="auth-switch" onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(""); }}>{mode === "login" ? "Need an account? Create one" : "Already registered? Sign in"}</button>
      <div className="auth-foot"><LockKeyhole size={12} /> Access is enforced by your stored role.</div>
    </section></main>
  );
}