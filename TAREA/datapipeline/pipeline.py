# pipeline.py
import io
import re
import sys
import logging
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine
from data.utils.config import DATABASE_CONFIG, DATABASE_CONFIG_DW, CSV_FILES, LOG_FILE

# Asegurar que la carpeta de logs exista antes de configurar logging
Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def create_db_engine(config):
    """Crea una conexión de motor a la base de datos MySQL."""
    try:
        engine = create_engine(
            f"mysql+mysqlconnector://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}",
            echo=False
        )
        # Validar conexión real inmediatamente
        with engine.connect() as conn:
            pass
        logging.info(f"Conexión a la base de datos '{config['database']}' establecida correctamente.")
        return engine
    except Exception as e:
        logging.error(f"Error al conectar a la base de datos '{config['database']}': {e}")
        print(f"Error al conectar a MySQL ({config['database']}): {e}")
        sys.exit(1)


def read_csv(file_path):

    try:
        with open(file_path, 'r', encoding='utf-8-sig', errors='replace') as f:
            raw_lines = f.readlines()

        cleaned_lines = []
        for line in raw_lines:
            line = line.rstrip('\r\n')
            line = re.sub(r'\|+$', '', line)
            if line.startswith('"') and line.endswith('"') and '""' in line:
                line = line[1:-1].replace('""', '"')
            cleaned_lines.append(line)

        df = pd.read_csv(
            io.StringIO('\n'.join(cleaned_lines)),
            dtype={'zip_code_prefix': str, 'geolocation_zip_code_prefix': str}
        )
        logging.info(f"Archivo {file_path} leído exitosamente ({len(df)} filas).")
        return df
    except Exception as e:
        logging.error(f"Error al leer el archivo {file_path}: {e}")
        print(f"Error al leer {file_path}: {e}")
        sys.exit(1)


def load_data(engine, table_name, df, if_exists='append'):
    """Carga un DataFrame de pandas a una tabla de MySQL."""
    try:
        df.to_sql(name=table_name, con=engine, if_exists=if_exists, index=False, chunksize=5000)
        logging.info(f"Datos cargados exitosamente en '{table_name}' ({len(df)} filas).")
        print(f"OK -> {table_name}: {len(df)} filas insertadas.")
    except Exception as e:
        logging.error(f"Error al cargar datos en la tabla {table_name}: {e}")
        print(f"ERROR al insertar en {table_name}: {e}")
        sys.exit(1)


def prepare_geolocation(df_geolocation):
    """Renombra columnas de geolocalización y deduplica por zip_code_prefix."""
    return (
        df_geolocation
        .rename(columns={
            'geolocation_zip_code_prefix': 'zip_code_prefix',
            'geolocation_lat': 'latitude',
            'geolocation_lng': 'longitude',
            'geolocation_city': 'city',
            'geolocation_state': 'state'
        })
        .groupby('zip_code_prefix', as_index=False)
        .first()
    )


def transform_customers(df_customers, geo_unicos):
    """Construye dim_customers alineado a los nombres de columna del CSV y DW."""
    dim_customer = (
        df_customers
        .rename(columns={'id': 'customer_id', 'unique_id': 'customer_unique_id'})
        .merge(
            geo_unicos[['zip_code_prefix', 'latitude', 'longitude']],
            on='zip_code_prefix',
            how='left'
        )
        .assign(
            city=lambda df: df['city'].fillna('desconocida'),
            state=lambda df: df['state'].fillna('NA')
        )
        [['customer_id', 'customer_unique_id', 'zip_code_prefix', 'city', 'state', 'latitude', 'longitude']]
        .reset_index(drop=True)
    )
    dim_customer.insert(0, 'customer_sk', range(1, len(dim_customer) + 1))
    return dim_customer


def transform_product(df_products, df_product_category):
    """Construye dim_products renombrando prefijos product_*."""
    dim_product = (
        df_products
        .rename(columns={
            'product_category_name': 'category_name',
            'product_weight_g': 'weight_g',
            'product_length_cm': 'length_cm',
            'product_height_cm': 'height_cm',
            'product_width_cm': 'width_cm'
        })
        .merge(
            df_product_category[['category_name', 'category_name_english']],
            on='category_name',
            how='left'
        )
        .assign(
            category_name=lambda df: df['category_name'].fillna('sin_categoria'),
            category_name_english=lambda df: df['category_name_english'].fillna('uncategorized')
        )
        [[
            'product_id',
            'category_name',
            'category_name_english',
            'weight_g',
            'length_cm',
            'height_cm',
            'width_cm'
        ]]
        .reset_index(drop=True)
    )
    dim_product.insert(0, 'product_sk', range(1, len(dim_product) + 1))
    return dim_product


def transform_sellers(df_sellers, geo_unicos):
    """Construye dim_sellers deduplicado por zip_code_prefix."""
    dim_sellers = (
        df_sellers
        .merge(
            geo_unicos[['zip_code_prefix', 'latitude', 'longitude']],
            on='zip_code_prefix',
            how='left'
        )
        .assign(
            city=lambda df: df['city'].fillna('desconocida'),
            state=lambda df: df['state'].fillna('NA')
        )
        [['seller_id', 'zip_code_prefix', 'city', 'state', 'latitude', 'longitude']]
        .reset_index(drop=True)
    )
    dim_sellers.insert(0, 'seller_sk', range(1, len(dim_sellers) + 1))
    return dim_sellers


def transform_date(df_orders):
    """Construye dim_date a partir de purchase_timestamp."""
    fechas = (
        pd.to_datetime(df_orders['purchase_timestamp'])
        .dropna()
        .dt.normalize()
        .drop_duplicates()
        .sort_values()
    )

    # DAYOFWEEK() de MySQL: 1=Domingo, 2=Lunes, ..., 7=Sábado
    mysql_dow = ((fechas.dt.dayofweek + 1) % 7) + 1

    dim_date = pd.DataFrame({
        'date_sk': fechas.dt.strftime('%Y%m%d').astype('uint32'),
        'full_date': fechas.dt.date,
        'year': fechas.dt.year,
        'quarter': fechas.dt.quarter,
        'month': fechas.dt.month,
        'month_name': fechas.dt.month_name(),
        'day_of_month': fechas.dt.day,
        'day_of_week': mysql_dow,
        'day_name': fechas.dt.day_name(),
        'is_weekend': mysql_dow.isin([1, 7])
    }).reset_index(drop=True)

    return dim_date


def transform_payments(df_order_payments):
    """Construye dim_payment asegurando que exista el registro 'not_defined'."""
    dim_payment = (
        df_order_payments[['payment_type', 'payment_installments']]
        .drop_duplicates()
        .rename(columns={'payment_type': 'primary_payment_type'})
        .assign(
            is_installment_plan=lambda df: df['payment_installments'] > 1
        )
        .reset_index(drop=True)
    )

    if 'not_defined' not in dim_payment['primary_payment_type'].values:
        fallback = pd.DataFrame([{
            'primary_payment_type': 'not_defined',
            'payment_installments': 0,
            'is_installment_plan': False
        }])
        dim_payment = pd.concat([dim_payment, fallback], ignore_index=True)

    dim_payment.insert(0, 'payment_sk', range(1, len(dim_payment) + 1))
    return dim_payment


def transform_fact(df_order_payments, df_order_reviews, dim_payment, df_orders, df_order_items, dim_customers, dim_products, dim_sellers):
    """Construye fact_sales uniendo hechos con las llaves subrogadas de cada dimensión."""
    # 1. Pago principal por orden
    primary_payments = (
        df_order_payments
        .sort_values(
            by=['order_id', 'payment_value', 'payment_sequential'],
            ascending=[True, False, True]
        )
        .drop_duplicates(subset=['order_id'], keep='first')
        [['order_id', 'payment_type', 'payment_installments']]
    )

    # 2. Promedio de calificación por orden (limpiando la fila corrupta en review_score)
    order_avg_reviews = (
        df_order_reviews
        .assign(review_score=pd.to_numeric(df_order_reviews['review_score'], errors='coerce'))
        .dropna(subset=['review_score'])
        .groupby('order_id', as_index=False)['review_score']
        .mean()
        .assign(review_score=lambda df: df['review_score'].round(2))
    )

    not_defined_sk = dim_payment.loc[
        dim_payment['primary_payment_type'] == 'not_defined', 'payment_sk'
    ].iloc[0]

    # Renombrar columnas de df_orders ('id' -> 'order_id', 'status' -> 'order_status')
    orders_clean = (
        df_orders
        .rename(columns={'id': 'order_id', 'status': 'order_status'})
        .assign(
            purchase_timestamp=pd.to_datetime(df_orders['purchase_timestamp']),
            delivered_customer_date=pd.to_datetime(df_orders['delivered_customer_date']),
            estimated_delivery_date=pd.to_datetime(df_orders['estimated_delivery_date'])
        )
    )

    fact_table = (
        df_order_items
        .merge(orders_clean, on='order_id', how='inner')
        .merge(dim_customers[['customer_id', 'customer_sk']], on='customer_id', how='inner')
        .merge(dim_products[['product_id', 'product_sk']], on='product_id', how='inner')
        .merge(dim_sellers[['seller_id', 'seller_sk']], on='seller_id', how='inner')
        .merge(primary_payments, on='order_id', how='left')
        .merge(
            dim_payment[['primary_payment_type', 'payment_installments', 'payment_sk']],
            left_on=['payment_type', 'payment_installments'],
            right_on=['primary_payment_type', 'payment_installments'],
            how='left'
        )
        .merge(order_avg_reviews, on='order_id', how='left')
        .assign(
            purchase_date_sk=lambda df: df['purchase_timestamp'].dt.strftime('%Y%m%d').astype('uint32'),
            payment_sk=lambda df: df['payment_sk'].fillna(not_defined_sk).astype(dim_payment['payment_sk'].dtype),
            total_item_amount=lambda df: df['price'] + df['freight_value'],
            delivery_time_days=lambda df: (
                df['delivered_customer_date'].dt.normalize() - df['purchase_timestamp'].dt.normalize()
            ).dt.days,
            delivery_delay_days=lambda df: (
                df['delivered_customer_date'].dt.normalize() - df['estimated_delivery_date'].dt.normalize()
            ).dt.days
        )
        [[
            'order_id',
            'order_item_id',
            'customer_sk',
            'product_sk',
            'seller_sk',
            'purchase_date_sk',
            'payment_sk',
            'order_status',
            'purchase_timestamp',
            'delivered_customer_date',
            'estimated_delivery_date',
            'price',
            'freight_value',
            'total_item_amount',
            'delivery_time_days',
            'delivery_delay_days',
            'review_score'
        ]]
    )

    return fact_table


def main():
    engine_dw = create_db_engine(DATABASE_CONFIG_DW)

    load_order = ['dim_customers', 'dim_products', 'dim_sellers', 'dim_date', 'dim_payment', 'fact_sales']
    dataframes = {}

    # Leer archivos
    df_customers = read_csv(CSV_FILES['customers'])
    df_geolocation = read_csv(CSV_FILES['geolocation'])
    df_order_items = read_csv(CSV_FILES['order_items'])
    df_order_payments = read_csv(CSV_FILES['order_payments'])
    df_order_reviews = read_csv(CSV_FILES['order_reviews'])
    df_orders = read_csv(CSV_FILES['orders'])
    df_products = read_csv(CSV_FILES['products'])
    df_sellers = read_csv(CSV_FILES['sellers'])
    df_product_category = read_csv(CSV_FILES['product_category'])

    # Preparar geolocalizaciones únicas
    geo_unicos = prepare_geolocation(df_geolocation)

    # Transformar dimensiones
    dim_customers = transform_customers(df_customers, geo_unicos)
    dataframes['dim_customers'] = dim_customers

    dim_products = transform_product(df_products, df_product_category)
    dataframes['dim_products'] = dim_products

    dim_sellers = transform_sellers(df_sellers, geo_unicos)
    dataframes['dim_sellers'] = dim_sellers

    dim_date = transform_date(df_orders)
    dataframes['dim_date'] = dim_date

    dim_payment = transform_payments(df_order_payments)
    dataframes['dim_payment'] = dim_payment

    # Transformar tabla de hechos (corregido: dim_payment en singular)
    fact_sales = transform_fact(
        df_order_payments,
        df_order_reviews,
        dim_payment,
        df_orders,
        df_order_items,
        dim_customers,
        dim_products,
        dim_sellers
    )
    dataframes['fact_sales'] = fact_sales

    # Cargar datos en MySQL en orden referencial
    for table in load_order:
        load_data(engine_dw, table, dataframes[table], if_exists='append')

    logging.info("Pipeline de datos ejecutado exitosamente.")
    print("Pipeline finalizado con éxito.")


if __name__ == "__main__":
    main()