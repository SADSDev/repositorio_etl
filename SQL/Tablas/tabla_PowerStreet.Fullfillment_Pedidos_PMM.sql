CREATE TABLE PowerStreet.Fullfilment_Pedidos_PMM
(
    NUR                     VARCHAR(20) NOT NULL,
    Fecha                   DATE NOT NULL,

    Vendedor                VARCHAR(20) NOT NULL,

    Cliente                 VARCHAR(20) NOT NULL,
    Nombre                  VARCHAR(250) NOT NULL,

    Orden                   VARCHAR(20) NOT NULL,

    Status_Orden            VARCHAR(30) NOT NULL,

    Documento_Orden         VARCHAR(100) NOT NULL,
    Documento_Auxiliar      VARCHAR(100) NULL,

    Status_Entrega          VARCHAR(30) NOT NULL,
    Motivo_Rechazo          VARCHAR(250) NULL,

    Total_Orden             DECIMAL(18,4) NULL,
    Cantidad_Orden          DECIMAL(18,4) NULL,

    Total_Entrega           DECIMAL(18,4) NULL,
    Cantidad_Entrega        DECIMAL(18,4) NULL,

    Cantidad_Contado        DECIMAL(18,4) NULL,
    Cantidad_Credito        DECIMAL(18,4) NULL,

    Total_Contado           DECIMAL(18,4) NULL,
    Total_Credito           DECIMAL(18,4) NULL,

    FillRate                DECIMAL(10,4) NULL,
    Volumen_Entregado       DECIMAL(10,4) NULL,
    Fulfillment             DECIMAL(10,4) NULL,

    Empresa                 INT NOT NULL,

    Clavecorr               VARCHAR(20) NOT NULL,
    Serie                   VARCHAR(20) NOT NULL,

    Nrodoc                  VARCHAR(20) NOT NULL,

    Detalle                 VARCHAR(100) NOT NULL
);
GO