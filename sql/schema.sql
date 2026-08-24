CREATE TABLE IF NOT EXISTS customers (
    id integer PRIMARY KEY,
    name text NOT NULL,
    email text NOT NULL UNIQUE,
    created_at date NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    id integer PRIMARY KEY,
    name text NOT NULL,
    category text NOT NULL,
    unit_price numeric(12, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE IF NOT EXISTS orders (
    id integer PRIMARY KEY,
    customer_id integer NOT NULL REFERENCES customers(id),
    order_date date NOT NULL,
    status text NOT NULL CHECK (status IN ('completed', 'refunded', 'pending', 'cancelled'))
);

CREATE TABLE IF NOT EXISTS order_items (
    id integer PRIMARY KEY,
    order_id integer NOT NULL REFERENCES orders(id),
    product_id integer NOT NULL REFERENCES products(id),
    quantity integer NOT NULL CHECK (quantity > 0),
    unit_price numeric(12, 2) NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE IF NOT EXISTS refunds (
    id integer PRIMARY KEY,
    order_id integer NOT NULL REFERENCES orders(id),
    refund_date date NOT NULL,
    amount numeric(12, 2) NOT NULL CHECK (amount >= 0),
    reason text NOT NULL
);

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
GRANT SELECT ON customers, products, orders, order_items, refunds TO queryforge_readonly;
