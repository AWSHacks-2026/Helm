import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login, register } from "../api/client";

export default function LoginPage() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"login" | "register">("login");
  const [error, setError] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      if (mode === "register") await register(email, password, name || "Seller");
      await login(email, password);
      nav("/");
    } catch {
      setError(mode === "login" ? "Login failed" : "Register failed");
    }
  }

  return (
    <form className="form" onSubmit={submit}>
      <h1>{mode === "login" ? "Log in" : "Create account"}</h1>
      {mode === "register" && (
        <input placeholder="Display name" value={name} onChange={(e) => setName(e.target.value)} />
      )}
      <input type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} required />
      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit">{mode === "login" ? "Log in" : "Register"}</button>
      <button type="button" onClick={() => setMode(mode === "login" ? "register" : "login")}>
        {mode === "login" ? "Need an account?" : "Have an account?"}
      </button>
      {error && <p>{error}</p>}
    </form>
  );
}
