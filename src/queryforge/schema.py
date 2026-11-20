from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class MetricDefinition:
    metric_id: str
    display_name: str
    definition: str


@dataclass(frozen=True, slots=True)
class SchemaColumn:
    name: str
    data_type: str
    description: str | None = None

    def prompt_line(self) -> str:
        suffix = f" {self.description}" if self.description else ""
        return f"- {self.name} {self.data_type}{suffix}"


@dataclass(frozen=True, slots=True)
class SchemaTable:
    name: str
    description: str
    grain: str
    columns: tuple[SchemaColumn, ...]


@dataclass(frozen=True, slots=True)
class SchemaRelationship:
    source_table: str
    source_column: str
    target_table: str
    target_column: str

    def prompt_line(self) -> str:
        return (
            f"- {self.source_table}.{self.source_column} -> "
            f"{self.target_table}.{self.target_column}"
        )


@dataclass(frozen=True, slots=True)
class SchemaCatalog:
    schema_name: str
    tables: tuple[SchemaTable, ...]
    relationships: tuple[SchemaRelationship, ...]


REVENUE_METRIC_DEFINITIONS = (
    MetricDefinition(
        metric_id="completed_revenue",
        display_name="Completed revenue",
        definition=(
            "SUM(order_items.quantity * order_items.unit_price) for orders where "
            "orders.status = 'completed'."
        ),
    ),
    MetricDefinition(
        metric_id="gross_revenue",
        display_name="Gross revenue",
        definition=(
            "SUM(order_items.quantity * order_items.unit_price) for orders where "
            "orders.status IN ('completed', 'refunded')."
        ),
    ),
    MetricDefinition(
        metric_id="refund_amount",
        display_name="Refund amount",
        definition="SUM(refunds.amount).",
    ),
    MetricDefinition(
        metric_id="net_revenue",
        display_name="Net revenue",
        definition="gross revenue minus refund amount.",
    ),
)


APPROVED_SCHEMA_CATALOG = SchemaCatalog(
    schema_name="public",
    tables=(
        SchemaTable(
            name="customers",
            description="Customer accounts with approved regional and segment attributes.",
            grain="one row per customer",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("name", "text"),
                SchemaColumn("created_at", "date"),
                SchemaColumn("region", "text", "North, South, East, West"),
                SchemaColumn("segment", "text", "Consumer, Business"),
            ),
        ),
        SchemaTable(
            name="categories",
            description="Product category reference data.",
            grain="one row per product category",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("name", "text"),
                SchemaColumn("description", "text"),
            ),
        ),
        SchemaTable(
            name="products",
            description="Product catalog entries and current catalog prices.",
            grain="one row per product, linked to one category",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("category_id", "integer", "references categories.id"),
                SchemaColumn("name", "text"),
                SchemaColumn("sku", "text"),
                SchemaColumn("unit_price", "numeric", "current catalog price"),
                SchemaColumn("active", "boolean"),
            ),
        ),
        SchemaTable(
            name="orders",
            description="Customer orders with lifecycle status and sales channel.",
            grain="one row per customer order",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("customer_id", "integer", "references customers.id"),
                SchemaColumn("order_date", "date"),
                SchemaColumn("status", "text", "completed, refunded, pending, cancelled"),
                SchemaColumn("channel", "text", "web, retail, partner"),
            ),
        ),
        SchemaTable(
            name="order_items",
            description="Purchase-time product line items belonging to orders.",
            grain="one row per product line item in an order",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("order_id", "integer", "references orders.id"),
                SchemaColumn("product_id", "integer", "references products.id"),
                SchemaColumn("quantity", "integer"),
                SchemaColumn("unit_price", "numeric", "purchase-time line-item price"),
            ),
        ),
        SchemaTable(
            name="payments",
            description="Payment attempts and their outcomes for orders.",
            grain="one row per payment attempt for an order",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("order_id", "integer", "references orders.id"),
                SchemaColumn("payment_date", "date"),
                SchemaColumn("amount", "numeric"),
                SchemaColumn("method", "text", "card, upi, wallet"),
                SchemaColumn("status", "text", "succeeded, failed, pending"),
            ),
        ),
        SchemaTable(
            name="refunds",
            description="Refund events issued against orders.",
            grain="one row per refund event for an order",
            columns=(
                SchemaColumn("id", "integer", "primary key"),
                SchemaColumn("order_id", "integer", "references orders.id"),
                SchemaColumn("refund_date", "date"),
                SchemaColumn("amount", "numeric"),
                SchemaColumn("reason", "text"),
            ),
        ),
    ),
    relationships=(
        SchemaRelationship("products", "category_id", "categories", "id"),
        SchemaRelationship("orders", "customer_id", "customers", "id"),
        SchemaRelationship("order_items", "order_id", "orders", "id"),
        SchemaRelationship("order_items", "product_id", "products", "id"),
        SchemaRelationship("payments", "order_id", "orders", "id"),
        SchemaRelationship("refunds", "order_id", "orders", "id"),
    ),
)


def render_schema_context(catalog: SchemaCatalog = APPROVED_SCHEMA_CATALOG) -> str:
    tables = "\n\n".join(
        f"{table.name}: {table.grain}\n"
        + "\n".join(column.prompt_line() for column in table.columns)
        for table in catalog.tables
    )
    relationships = "\n".join(item.prompt_line() for item in catalog.relationships)
    revenue_metrics = "\n".join(
        f"- {metric.display_name} means {metric.definition}"
        for metric in REVENUE_METRIC_DEFINITIONS
    )
    return f"""
You can query this PostgreSQL ecommerce demo schema.

Schema: {catalog.schema_name}

Tables and grains:

{tables}

Relationships:
{relationships}

Metric definitions:
{revenue_metrics}
- Completed order count means COUNT(*) from orders where orders.status = 'completed'.
- Average order value means completed revenue divided by completed order count.
- Refund rate means refund amount divided by gross revenue, expressed as a percentage.
- Payment success rate means AVG(CASE WHEN payments.status = 'succeeded' THEN 1 ELSE 0 END) * 100, expressed as a percentage.

Rules:
- Use order_items.unit_price for historical revenue, not products.unit_price.
- Aggregate order_items revenue and refunds independently before combining them.
- Use only the supplied tables and columns.
- Do not use customer email or any raw personal data.
- Return exactly one SELECT statement.
""".strip()


SCHEMA_CONTEXT = render_schema_context()
