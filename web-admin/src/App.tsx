import { useCallback, useEffect, useState } from "react";
import { NavLink, Route, Routes } from "react-router-dom";
import { Button } from "./components/ui/button";
import { apiFetch } from "./lib/api";
import Alerts from "./pages/Alerts";
import Financials from "./pages/Financials";
import Login from "./pages/Login";
import Overview from "./pages/Overview";
import Sources from "./pages/Sources";
import Topics from "./pages/Topics";

const navItems = [
  { to: "/", label: "Обзор" },
  { to: "/sources", label: "Источники" },
  { to: "/topics", label: "Темы" },
  { to: "/alerts", label: "Алерты" },
  { to: "/financials", label: "Финансы" }
];

type AdminMeResponse = {
  authenticated: boolean;
  username: string;
};

export default function App() {
  const [status, setStatus] = useState<"loading" | "authenticated" | "unauthenticated">(
    "loading"
  );
  const [username, setUsername] = useState("");

  const fetchMe = useCallback(async () => {
    try {
      const data = await apiFetch<AdminMeResponse>("/api/admin/auth/me");
      setUsername(data.username);
      setStatus(data.authenticated ? "authenticated" : "unauthenticated");
    } catch {
      setStatus("unauthenticated");
    }
  }, []);

  useEffect(() => {
    void fetchMe();
  }, [fetchMe]);

  const handleLogout = async () => {
    await apiFetch("/api/admin/auth/logout", { method: "POST" });
    setUsername("");
    setStatus("unauthenticated");
  };

  if (status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-400">
        Проверяем сессию...
      </div>
    );
  }

  if (status === "unauthenticated") {
    return <Login onSuccess={fetchMe} />;
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <div>
            <p className="text-xs uppercase tracking-[0.2em] text-slate-400">INFRA Admin</p>
            <h1 className="text-lg font-semibold">Панель администратора</h1>
            <p className="text-xs text-slate-500">Вы вошли как {username}</p>
          </div>
          <Button onClick={handleLogout}>Выйти</Button>
        </div>
      </header>
      <div className="mx-auto flex max-w-6xl gap-6 px-6 py-6">
        <nav className="w-48 space-y-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-md px-3 py-2 text-sm ${
                  isActive ? "bg-slate-800 text-white" : "text-slate-400 hover:bg-slate-900"
                }`
              }
              end={item.to === "/"}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Overview />} />
            <Route path="/sources" element={<Sources />} />
            <Route path="/topics" element={<Topics />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/financials" element={<Financials />} />
          </Routes>
        </main>
      </div>
    </div>
  );
}
