import { Button } from "@/components/ui/button";

export function Billing({ plan, invoices }: { plan: string; invoices: { id: string; date: string; total: string }[] }) {
  return (
    <div className="grid gap-6 p-4">
      <h2 className="text-lg font-semibold">Billing</h2>
      <p className="text-sm">Plan: {plan}</p>
      <table className="w-full text-sm">
        <thead>
          <tr><th>Date</th><th>Total</th></tr>
        </thead>
        <tbody>
          {invoices.map((i) => (
            <tr key={i.id}><td>{i.date}</td><td>{i.total}</td></tr>
          ))}
        </tbody>
      </table>
      <div className="flex gap-2">
        <Button>Change plan</Button>
        <Button variant="outline">Download invoices</Button>
      </div>
    </div>
  );
}
