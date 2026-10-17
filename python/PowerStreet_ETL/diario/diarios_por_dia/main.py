#----------------------------------------
#LIBRERIAS
#----------------------------------------
import asyncio
from datetime import datetime


#----------------------------------------
#IMPORTS
#----------------------------------------
#configuraciones
import configuraciones.entorno
from playwright.async_api import async_playwright

from configuraciones.parametros import schema
from core.navegador import carga_pagina

from procesos.libros import (
    libros_descarga,
    libros_carga_sql
)

from procesos.universo_clientes import (
    universo_descarga,
    universo_carga_sql
)
#-----------------------------------
#PROCESO
#-----------------------------------

async def main(fecha_hoy):
    #descarga de datos de PowerStreet
    print(f"\n>>> DESCARGANDO datos "f"para {fecha_hoy}")
    async with async_playwright() as p:
        new_page, browser, context = await carga_pagina(p,headless=True)
        try:

            print("Descargando Libro de rutas...")
            df_libros = await libros_descarga(new_page,fecha_hoy)

            print("Descargando Universo de Clientes...")
            df_universo = await universo_descarga(new_page,fecha_hoy)
        finally:
            await browser.close()
    print("\n>>> DESCARGA de archivos completa.")

    #carga de datos a SQL
    print("\n>>> CARGANDO datos en SQL...")
    libros_carga_sql(df=df_libros,schema=schema,tabla="POWERSTREET_Libros")
    universo_carga_sql(df=df_universo,schema=schema,tabla="POWERSTREET_Universo_Clientes")
    print("\n>>> CARGA terminada correctamente.")


if __name__ == "__main__":
    fecha_hoy = datetime.today().strftime("%d-%m-%Y")
    asyncio.run(main(fecha_hoy))