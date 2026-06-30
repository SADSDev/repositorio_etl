#----------------------------------------
#LIBRERIAS
#----------------------------------------
import asyncio
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

#----------------------------------------
#IMPORTS
#----------------------------------------
#configuraciones
from configuraciones.conexion_sql import motor
import configuraciones.entorno
#parametros
from configuraciones.parametros import (usuariops, contraseñaps)
#procesos
from core.navegador import carga_pagina
from procesos.universo_clientes import universo
from procesos.libros import libros
#-----------------------------------
#PROCESO
#-----------------------------------

async def main(fecha_hoy):
    print(f"\n>>> Ejecutando procesos para: {fecha_hoy}")
    async with async_playwright() as p:
        #iniciar sesion 1 sola vez por día de proceso
        new_page, browser, context = await carga_pagina(p,headless=False)
        try:
            print("ejecutando libros...")
            await libros(new_page)
            
            print("ejecutando UX...")
            await universo(new_page, fecha_hoy)
        finally:
            await browser.close()


if __name__ == "__main__":
     # Ejecutar solo para hoy
    fecha_hoy_obj = datetime.today().date()
    fecha_hoy_str = fecha_hoy_obj.strftime("%d-%m-%Y")
    asyncio.run(main(fecha_hoy_str))