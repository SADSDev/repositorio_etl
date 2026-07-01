CREATE TABLE PowerStreet.Venta_Diaria
(
    Fecha               DATE            NOT NULL,
    NUR                 VARCHAR(20)     NOT NULL,
    Vendedor            VARCHAR(10)     NOT NULL,
    Cliente             VARCHAR(20)     NOT NULL,
    Nombre_Cliente      VARCHAR(200)    NULL,
    Potencial           VARCHAR(10)     NULL,
    Codigo_Articulo        VARCHAR(20)     NOT NULL,
    Descripcion_Articulo    VARCHAR(100)    NOT NULL,
    Cantidad            DECIMAL(12,4)   NOT NULL,
    Total               DECIMAL(12,4)   NOT NULL
);