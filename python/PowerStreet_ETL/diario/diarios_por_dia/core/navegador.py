#------------------
#LIBRERIAS
#---------------------
import base64
import cv2
import numpy as np
from playwright.async_api import TimeoutError as PlaywrightTimeoutError


from paddleocr import PaddleOCR

#--------------------------
#IMPORTS
#-------------------------
from configuraciones.parametros import (
    usuariops,
    contraseñaps,
    urlpowerstreet
)

#--------------------------------
#proceso de carga de página inical de PS
#la cual, se reutilza en todos los  procesos de reportes
#----------------------------------
async def carga_pagina(p, headless=True):
    #bucle pequeño para el intento de carga de página en caso de reseteos de conexión
    async def safe_goto(page, url, retries=3):
        for i in range(retries):
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=180000)
                return#exito, rompe bucle
            except Exception as e:
                print(f"Fallo de carga de página en elintento {i}")
                await page.wait_for_timeout(15000)#espera 15 segundos antes de volver a intentar
        raise Exception("No se pudo cargar la página")
    
    browser = await p.chromium.launch(headless=headless)
    #contexto del navegador usado, se trata de dejar una huella de navegadores convencionales al hacer conexión
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120 Safari/537.36",
        viewport={"width": 1366, "height": 768},
        locale="es-MX",)
    page = await context.new_page()

    await safe_goto(page, url="https://client.powerstreet.cloud")
    await page.wait_for_load_state("networkidle", timeout=240000)
    print("Página cargada!!!")

    # credenciales
    await page.fill('input[name="user"]', usuariops)
    await page.fill('input[name="pass"]', contraseñaps)
    await page.click('input[value="iniciar sesión"]')

    # Esperar hasta 10 segundos a que aparezca algún modal
    modal = page.locator('[role="dialog"]')
    try:
        await modal.first.wait_for(state="visible",timeout=12_000)
        print("Modal detectado, identificando tipo...")
        # Dar tiempo para que termine de renderizarse
        await page.wait_for_timeout(1500)
        # CASO 1: CAPTCHA
        dialog = page.locator(
            '[role="dialog"][aria-describedby="captcha-dialog"]'
        )
        if await dialog.is_visible():
            print("CAPTCHA detectado, resolviendo...")
            ocr = PaddleOCR(use_textline_orientation=False,lang='en')
            while await dialog.is_visible():
                print("resolviendo captcha")
                image = await page.query_selector('#captcha-img')#selección de la imagen del captcha
                if image:
                    print("imagen encontrada")
                    await page.locator('#captcha-img').get_attribute('src')
                    captcha_img = page.locator('#captcha-img')
                    await captcha_img.wait_for(state="visible")
                    
                    # Descargar imagen desde el navegador
                    img_base64 = await captcha_img.evaluate("""
                        img => {
                            const canvas = document.createElement('canvas');
                            canvas.width = img.naturalWidth;
                            canvas.height = img.naturalHeight;
                            const ctx = canvas.getContext('2d');
                            ctx.drawImage(img, 0, 0);
                            return canvas.toDataURL('image/png').split(',')[1];
                        }
                        """)
                    img_bytes = base64.b64decode(img_base64)
                    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    if img is None:
                        print("Imagen vacía")
                        continue
                    print("Captcha descargado correctamente")
                    # limpieza de la imagen
                    # Convierte la imagen a escala de grises
                    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    # Aplicar un umbral para obtener solo los tonos de negro (y gris)
                    _, imagen_umbral = cv2.threshold(
                        gray_img, 150, 255, cv2.THRESH_BINARY_INV)
                    # Crear una imagen en blanco
                    imagen_blanca = np.ones_like(img) * 255
                    # Aplicar la máscara de umbral a la imagen original
                    resultado = cv2.bitwise_and(img, img, mask=imagen_umbral)
                    # Combinar la imagen original con la imagen en blanco usando la máscara inversa
                    imagen_final = cv2.add(imagen_blanca, resultado, mask=cv2.bitwise_not(imagen_umbral))
                    # Aumentar el contraste en un 300%
                    alpha = 4.0  # Factor de contraste (1.0 + 3.0 = 4.0 para +300%)
                    imagen_contraste = cv2.convertScaleAbs(imagen_final, alpha=alpha, beta=0)
                    # Aumentar el brillo en un 150%
                    beta = 150  # Valor de brillo (150 para +150%)
                    imagen_brillo = cv2.convertScaleAbs(imagen_contraste, alpha=1.0, beta=beta)
                    resultado = ocr.ocr(imagen_brillo)
                    if resultado and resultado[0]: #SI EL RESULTADO NO ESTÁ VACIO
                        captchaResult = "".join([linea[1][0] for linea in resultado[0]])
                        print(captchaResult)
                        await page.locator('input[name="captcha-text"]').wait_for(state="visible",timeout=60000)
                        await page.fill('input[name="captcha-text"]', captchaResult)
                        modal = page.locator('[role="dialog"]')#adecuar 
                        await modal.locator('button:has-text("Validar")').click()
                        await page.wait_for_timeout(1500)#esperar 1.5 segundos para que el programa alcanze a hacer la validacion del while    
                    else:
                        print("no se encontró ningun texto en el captcha, volviendo a intentar")
                        await page.locator('#btn-refresh-captcha').click()
        # CASO 2: Centro de notificaciones
        elif await page.locator('[role="dialog"][aria-describedby="ui-id-5"]').is_visible():
            print("Centro de notificaciones detectado, cerrando...")
            await page.locator('[role="dialog"][aria-describedby="ui-id-5"]').locator('.ui-dialog-titlebar-close').click()

    except PlaywrightTimeoutError:
        print("No apareció ningún modal durante los 12 segundos.")
        print("Continuando sin modal...")

    
    #continuación después de resolver el captcha
    #abrir enterprise 
    async with page.expect_popup() as popup_info:
        await page.click('text="Enterprise"')
        
    new_page = await popup_info.value  # ahora sí tenemos la nueva pestaña con certeza
    await new_page.wait_for_load_state("networkidle", timeout=240000)
    print("🔗 URL activa:", new_page.url)
    
    #si hay sesiones abiertas se quitan, sino se continua al menú principal
    boton = await new_page.query_selector('.p-continuebutton')
    if  boton:
        print("sesiones abiertas, cerrandolas")
        await boton.click()
        await new_page.wait_for_load_state("networkidle", timeout=240000)#espera a cargar el menú principal
    else:
        print("Sin sesiones abiertas, continuando")
    
    #Ya en el menú principal
    #cambiar  menú lateral a barra superior
    await new_page.click('[title="alternar barra de menú"]')
    
    return new_page, browser, context
