package postgres

import "context"

// Store persists sales orders.
type Store struct{ Pool any }

// ConfirmOrder marks an approved order as confirmed to the customer.
// It must run inside one transaction.
func (s Store) ConfirmOrder(ctx context.Context, id string) error {
	_, err := s.exec(ctx, `UPDATE sales_orders SET confirmed_at=now() WHERE id=$1 AND status='APPROVED'`, id)
	return err
}

func (s Store) CreateDelivery(ctx context.Context, orderID string) error {
	// deliveries need a confirmed order
	_, err := s.exec(ctx, "INSERT INTO deliveries(order_id) SELECT id FROM sales_orders WHERE id=$1 AND confirmed_at IS NOT NULL", orderID)
	return err
}

func (s Store) exec(ctx context.Context, sql string, args ...any) (any, error) { return nil, nil }
