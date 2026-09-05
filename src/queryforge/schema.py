SCHEMA_CONTEXT = """
You can query this PostgreSQL ecommerce demo schema.

Schema: public

Tables and grains:

customers: one row per customer
- id integer primary key
- name text
- created_at date
- region text: North, South, East, West
- segment text: Consumer, Business

categories: one row per product category
- id integer primary key
- name text
- description text

products: one row per product, linked to one category
- id integer primary key
- category_id integer references categories.id
- name text
- sku text
- unit_price numeric current catalog price
- active boolean

orders: one row per customer order
- id integer primary key
- customer_id integer references customers.id
- order_date date
- status text: completed, refunded, pending, cancelled
- channel text: web, retail, partner

order_items: one row per product line item in an order
- id integer primary key
- order_id integer references orders.id
- product_id integer references products.id
- quantity integer
- unit_price numeric purchase-time line-item price

payments: one row per payment attempt for an order
- id integer primary key
- order_id integer references orders.id
- payment_date date
- amount numeric
- method text: card, upi, wallet
- status text: succeeded, failed, pending

refunds: one row per refund event for an order
- id integer primary key
- order_id integer references orders.id
- refund_date date
- amount numeric
- reason text

Relationships:
- products.category_id -> categories.id
- orders.customer_id -> customers.id
- order_items.order_id -> orders.id
- order_items.product_id -> products.id
- payments.order_id -> orders.id
- refunds.order_id -> orders.id

Metric definitions:
- Completed revenue means SUM(order_items.quantity * order_items.unit_price) for orders where orders.status = 'completed'.
- Gross revenue means SUM(order_items.quantity * order_items.unit_price) for orders where orders.status IN ('completed', 'refunded').
- Refund amount means SUM(refunds.amount).
- Net revenue means gross revenue minus refund amount.
- Completed order count means COUNT(*) from orders where orders.status = 'completed'.
- Average order value means completed revenue divided by completed order count.
- Refund rate means refund amount divided by gross revenue, expressed as a percentage.
- Payment success rate means AVG(CASE WHEN payments.status = 'succeeded' THEN 1 ELSE 0 END) * 100, expressed as a percentage.

Rules:
- Use order_items.unit_price for historical revenue, not products.unit_price.
- Use only the supplied tables and columns.
- Do not use customer email or any raw personal data.
- Return exactly one SELECT statement.
""".strip()
