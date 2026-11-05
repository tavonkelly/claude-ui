import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

export function Billing({ plan }: { plan: string }) {
  return (
    <div className="p-[13px]" style={{ padding: 10 }}>
      <Card>
        <CardContent>
          <Card>
            <CardContent>Invoice history</CardContent>
          </Card>
        </CardContent>
      </Card>
      <div className="rounded-lg border p-4">
        <div className="rounded-md border p-4">Usage</div>
      </div>
      <h1 className="bg-gradient-to-r from-purple-500 to-blue-500 bg-clip-text text-transparent">Billing</h1>
      <div className="border-l-4 border-purple-500 rounded-md p-4">Trial</div>
      <Button variant="primary">Upgrade</Button>
      <Button variant="primary">Contact sales</Button>
    </div>
  );
}
