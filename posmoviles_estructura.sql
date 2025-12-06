CREATE TABLE Usuarios (
    id_user    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    password   VARCHAR(255) NOT NULL,
    role       VARCHAR(20)  NOT NULL CHECK (role IN ('admin','cashier')),
    active     BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE Productos (
    id_product   BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    product_name VARCHAR(150) NOT NULL,
    barcode      VARCHAR(100) NOT NULL UNIQUE,
    price        DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    stock        INT NOT NULL DEFAULT 0 CHECK (stock >= 0),
    created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    product_state VARCHAR(10) DEFAULT 'Enable' CHECK (product_state IN ('Enable', 'Disable')),
    imagen_url VARCHAR(500)
);
CREATE TABLE Ventas (
    id_sale    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticket_id  BIGINT NOT NULL,
    quantity   TEXT NOT NULL,
    unit_price TEXT NOT NULL,
    total      DECIMAL(10,2) NOT NULL CHECK (total >= 0),
    id_user    BIGINT NOT NULL,
    ticket_number VARCHAR(50) NOT NULL,
    sale_datetime TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sale_state VARCHAR(50) NOT NULL,
    products TEXT NOT NULL
    CONSTRAINT ticket_id_unique UNIQUE (ticket_id),
    CONSTRAINT fk_venta_usuario FOREIGN KEY (id_user) REFERENCES usuarios(id_user)
);
CREATE INDEX idx_ventas_ticket       ON Ventas(ticket_id);
CREATE INDEX idx_productos_nombre    ON Productos(product_name);

--Funcion para obtener los precios de cada producto en la lista
CREATE OR REPLACE FUNCTION obtener_precios_desde_productos(lista_productos TEXT)
RETURNS TABLE(
    producto_nombre TEXT,
    precio DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    WITH productos_lista AS (
        SELECT 
            trim(unnest(string_to_array(trim(both '()' from lista_productos), ','))) as producto_buscado
    )
    SELECT 
        pl.producto_buscado as producto_nombre,
        p.price as precio
    FROM productos_lista pl
    INNER JOIN productos p ON pl.producto_buscado = p.product_name
    ORDER BY pl.producto_buscado;
END;
$$ LANGUAGE plpgsql;

--Funcion para comprobar el stock de los productos
CREATE OR REPLACE FUNCTION productos_sin_stock(lista_productos TEXT)
RETURNS TABLE(
    producto_nombre TEXT
) AS $$
BEGIN
    RETURN QUERY
    WITH productos_expandidos AS (
        SELECT 
            trim(unnest(string_to_array(trim(both '()' from lista_productos), ','))) as producto_venta
    )
    SELECT 
        pe.producto_venta as producto_nombre
    FROM productos_expandidos pe
    INNER JOIN productos p ON pe.producto_venta = p.product_name
    WHERE p.stock = 0
    ORDER BY pe.producto_venta;
END;
$$ LANGUAGE plpgsql;

--Funcion para comprobar que los productos existan
CREATE OR REPLACE FUNCTION productos_inexistentes(lista_productos TEXT)
    RETURNS TABLE(producto_inexistente TEXT) AS $$
    BEGIN
        RETURN QUERY
        WITH productos_expandidos AS (
            SELECT 
                trim(unnest(string_to_array(trim(both '()' from lista_productos), ','))) as producto_venta
        )
        SELECT 
            pe.producto_venta
        FROM productos_expandidos pe
        LEFT JOIN productos p ON pe.producto_venta = p.product_name
        WHERE p.product_name IS NULL
        ORDER BY pe.producto_venta;
    END;
    $$ LANGUAGE plpgsql;