SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS order_reviews;
DROP TABLE IF EXISTS order_payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS product_categories;
DROP TABLE IF EXISTS sellers;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS geolocations;

CREATE TABLE geolocations (
    zip_code_prefix VARCHAR(10) PRIMARY KEY,
    latitude DOUBLE NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude DOUBLE NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    city VARCHAR(100) NOT NULL,
    state CHAR(2) NOT NULL
) ENGINE=InnoDB COMMENT='Catálogo normalizado de ubicaciones por prefijo de código postal.';

CREATE TABLE product_categories (
    category_name VARCHAR(100) PRIMARY KEY,
    category_name_english VARCHAR(100) NOT NULL
) ENGINE=InnoDB COMMENT='Catálogo maestro de categorías de productos y su traducción.';

-- Entidades Principales
CREATE TABLE customers (
    customer_id CHAR(32) PRIMARY KEY,
    customer_unique_id CHAR(32) NOT NULL,
    zip_code_prefix VARCHAR(10) NOT NULL,
    CONSTRAINT fk_customers_geolocation 
        FOREIGN KEY (zip_code_prefix) REFERENCES geolocations(zip_code_prefix)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE sellers (
    seller_id CHAR(32) PRIMARY KEY,
    zip_code_prefix VARCHAR(10) NOT NULL,
    CONSTRAINT fk_sellers_geolocation 
        FOREIGN KEY (zip_code_prefix) REFERENCES geolocations(zip_code_prefix)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE products (
    product_id CHAR(32) PRIMARY KEY,
    category_name VARCHAR(100),
    name_length INT CHECK (name_length >= 0),
    description_length INT CHECK (description_length >= 0),
    photos_qty INT DEFAULT 0 CHECK (photos_qty >= 0),
    weight_g INT CHECK (weight_g >= 0),
    length_cm INT CHECK (length_cm >= 0),
    height_cm INT CHECK (height_cm >= 0),
    width_cm INT CHECK (width_cm >= 0),
    CONSTRAINT fk_products_category 
        FOREIGN KEY (category_name) REFERENCES product_categories(category_name)
        ON UPDATE CASCADE ON DELETE SET NULL
) ENGINE=InnoDB;

-- Tablas Transaccionales
CREATE TABLE orders (
    order_id CHAR(32) PRIMARY KEY,
    customer_id CHAR(32) NOT NULL,
    order_status VARCHAR(20) NOT NULL DEFAULT 'created' 
        CHECK (order_status IN ('created', 'approved', 'invoiced', 'processing', 'shipped', 'delivered', 'unavailable', 'canceled')),
    purchase_timestamp DATETIME NOT NULL,
    approved_at DATETIME NULL,
    delivered_carrier_date DATETIME NULL,
    delivered_customer_date DATETIME NULL,
    estimated_delivery_date DATETIME NOT NULL,
    CONSTRAINT fk_orders_customer 
        FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE order_items (
    order_id CHAR(32) NOT NULL,
    order_item_id INT NOT NULL CHECK (order_item_id >= 1),
    product_id CHAR(32) NOT NULL,
    seller_id CHAR(32) NOT NULL,
    shipping_limit_date DATETIME NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    freight_value DECIMAL(10, 2) NOT NULL DEFAULT 0.00 CHECK (freight_value >= 0),
    PRIMARY KEY (order_id, order_item_id),
    CONSTRAINT fk_items_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_items_product FOREIGN KEY (product_id) REFERENCES products(product_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_items_seller FOREIGN KEY (seller_id) REFERENCES sellers(seller_id) ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE order_payments (
    order_id CHAR(32) NOT NULL,
    payment_sequential INT NOT NULL CHECK (payment_sequential >= 1),
    payment_type VARCHAR(30) NOT NULL 
        CHECK (payment_type IN ('credit_card', 'boleto', 'voucher', 'debit_card', 'not_defined')),
    payment_installments INT NOT NULL DEFAULT 1 CHECK (payment_installments >= 0),
    payment_value DECIMAL(10, 2) NOT NULL CHECK (payment_value >= 0),
    PRIMARY KEY (order_id, payment_sequential),
    CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE order_reviews (
    review_id CHAR(32) PRIMARY KEY,
    order_id CHAR(32) NOT NULL,
    review_score INT NOT NULL CHECK (review_score BETWEEN 1 AND 5),
    comment_title VARCHAR(255),
    comment_message TEXT,
    creation_date DATETIME NOT NULL,
    answer_timestamp DATETIME NULL,
    CONSTRAINT fk_reviews_order FOREIGN KEY (order_id) REFERENCES orders(order_id) ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

SET FOREIGN_KEY_CHECKS = 1;

