#----------------------------------
#LIBRERIAS
#----------------------------------
import unicodedata
import re

#----------------------------------
#FUNCION NORMALIZADORA DE TEXTO
#----------------------------------
def normalizar_texto(s):
    s = str(s)
    # Quitar acentos
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # Mayúsculas
    s = s.upper()
    # Reemplazar saltos, tabs, espacios raros
    s = re.sub(r'[\r\n\t]+', ' ', s)
    # Quitar espacios múltiples
    s = re.sub(r'\s+', ' ', s)
    # Quitar espacios al inicio y fin
    s = s.strip()
    return s      