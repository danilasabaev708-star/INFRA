import { Card } from "../components/ui/card";

export default function Overview() {
  return (
    <div className="space-y-4">
      <Card>
        <h2 className="text-lg font-semibold">Состояние системы</h2>
        <p className="text-sm text-slate-400">Метрики обновляются раз в минуту.</p>
      </Card>
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <p className="text-sm text-slate-400">Контент</p>
          <p className="text-2xl font-semibold">0 сигналов</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-400">AI</p>
          <p className="text-2xl font-semibold">0 вызовов сегодня</p>
        </Card>
        <Card>
          <p className="text-sm text-slate-400">Alerts</p>
          <p className="text-2xl font-semibold">0 активных</p>
        </Card>
      </div>
    </div>
  );
}
