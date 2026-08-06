"""Load raw Olist CSVs into a dictionary of DataFrames."""
import pandas as pd
from pathlib import Path

RAW_DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "raw"

def load_raw_tables() -> dict[str, pd.DataFrame]:
    """Load all Olist CSVs and return them as a dict keyed by table name."""
    files = {
        "customers": "olist_customers_dataset.csv",
        "geolocation": "olist_geolocation_dataset.csv",
        "order_items": "olist_order_items_dataset.csv",
        "order_payments": "olist_order_payments_dataset.csv",
        "order_reviews": "olist_order_reviews_dataset.csv",
        "orders": "olist_orders_dataset.csv",
        "products": "olist_products_dataset.csv",
        "sellers": "olist_sellers_dataset.csv",
        "category_translation": "product_category_name_translation.csv",
    }

    tables = {}
    for name, filename in files.items():
        path = RAW_DATA_DIR / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {filename} in data/raw/. Did you download and unzip the dataset?"
            )
        tables[name] = pd.read_csv(path)

    return tables


if __name__ == "__main__":
    tables = load_raw_tables()
    for name, df in tables.items():
        print(f"{name:20s} → {df.shape[0]:>7,} rows, {df.shape[1]} cols")
print(2)        