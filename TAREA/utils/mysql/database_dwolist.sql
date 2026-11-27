create database dwolist;

USE dwolist;

SET FOREIGN_KEY_CHECKS = 0;


DROP TABLE IF EXISTS fact_sales;
DROP TABLE IF EXISTS dim_customers;
DROP TABLE IF EXISTS dim_products;
DROP TABLE IF EXISTS dim_sellers;
DROP TABLE IF EXISTS dim_date;
DROP TABLE IF EXISTS dim_payment;


CREATE TABLE dim_customers (
    customer_sk INT AUTO_INCREMENT PRIMARY KEY,
    customer_id CHAR(32) NOT NULL UNIQUE,
    customer_unique_id CHAR(32) NOT NULL,
    zip_code_prefix VARCHAR(10),
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL,
    latitude DOUBLE,
    longitude DOUBLE
) ENGINE=InnoDB;


CREATE TABLE dim_products (
    product_sk INT AUTO_INCREMENT PRIMARY KEY,
    product_id CHAR(32) NOT NULL UNIQUE,
    category_name VARCHAR(100),
    category_name_english VARCHAR(100),
    weight_g INT,
    length_cm INT,
    height_cm INT,
    width_cm INT
) ENGINE=InnoDB;


CREATE TABLE dim_sellers (
    seller_sk INT AUTO_INCREMENT PRIMARY KEY,
    seller_id CHAR(32) NOT NULL UNIQUE,
    zip_code_prefix VARCHAR(10),
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL,
    latitude DOUBLE,
    longitude DOUBLE
) ENGINE=InnoDB;


CREATE TABLE dim_date (
    date_sk INT PRIMARY KEY COMMENT 'Formato YYYYMMDD',
    full_date DATE NOT NULL UNIQUE,
    year INT NOT NULL,
    quarter INT NOT NULL,
    month INT NOT NULL,
    month_name VARCHAR(15) NOT NULL,
    day_of_month INT NOT NULL,
    day_of_week INT NOT NULL,
    day_name VARCHAR(15) NOT NULL,
    is_weekend BOOLEAN NOT NULL
) ENGINE=InnoDB;


CREATE TABLE dim_payment (
    payment_sk INT AUTO_INCREMENT PRIMARY KEY,
    primary_payment_type VARCHAR(30) NOT NULL,
    payment_installments INT NOT NULL,
    is_installment_plan BOOLEAN NOT NULL,
    UNIQUE KEY uq_payment_profile (primary_payment_type, payment_installments)
) ENGINE=InnoDB;


CREATE TABLE fact_sales (
    sales_sk BIGINT AUTO_INCREMENT PRIMARY KEY,
    order_id CHAR(32) NOT NULL,
    order_item_id INT NOT NULL,
    

    customer_sk INT NOT NULL,
    product_sk INT NOT NULL,
    seller_sk INT NOT NULL,
    purchase_date_sk INT NOT NULL,
    payment_sk INT NOT NULL,
    

    order_status VARCHAR(20) NOT NULL,
    purchase_timestamp DATETIME NOT NULL,
    delivered_customer_date DATETIME NULL,
    estimated_delivery_date DATETIME NOT NULL,
    

    price DECIMAL(10, 2) NOT NULL,
    freight_value DECIMAL(10, 2) NOT NULL,
    total_item_amount DECIMAL(10, 2) NOT NULL,
    delivery_time_days INT NULL,
    delivery_delay_days INT NULL,
    review_score DECIMAL(3, 2) NULL,
    
    UNIQUE KEY uq_order_item (order_id, order_item_id),
    CONSTRAINT fk_fact_customer FOREIGN KEY (customer_sk) REFERENCES dim_customers(customer_sk),
    CONSTRAINT fk_fact_product FOREIGN KEY (product_sk) REFERENCES dim_products(product_sk),
    CONSTRAINT fk_fact_seller FOREIGN KEY (seller_sk) REFERENCES dim_sellers(seller_sk),
    CONSTRAINT fk_fact_date FOREIGN KEY (purchase_date_sk) REFERENCES dim_date(date_sk),
    CONSTRAINT fk_fact_payment FOREIGN KEY (payment_sk) REFERENCES dim_payment(payment_sk)
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

