import { Card } from "../components/ui/card";

export default function Profile() {
  return (
    <Card className="space-y-3">
      <div>
        <h2 className="text-lg font-semibold">Профиль</h2>
        <p className="text-sm text-slate-400">Тариф, доставки, quiet hours.</p>
      </div>
      <div className="rounded-md bg-slate-800 p-3 text-sm">
        <p>Тариф: FREE</p>
        <p>Доставка: дайджест каждые 3 часа</p>
        <p>Тихие часы: не настроены</p>
      </div>
    </Card>
  );
}
