CREATE TABLE PowerStreet.ITO_Consolidado
(   
    CLO                                     INT NOT NULL,
    Agencia                                 VARCHAR(200) NOT NULL,
    Fecha                                   DATE NOT NULL,
    NUR                                    VARCHAR(20) NOT NULL,

    Visitas_Geocerca                        INT NOT NULL,
    Visitas_Totales                         INT NOT NULL,
    Visitas_Efectivas                       INT NOT NULL,
    Visitas_Programadas                     INT NOT NULL,
    Visitas_Unicas_Dentro_ITO               INT NOT NULL,

    Pct_Geocerca                            DECIMAL(10,4) NOT NULL,
    Pct_Cobertura_ITO                       DECIMAL(10,4) NOT NULL,
    Pct_Strike_Rate                         DECIMAL(10,4) NOT NULL,

    Visitas_Efectivas_MenorIgual_2min       INT NOT NULL,
    Pct_Visitas_Efectivas_MenorIgual_2min   DECIMAL(10,4) NOT NULL,
    Periodo                                 VARCHAR(35)
);