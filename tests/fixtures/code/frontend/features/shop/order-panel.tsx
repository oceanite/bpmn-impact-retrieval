import { api } from "@/lib/api";

export interface OrderDetail {
  id: string;
  confirmed?: boolean;
}

// Shows one order with its Confirm action.
export function OrderPanel({ id }: { id: string }) {
  const confirm = () => api(`/orders/${id}/confirm`, { method: "POST" });
  return <button onClick={confirm}>Confirm order</button>;
}

export const formatTotal = (value: number) => value.toFixed(2);
