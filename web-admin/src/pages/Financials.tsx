import { FormEvent, useCallback, useEffect, useState } from "react";
import { Button } from "../components/ui/button";
import { Card } from "../components/ui/card";
import { apiFetch } from "../lib/api";

type Subscription = {
  id: number;
  user_id: number;
  plan_tier: string;
  status: string;
  amount_rub: number;
  started_at: string;
  expires_at: string | null;
  created_at: string;
};

type SummaryTier = {
  revenue_rub: number;
  count: number;
};

type Summary = {
  revenue_rub: number;
  payments_count: number;
  new_subscriptions_count: number;
  active_subscriptions_count: number;
  by_tier: Record<string, SummaryTier>;
};

const formatDate = (value: string | null) =>
  value ? new Date(value).toLocaleString("ru-RU") : "—";

const toIsoDate = (value: string, endOfDay = false) => {
  if (!value) return undefined;
  const time = endOfDay ? "23:59:59" : "00:00:00";
  const date = new Date(`${value}T${time}`);
  return date.toISOString();
};

export default function Financials() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [filters, setFilters] = useState({ from: "", to: "" });
  const [loading, setLoading] = useState(false);
  const [assign, setAssign] = useState({
    tg_id: "",
    plan_tier: "pro",
    status: "active",
    amount_rub: "0",
    expires_at: ""
  });
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    const params = new URLSearchParams();
    const fromIso = toIsoDate(filters.from);
    const toIso = toIsoDate(filters.to, true);
    if (fromIso) params.set("from", fromIso);
    if (toIso) params.set("to", toIso);
    const query = params.toString();
    const suffix = query ? `?${query}` : "";
    try {
      const [summaryData, subscriptionData] = await Promise.all([
        apiFetch<Summary>(`/api/admin/financials/summary${suffix}`),
        apiFetch<Subscription[]>(`/api/admin/subscriptions${suffix}`)
      ]);
      setSummary(summaryData);
      setSubscriptions(subscriptionData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Не удалось загрузить финансовые данные. Попробуйте снова."
      );
    } finally {
      setLoading(false);
    }
  }, [filters.from, filters.to]);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleAssign = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    try {
      await apiFetch("/api/admin/subscriptions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          tg_id: Number(assign.tg_id),
          plan_tier: assign.plan_tier,
          status: assign.status,
          amount_rub: Number(assign.amount_rub),
          expires_at: assign.expires_at ? toIsoDate(assign.expires_at, true) : null
        })
      });
      setAssign({ ...assign, tg_id: "", amount_rub: "0", expires_at: "" });
      await loadData();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Не удалось создать подписку. Проверьте введённые данные."
      );
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold">Финансы</h2>
            <p className="text-sm text-slate-400">Подписки, платежи и ручные гранты.</p>
          </div>
          <Button onClick={loadData} disabled={loading}>
            {loading ? "Обновляем..." : "Обновить"}
          </Button>
        </div>
        <div className="mt-4 flex flex-wrap gap-3 text-sm text-slate-300">
          <label className="flex items-center gap-2">
            С
            <input
              type="date"
              className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1"
              value={filters.from}
              onChange={(event) => setFilters({ ...filters, from: event.target.value })}
            />
          </label>
          <label className="flex items-center gap-2">
            По
            <input
              type="date"
              className="rounded-md border border-slate-800 bg-slate-900 px-2 py-1"
              value={filters.to}
              onChange={(event) => setFilters({ ...filters, to: event.target.value })}
            />
          </label>
        </div>
      </Card>

      {summary && (
        <div className="grid gap-4 md:grid-cols-4">
          <Card>
            <p className="text-sm text-slate-400">Выручка</p>
            <p className="text-2xl font-semibold">{summary.revenue_rub} ₽</p>
          </Card>
          <Card>
            <p className="text-sm text-slate-400">Платежи</p>
            <p className="text-2xl font-semibold">{summary.payments_count}</p>
          </Card>
          <Card>
            <p className="text-sm text-slate-400">Новые подписки</p>
            <p className="text-2xl font-semibold">{summary.new_subscriptions_count}</p>
          </Card>
          <Card>
            <p className="text-sm text-slate-400">Активные подписки</p>
            <p className="text-2xl font-semibold">{summary.active_subscriptions_count}</p>
          </Card>
        </div>
      )}

      {summary && (
        <Card>
          <h3 className="text-sm font-semibold text-slate-200">Разбивка по тарифам</h3>
          <div className="mt-3 grid gap-3 md:grid-cols-3">
            {Object.entries(summary.by_tier).map(([tier, data]) => (
              <div key={tier} className="rounded-md border border-slate-800 bg-slate-900 p-3">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">{tier}</p>
                <p className="text-lg font-semibold">{data.revenue_rub} ₽</p>
                <p className="text-xs text-slate-500">{data.count} подписок</p>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Card>
        <h3 className="text-sm font-semibold text-slate-200">Назначить подписку</h3>
        <form className="mt-3 grid gap-3 md:grid-cols-5" onSubmit={handleAssign}>
          <input
            className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
            placeholder="tg_id"
            value={assign.tg_id}
            onChange={(event) => setAssign({ ...assign, tg_id: event.target.value })}
            required
          />
          <select
            className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
            value={assign.plan_tier}
            onChange={(event) => setAssign({ ...assign, plan_tier: event.target.value })}
          >
            <option value="free">free</option>
            <option value="pro">pro</option>
            <option value="corp">corp</option>
          </select>
          <select
            className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
            value={assign.status}
            onChange={(event) => setAssign({ ...assign, status: event.target.value })}
          >
            <option value="active">active</option>
            <option value="trial">trial</option>
            <option value="canceled">canceled</option>
            <option value="expired">expired</option>
          </select>
          <input
            className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Сумма, ₽"
            value={assign.amount_rub}
            onChange={(event) => setAssign({ ...assign, amount_rub: event.target.value })}
          />
          <input
            type="date"
            className="rounded-md border border-slate-800 bg-slate-900 px-3 py-2 text-sm"
            value={assign.expires_at}
            onChange={(event) => setAssign({ ...assign, expires_at: event.target.value })}
          />
          <Button className="md:col-span-5" type="submit">
            Сохранить
          </Button>
        </form>
        {error && <p className="mt-2 text-sm text-rose-400">{error}</p>}
      </Card>

      <Card>
        <h3 className="text-sm font-semibold text-slate-200">Подписки</h3>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="text-xs uppercase text-slate-500">
              <tr>
                <th className="py-2">ID</th>
                <th className="py-2">User</th>
                <th className="py-2">Тариф</th>
                <th className="py-2">Статус</th>
                <th className="py-2">Сумма</th>
                <th className="py-2">Создано</th>
                <th className="py-2">Истекает</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {subscriptions.map((subscription) => (
                <tr key={subscription.id} className="text-slate-200">
                  <td className="py-2">{subscription.id}</td>
                  <td className="py-2">{subscription.user_id}</td>
                  <td className="py-2">{subscription.plan_tier}</td>
                  <td className="py-2">{subscription.status}</td>
                  <td className="py-2">{subscription.amount_rub} ₽</td>
                  <td className="py-2">{formatDate(subscription.created_at)}</td>
                  <td className="py-2">{formatDate(subscription.expires_at)}</td>
                </tr>
              ))}
              {!subscriptions.length && (
                <tr>
                  <td colSpan={7} className="py-4 text-center text-slate-500">
                    Подписок нет.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
