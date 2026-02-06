import { Card } from "../components/ui/card";

export default function Favorites() {
  return (
    <Card>
      <h2 className="text-lg font-semibold">Избранное</h2>
      <p className="text-sm text-slate-400">Сохранённые новости и сигналы.</p>
    </Card>
  );
}
