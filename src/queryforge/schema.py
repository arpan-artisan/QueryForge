SCHEMA_CONTEXT = """
You can query this PostgreSQL ecommerce schema.

Tables:

customers
- id integer primary key
- name text
- email text
- created_at date

products
- id integer primary key
- name text
- category text
- unit_price numeric

orders
- id integer primary key
- customer_id integer references customers.id
- order_date date
- status text: completed, refunded, pending, cancelled

order_items
- id integer primary key
- order_id integer references orders.id
- product_id integer references products.id
- quantity integer
- unit_price numeric purchase-time price

refunds
- id integer primary key
- order_id integer references orders.id
- refund_date date
- amount numeric
- reason text

Revenue means SUM(order_items.quantity * order_items.unit_price) for completed orders.
Refund amount means SUM(refunds.amount).
Use only SELECT statements.
""".strip()
