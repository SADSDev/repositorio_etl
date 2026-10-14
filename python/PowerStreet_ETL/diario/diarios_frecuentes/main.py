#----------------------------------------
#LIBRERIAS
#----------------------------------------
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright
from sqlalchemy import text

#----------------------------------------
#IMPORTS
#----------------------------------------
from configuraciones.conexion_sql import motor
from configuraciones.parametros import schema
import configuraciones.entorno

from core.navegador import carga_pagina
from procesos.ventas_diarias import(
    ventas_descarga, ventas_carga_sql
)
from procesos.seguimiento_indicadores import(
    indicadores_descarga, indicadores_carga_sql
)
from procesos.combos_por_cliente import(
    combos_por_cliente_descarga, combos_por_cliente_carga_sql
)
from procesos.fullfillment_pedidos_pmm import(
    fullfillment_pedidos_descarga, fullfillment_pedidos_carga_sql
)
from procesos.ito_consolidado import(
    ito_consolidado_descarga, ito_consolidado_carga_sql
)
from procesos.ito_detallado import(
    ito_detallado_descarga, ito_detallado_carga_sql
)
from procesos.pdv_por_agencia import(
    pdv_agencia_descarga, pdv_agencia_carga_sql
)
from procesos.encuestas_supervisor import(
    encuestas_supervisor_descarga, encuestas_supervisor_carga_sql
)
#-----------------------------------
#PROCESO
#-----------------------------------

#definicion de main
async def main(fecha_hoy):

    print(f"\n>>> DESCARGANDO datos "f"para {fecha_hoy}")

    async with async_playwright() as p:

        new_page, browser, context = await carga_pagina(p,headless=True)
        try:

            print("decargando venta diaria...")
            df_venta=await ventas_descarga(new_page, fecha_hoy)

            print("descargando indicadores...")
            df_indicadores=await indicadores_descarga(new_page,fecha_hoy)

            print("descargando combos por Clciente")
            df_combos=await combos_por_cliente_descarga(new_page, fecha_hoy)

            print("ejecuntando pedidos pmm...")
            df_pedidos=await fullfillment_pedidos_descarga(new_page, fecha_hoy)

            print("descargando ito consolidado...")
            df_ito_conso=await ito_consolidado_descarga(new_page, fecha_hoy)

            print("descargando ito detallado...")
            df_ito_detalle=await ito_detallado_descarga(new_page, fecha_hoy)

            print("descargado pdv por agencia...")
            df_pdv_agencia=await pdv_agencia_descarga(new_page, fecha_hoy)

            print("descargando encustas de supervisores...")
            df_encuestas_supervisor=await encuestas_supervisor_descarga(new_page, fecha_hoy)

        finally:
            await browser.close()
    print("\n>>> DESCARGA de archivos completa.")
    
    #subida de datos 
    print("\n>>> CARGANDO datos en SQL...")
    lista_reportes=[
        {"carga_sql":ventas_carga_sql, "df":df_venta, "tabla":"POWERSTREET_Venta_Diaria"},
        {"carga_sql":indicadores_carga_sql, "df":df_indicadores, "tabla":"POWERSTREET_Seguimiento_Indicadores"},
        {"carga_sql":combos_por_cliente_carga_sql, "df":df_combos, "tabla":"POWERSTREET_Combos_Por_Cliente"},
        {"carga_sql":fullfillment_pedidos_carga_sql, "df":df_pedidos, "tabla":"POWERSTREET_Fullfillment_Pedidos_PMM"},
        {"carga_sql":ito_consolidado_carga_sql, "df":df_ito_conso, "tabla":"POWERSTREET_ITO_Consolidado"},
        {"carga_sql":ito_detallado_carga_sql, "df":df_ito_detalle, "tabla":"POWERSTREET_ITO_Detallado"},
        {"carga_sql":pdv_agencia_carga_sql, "df":df_pdv_agencia, "tabla":"POWERSTREET_PDV_PorAgencia"},
        {"carga_sql":encuestas_supervisor_carga_sql, "df":df_encuestas_supervisor, "tabla":"POWERSTREET_Encuestas_Supervisores"}
    ]
    for reporte in lista_reportes:
        carga_sql = reporte["carga_sql"]
        df = reporte["df"]
        tabla = reporte["tabla"]

        if df is None or df.empty:
            print(f"{tabla}: sin datos, continuando con el siguiente proceso...")
            continue

        print(f"Cargando {tabla} a SQL...")
        carga_sql(df=df,schema=schema,tabla=tabla)
        print("Datos cargados")

    

# obtener la ultima fecha con registros en sql
def obtener_ultima_fecha_sql(schema:str):

    with motor.begin() as conn:
        ultima_fecha_texto = text(f"""
            SELECT MIN(Fecha_Maxima) AS Menor_Fecha_Reciente
            FROM (
                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Venta_Diaria

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Seguimiento_Indicadores

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Combos_Por_Cliente

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Fullfillment_Pedidos_PMM

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_ITO_Consolidado

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_ITO_Detallado

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_PDV_PorAgencia

                UNION ALL

                SELECT MAX(Fecha) AS Fecha_Maxima
                FROM {schema}.POWERSTREET_Encuestas_Supervisores
                
            ) AS fechas_maximas;
        """)

        resultado = conn.execute(ultima_fecha_texto)

        return resultado.scalar()
    
#ejecución del programa principal
if __name__ == "__main__":

    ultima_fecha_sql = obtener_ultima_fecha_sql(schema=schema)

    print(
        f"La última fecha de registro en SQL fue el "
        f"{ultima_fecha_sql}"
    )

    fecha_hoy_obj = datetime.today().date()
    if (ultima_fecha_sql and fecha_hoy_obj > ultima_fecha_sql):

        print(
            f"Hoy es {fecha_hoy_obj} y el último registro "
            f"en SQL es del {ultima_fecha_sql}"
        )

        print(
            f"Se iniciará carga de datos desde "
            f"{ultima_fecha_sql} hasta {fecha_hoy_obj}"
        )

        current_date = ultima_fecha_sql

        while current_date <= fecha_hoy_obj:

            fecha_formateada = current_date.strftime(
                "%d-%m-%Y"
            )

            print(
                f"\nProcesando fecha: "
                f"{fecha_formateada}"
            )

            asyncio.run(
                main(fecha_formateada)
            )

            current_date += timedelta(days=1)

    else:

        print(
            "No hay fechas nuevas para procesar"
        )

        fecha_hoy_str = (
            fecha_hoy_obj.strftime("%d-%m-%Y")
        )

        asyncio.run(
            main(fecha_hoy_str)
        )