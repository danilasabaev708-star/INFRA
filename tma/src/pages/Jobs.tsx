import { Card } from "../components/ui/card";

export default function Jobs() {
  return (
    <Card>
      <h2 className="text-lg font-semibold">Jobs</h2>
      <p className="text-sm text-slate-400">Вакансии доступны только на PRO.</p>
      <div className="mt-3 rounded-md bg-slate-800 p-3 text-sm">Найдено 0 вакансий</div>
    </Card>
  );
}
