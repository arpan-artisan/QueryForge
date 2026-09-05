DO $$
DECLARE
    public_table record;
BEGIN
    FOR public_table IN
        SELECT tablename
        FROM pg_tables
        WHERE schemaname = 'public'
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS public.%I CASCADE', public_table.tablename);
    END LOOP;
END
$$;

CREATE TABLE customers (
    id integer PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    created_at date NOT NULL,
    region text NOT NULL CHECK (region IN ('North', 'South', 'East', 'West')),
    segment text NOT NULL CHECK (segment IN ('Consumer', 'Business'))
);

CREATE TABLE categories (
    id integer PRIMARY KEY,
    name text NOT NULL UNIQUE,
    description text NOT NULL
);

CREATE TABLE products (
    id integer PRIMARY KEY,
    category_id integer NOT NULL REFERENCES categories(id),
    name text NOT NULL UNIQUE,
    sku text NOT NULL UNIQUE,
    unit_price numeric(12, 2) NOT NULL CHECK (unit_price >= 0),
    active boolean NOT NULL DEFAULT true
);

CREATE TABLE orders (
    id integer PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(id),
    order_date date NOT NULL,
    status text NOT NULL CHECK (status IN ('completed', 'refunded', 'pending', 'cancelled')),
    channel text NOT NULL CHECK (channel IN ('web', 'retail', 'partner'))
);

CREATE TABLE order_items (
    id integer PRIMARY KEY,
    order_id integer NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id integer NOT NULL REFERENCES products(id),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(12, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE payments (
    id integer PRIMARY KEY,
    order_id integer NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_date date NOT NULL,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    method text NOT NULL CHECK (method IN ('card', 'upi', 'wallet')),
    status text NOT NULL CHECK (status IN ('succeeded', 'failed', 'pending'))
);

CREATE TABLE refunds (
    id integer PRIMARY KEY,
    order_id integer NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    refund_date date NOT NULL,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    reason text NOT NULL
);

CREATE INDEX idx_products_category_id ON products(category_id);
CREATE INDEX idx_orders_customer_id ON orders(customer_id);
CREATE INDEX idx_orders_order_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_order_items_order_id ON order_items(order_id);
CREATE INDEX idx_order_items_product_id ON order_items(product_id);
CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_status ON payments(status);
CREATE INDEX idx_refunds_order_id ON refunds(order_id);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'queryforge_readonly') THEN
        CREATE ROLE queryforge_readonly LOGIN PASSWORD 'queryforge_readonly';
    END IF;
END
$$;

ALTER ROLE queryforge_readonly
    WITH LOGIN PASSWORD 'queryforge_readonly' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;

GRANT CONNECT ON DATABASE queryforge TO queryforge_readonly;
GRANT USAGE ON SCHEMA public TO queryforge_readonly;
REVOKE CREATE ON SCHEMA public FROM queryforge_readonly;
GRANT SELECT ON customers, categories, products, orders, order_items, payments, refunds TO queryforge_readonly;
