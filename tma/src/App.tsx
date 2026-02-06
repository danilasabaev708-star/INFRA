import { NavLink, Route, Routes } from "react-router-dom";
import { Card } from "./components/ui/card";
import Favorites from "./pages/Favorites";
import Jobs from "./pages/Jobs";
import Notifications from "./pages/Notifications";
import Profile from "./pages/Profile";
import Studio from "./pages/Studio";
import Topics from "./pages/Topics";

const navItems = [
  { to: "/topics", label: "Темы" },
  { to: "/notifications", label: "Уведомления" },
  { to: "/jobs", label: "Jobs" },
  { to: "/favorites", label: "Избранное" },
  { to: "/profile", label: "Профиль" }
];

export default function App() {
  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <header className="border-b border-slate-800 px-4 py-4">
        <h1 className="text-lg font-semibold">INFRA</h1>
        <p className="text-xs text-slate-400">Клиент для Telegram Mini App</p>
      </header>
      <main className="flex-1 px-4 py-4">
        <Routes>
          <Route path="/" element={<Topics />} />
          <Route path="/topics" element={<Topics />} />
          <Route path="/notifications" element={<Notifications />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/favorites" element={<Favorites />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/studio" element={<Studio />} />
        </Routes>
      </main>
      <nav className="border-t border-slate-800 px-2 py-2">
        <div className="grid grid-cols-5 gap-2 text-center text-xs">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-md px-1 py-2 ${isActive ? "bg-slate-800" : "text-slate-400"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
