import { FormEvent, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { apiFetch } from "../lib/api";

type LoginProps = {
  onSuccess: () => void;
};

export default function Login({ onSuccess }: LoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await apiFetch("/api/admin/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password })
      });
      await onSuccess();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Не удалось выполнить вход. Проверьте подключение."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-6 text-slate-100">
      <Card className="w-full max-w-sm space-y-4">
        <div>
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">INFRA Admin</p>
          <h2 className="text-lg font-semibold">Вход в панель</h2>
        </div>
        <form className="space-y-3" onSubmit={handleSubmit}>
          <label className="block text-sm text-slate-400">
            Логин
            <input
              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              required
            />
          </label>
          <label className="block text-sm text-slate-400">
            Пароль
            <input
              className="mt-1 w-full rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
            />
          </label>
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <Button className="w-full" type="submit" disabled={loading}>
            {loading ? "Входим..." : "Войти"}
          </Button>
        </form>
      </Card>
    </div>
  );
}
