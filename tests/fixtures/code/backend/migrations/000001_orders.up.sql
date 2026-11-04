-- sales orders and deliveries
CREATE TABLE sales_orders (id uuid PRIMARY KEY, status text NOT NULL, confirmed_at timestamptz);
CREATE TABLE IF NOT EXISTS deliveries (id uuid PRIMARY KEY, order_id uuid REFERENCES sales_orders(id));
