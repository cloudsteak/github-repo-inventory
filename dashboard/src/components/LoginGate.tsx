import { FormEvent, useState } from "react";

type LoginGateProps = {
  onLogin: (password: string) => Promise<void>;
};

export function LoginGate({ onLogin }: LoginGateProps) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onLogin(password);
    } catch {
      setError("Invalid password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page">
      <div className="error-panel login-panel">
        <h1>GitHub Repo Inventory</h1>
        <p className="muted">Enter the dashboard password to view inventory data.</p>
        <form className="login-form" onSubmit={handleSubmit}>
          <label htmlFor="dashboard-password">Password</label>
          <input
            id="dashboard-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={submitting}
          />
          <button type="submit" disabled={submitting || !password}>
            {submitting ? "Signing in…" : "Sign in"}
          </button>
        </form>
        {error ? <p className="login-error">{error}</p> : null}
      </div>
    </div>
  );
}
