# config.py

DATABASE_CONFIG = {
    'host': 'localhost',
    'port': 3312,
    'user': 'root',
    'password': 'datarea',
    'database': 'olist_db',
}

DATABASE_CONFIG_DW = {
    'host': 'localhost',
    'port': 3312,
    'user': 'root',
    'password': 'datarea',
    'database': 'dwolist'
}

CSV_FILES = {
    'customers': 'data/olist_customers_dataset.csv',
    'geolocation': 'data/olist_geolocation_dataset.csv',
    'order_items': 'data/olist_order_items_dataset.csv',
    'order_payments': 'data/olist_order_payments_dataset.csv',
    'order_reviews': 'data/olist_order_reviews_dataset.csv',
    'orders': 'data/olist_orders_dataset.csv',
    'products': 'data/olist_products_dataset.csv',
    'sellers': 'data/olist_sellers_dataset.csv',
    'product_category': 'data/product_category_name_translation.csv'
}

LOG_FILE = 'logs/pipeline.log'