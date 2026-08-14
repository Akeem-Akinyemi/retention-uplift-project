"""
Build a feature table using ONLY information available at a customer's
FIRST order — no downstream orders, no future information.

This matters because our target is "did this customer place a second order,"
so any feature computed across a customer's full order history (total spend,
order count, recency) would leak the answer into the input.
"""
import duckdb
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from load_data import load_raw_tables

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def build_first_order_features() -> None:
    tables = load_raw_tables()

    con = duckdb.connect()
    for name, df in tables.items():
        con.register(name, df)

    query = """
    WITH orders_customers AS (
        SELECT
            o.order_id,
            c.customer_unique_id,
            c.customer_state,
            CAST(o.order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
            CAST(o.order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
            CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
    ),

    first_orders AS (
        SELECT *,
            ROW_NUMBER() OVER (
                PARTITION BY customer_unique_id
                ORDER BY order_purchase_timestamp
            ) AS order_rank
        FROM orders_customers
        QUALIFY order_rank = 1
    ),

    order_items_agg AS (
        SELECT
            order_id,
            COUNT(*) AS n_items,
            SUM(price) AS items_total_price,
            SUM(freight_value) AS total_freight,
            COUNT(DISTINCT product_id) AS n_distinct_products
        FROM order_items
        GROUP BY order_id
    ),

    first_item_category AS (
        SELECT
            oi.order_id,
            p.product_category_name,
            ROW_NUMBER() OVER (PARTITION BY oi.order_id ORDER BY oi.order_item_id) AS rn
        FROM order_items oi
        JOIN products p ON oi.product_id = p.product_id
        QUALIFY rn = 1
    ),

    payments_agg AS (
        SELECT
            order_id,
            SUM(payment_value) AS payment_total,
            MAX(payment_installments) AS max_installments,
            ARG_MAX(payment_type, payment_value) AS payment_type
        FROM order_payments
        GROUP BY order_id
    ),

    reviews_agg AS (
        SELECT
            order_id,
            AVG(review_score) AS review_score
        FROM order_reviews
        GROUP BY order_id
    )

    SELECT
        fo.customer_unique_id,
        fo.customer_state,
        fo.order_purchase_timestamp AS first_purchase_date,
        oi.n_items,
        oi.n_distinct_products,
        oi.items_total_price,
        oi.total_freight,
        fic.product_category_name,
        pay.payment_total,
        pay.max_installments,
        pay.payment_type,
        DATE_DIFF('day', fo.order_purchase_timestamp, fo.order_delivered_customer_date) AS delivery_days,
        DATE_DIFF('day', fo.order_estimated_delivery_date, fo.order_delivered_customer_date) AS delivery_delay_days,
        rev.review_score
    FROM first_orders fo
    LEFT JOIN order_items_agg oi ON fo.order_id = oi.order_id
    LEFT JOIN first_item_category fic ON fo.order_id = fic.order_id
    LEFT JOIN payments_agg pay ON fo.order_id = pay.order_id
    LEFT JOIN reviews_agg rev ON fo.order_id = rev.order_id
    """

    first_order_features = con.execute(query).df()

    output_path = PROCESSED_DIR / "first_order_features.csv"
    first_order_features.to_csv(output_path, index=False)

    print(f"Built first_order_features: {first_order_features.shape[0]:,} customers, "
          f"{first_order_features.shape[1]} columns")
    print(first_order_features.head())


if __name__ == "__main__":
    build_first_order_features()