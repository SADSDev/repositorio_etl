CREATE TABLE PowerStreet.Universo_Clientes
(
    Distribuidor                INT             NOT NULL,
    Agencia                     INT             NOT NULL,

    Codigo_GLN                  VARCHAR(20)     NOT NULL,
    Codigo_Pwst                 VARCHAR(20)     NULL,

    Fecha_Actualizacion         DATE            NOT NULL,

    Itinerarios                 VARCHAR(50)     NULL,
    Frecuencia                  TINYINT         NULL,

    Lunes                       INT             NULL,
    Martes                      INT             NULL,
    Miercoles                   INT             NULL,
    Jueves                      INT             NULL,
    Viernes                     INT             NULL,
    Sabado                      INT             NULL,

    Nombre                      VARCHAR(300)    NULL,
    Colonia                     VARCHAR(300)    NULL,
    Direccion                   VARCHAR(300)    NULL,

    Potencial                   VARCHAR(100)     NULL,

    Estado                      VARCHAR(200)    NULL,
    Municipio                   VARCHAR(200)    NULL,

    Zona                        INT             NULL,
    ZonaVent                    INT             NULL,
    ZonaRepa                    INT             NULL,

    TipoCliente                 VARCHAR(100)     NULL,
    Canal                       VARCHAR(200)    NULL,
    Lista                       VARCHAR(250)    NULL,

    X                           NUMERIC(18,9)   NULL,
    Y                           NUMERIC(18,9)   NULL,

    Codigo_MKD                  VARCHAR(60)     NULL,
    Baja                        VARCHAR(60)     NULL,
    Potencial_MKD               VARCHAR(60)     NULL,
    Censo                       VARCHAR(60)     NULL,
    Status                      VARCHAR(60)     NULL,

    NUR                         VARCHAR(30)     NULL,

    Tipo_Credito                VARCHAR(100)     NULL,
    Programa                    VARCHAR(200)    NULL,

    Telefono_Cliente            VARCHAR(100)     NULL,
    Telefono_Mensajes           VARCHAR(100)     NULL,
    CorreoElectronico           VARCHAR(250)    NULL,

    CONSTRAINT PK_Clientes
        PRIMARY KEY (Codigo_GLN),

    CONSTRAINT FK_Clientes_Agencias
        FOREIGN KEY (Agencia)
        REFERENCES CATALOGOS.Agencias(Agencia)
);