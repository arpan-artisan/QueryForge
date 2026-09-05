# QueryForge Demo Database

The local demo database is a deterministic Postgres commerce fixture for Ask Data development and future evals.

It is local development data only. `uv run queryforge init-db` resets the `public` schema and replaces manual edits in the demo tables.

## Dataset Contract

- Version: `queryforge-commerce-v1`
- Schema: `public`
- Tables: `customers`, `categories`, `products`, `orders`, `order_items`, `payments`, `refunds`
- Fingerprint: `1b4911260c79d7ffa835a9c34c07c71fcbda93389cba0cea110f4f11d5a930b6`

Table grains:

- `customers`: one row per customer
- `categories`: one row per product category
- `products`: one row per product, linked to one category
- `orders`: one row per customer order
- `order_items`: one row per product line item in an order
- `payments`: one row per payment attempt for an order
- `refunds`: one row per refund event for an order

Relationships:

- `products.category_id -> categories.id`
- `orders.customer_id -> customers.id`
- `order_items.order_id -> orders.id`
- `order_items.product_id -> products.id`
- `payments.order_id -> orders.id`
- `refunds.order_id -> orders.id`

Metric rules:

- Completed revenue uses `SUM(order_items.quantity * order_items.unit_price)` for completed orders.
- Gross revenue includes completed and refunded orders.
- Net revenue is gross revenue minus refund amount.
- Average order value is completed revenue divided by completed order count.
- Refund rate is refund amount divided by gross revenue, expressed as a percentage.
- Payment success rate is the percentage of payment attempts with `payments.status = 'succeeded'`.
- Historical revenue must use `order_items.unit_price`, not current `products.unit_price`.

## Readiness Commands

```bash
docker compose up -d postgres
uv run queryforge init-db
uv run queryforge check-db
```

`init-db` uses `QUERYFORGE_DATABASE_OWNER_URL`. Ask Data and `check-db` use `QUERYFORGE_QUERY_DATABASE_URL`.

## Expected Facts

These values are the stable expected answers for future eval authors.

<!-- expected-facts-json:start -->
```json
{
  "row_counts": {
    "customers": 6,
    "categories": 4,
    "products": 8,
    "orders": 10,
    "order_items": 16,
    "payments": 10,
    "refunds": 2
  },
  "facts": {
    "completed_revenue": "2040.00",
    "gross_revenue": "2260.00",
    "net_revenue": "1995.00",
    "completed_order_count": 7,
    "average_order_value": "291.43",
    "refund_amount": "265.00",
    "refund_rate": "11.73",
    "payment_success_rate": "80.00",
    "revenue_by_product": [
      {
        "product": "Noise Canceling Headphones",
        "revenue": "450.00"
      },
      {
        "product": "USB-C Dock",
        "revenue": "380.00"
      },
      {
        "product": "4K Monitor",
        "revenue": "340.00"
      },
      {
        "product": "Portable Monitor",
        "revenue": "220.00"
      },
      {
        "product": "Laptop Stand",
        "revenue": "180.00"
      },
      {
        "product": "Starter Keyboard",
        "revenue": "180.00"
      },
      {
        "product": "Webcam Pro",
        "revenue": "160.00"
      },
      {
        "product": "Studio Microphone",
        "revenue": "130.00"
      }
    ],
    "revenue_by_category": [
      {
        "category": "Accessories",
        "revenue": "740.00"
      },
      {
        "category": "Audio",
        "revenue": "580.00"
      },
      {
        "category": "Displays",
        "revenue": "560.00"
      },
      {
        "category": "Video",
        "revenue": "160.00"
      }
    ],
    "revenue_by_month": [
      {
        "month": "2026-06-01",
        "revenue": "495.00"
      },
      {
        "month": "2026-07-01",
        "revenue": "395.00"
      },
      {
        "month": "2026-08-01",
        "revenue": "1150.00"
      }
    ]
  }
}
```
<!-- expected-facts-json:end -->

