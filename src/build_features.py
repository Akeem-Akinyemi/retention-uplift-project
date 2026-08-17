"""Build a customer-level feature table from raw Olist tables using DuckDB."""
import duckdb
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent))
from load_data import load_raw_tables

PROCESSED_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"


def build_customer_features() -> None:
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
            o.order_status,
            CAST(o.order_purchase_timestamp AS TIMESTAMP) AS order_purchase_timestamp,
            CAST(o.order_delivered_customer_date AS TIMESTAMP) AS order_delivered_customer_date,
            CAST(o.order_estimated_delivery_date AS TIMESTAMP) AS order_estimated_delivery_date
        FROM orders o
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_status = 'delivered'
    ),

    order_values AS (
        SELECT
            order_id,
            SUM(payment_value) AS order_value
        FROM order_payments
        GROUP BY order_id
    ),

    order_reviews_agg AS (
        SELECT
            order_id,
            AVG(review_score) AS review_score
        FROM order_reviews
        GROUP BY order_id
    ),

    order_level AS (
        SELECT
            oc.customer_unique_id,
            oc.customer_state,
            oc.order_id,
            oc.order_purchase_timestamp,
            ov.order_value,
            orv.review_score,
            DATE_DIFF(
                'day',
                oc.order_estimated_delivery_date,
                oc.order_delivered_customer_date
            ) AS delivery_delay_days
        FROM orders_customers oc
        LEFT JOIN order_values ov ON oc.order_id = ov.order_id
        LEFT JOIN order_reviews_agg orv ON oc.order_id = orv.order_id
    )

    SELECT
        customer_unique_id,
        MAX(customer_state) AS customer_state,
        COUNT(DISTINCT order_id) AS n_orders,
        MIN(order_purchase_timestamp) AS first_purchase_date,
        MAX(order_purchase_timestamp) AS last_purchase_date,
        DATE_DIFF(
            'day',
            MAX(order_purchase_timestamp),
            (SELECT MAX(order_purchase_timestamp) FROM order_level)
        ) AS recency_days,
        SUM(order_value) AS total_spend,
        AVG(order_value) AS avg_order_value,
        AVG(review_score) AS avg_review_score,
        AVG(delivery_delay_days) AS avg_delivery_delay_days
    FROM order_level
    GROUP BY customer_unique_id
    ORDER BY total_spend DESC
    """

    customer_features = con.execute(query).df()

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    output_path = PROCESSED_DIR / "customer_features.csv"
    customer_features.to_csv(output_path, index=False)

    print(f"Built customer_features table: {customer_features.shape[0]:,} customers, "
          f"{customer_features.shape[1]} columns")
    print(f"Saved to {output_path}")
    print("\nPreview:")
    print(customer_features.head())


if __name__ == "__main__":
    build_customer_features()
    