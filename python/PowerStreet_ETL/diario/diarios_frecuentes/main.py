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
import configuraciones.entorno
from core.navegador import carga_pagina
from procesos.db_cliente import dbcliente
from procesos.ventas_diarias import ventas
from procesos.seguimiento_indicadores import indicadores
from procesos.tiempos_y_movimientos import tiempos
from procesos.cp import cp
from procesos.combos import combos
from procesos.compos_por_cliente import combos_por_cliente
from procesos.fullfillment_pedidos_pmm import fullfillment_pedidos
from procesos.ito_consolidado import ito_consolidado
from procesos.ito_detallado import ito_detallado
#-----------------------------------
#PROCESO
#-----------------------------------

#definicion de main
async def main(fecha_hoy):

    print(f"\n>>> Ejecutando procesos para: {fecha_hoy}")

    async with async_playwright() as p:

        new_page, browser, context = await carga_pagina(
            p,
            headless=True
        )

        try:

            print("ejecutando dbcliente...")
            await dbcliente(new_page, fecha_hoy)

            print("ejecutando venta diaria...")
            await ventas(new_page, fecha_hoy)

            print("ejecutando indicadores...")
            await indicadores(new_page,fecha_hoy)

            #print("ejecutando tiempos...")
            #await tiempos(new_page, fecha_hoy)

            #print("ejecutando 1c1p...")
            #await cp(new_page, fecha_hoy)

            print("ejecutando combos por Clciente")
            await combos_por_cliente(new_page, fecha_hoy)

            print("ejecutando combos...")
            await combos(new_page, fecha_hoy)

            print("ejecuntando pedidos pmm...")
            await fullfillment_pedidos(new_page, fecha_hoy)

            print("ejecutando ito consolidado...")
            await ito_consolidado(new_page, fecha_hoy)

            print("ejecutando ito detallado...")
            await ito_detallado(new_page, fecha_hoy)
        finally:

            await browser.close()

#obtener la ultima fecha con registros en sql
def obtener_ultima_fecha_sql():

    with motor.begin() as conn:

        ultima_fecha_texto = text("""
            SELECT MIN(Fecha_Maxima) AS Menor_Fecha_Reciente
            FROM (
                SELECT MAX(Fecha) AS Fecha_Maxima FROM PowerStreet.DB_Cliente
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.Venta_Diaria
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.Seguimiento_Indicadores
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.[1c1p]
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.Combos
                UNION ALL
                SELECT MAX(Fecha_visita) FROM PowerStreet.Tiempos_y_Mov
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.Fullfillment_Pedidos_PMM
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.ITO_Consolidado
                UNION ALL
                SELECT MAX(Fecha) FROM PowerStreet.ITO_Detallado
            ) AS fechas_maximas
        """)

        resultado = conn.execute(
            ultima_fecha_texto
        )

        return resultado.scalar()
    
#ejecución del programa principal
if __name__ == "__main__":

    ultima_fecha_sql = obtener_ultima_fecha_sql()

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