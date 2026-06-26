CREATE TABLE PowerStreet.ITO_Detallado
(   
    CLO                             INT NOT NULL,
    Agencia                         INT NOT NULL,
    NUR                            VARCHAR(20) NOT NULL,
    Vendedor                        VARCHAR(100) NOT NULL,

    Fecha                           DATE NOT NULL,

    Secuencia_ITO                   INT NULL,
    Secuencia_Real                  INT NULL,

    Cliente                         VARCHAR(50) NOT NULL,
    Nombre_Cliente                   VARCHAR(250) NOT NULL,

    id_Visita                       VARCHAR(100) NULL,

    Estatus                         VARCHAR(50) NOT NULL,

    Apertura                        VARCHAR(20) NULL,
    Cierre                          VARCHAR(20) NULL,

    Inicio_de_visita                TIME NULL,
    Fin_de_visita                   TIME NULL,

    Tiempo_de_estancia_en_visita    INT NULL,
    Tiempo_translado                INT NULL,

    Visita_efectiva                 VARCHAR(5) NOT NULL,

    Visitas_Geocerca                INT NULL,
    Visitas_Totales                 INT NULL,
    Visitas_Programadas             INT NULL,
    Visitas_Unicas_ITO              INT NULL
);
GO


