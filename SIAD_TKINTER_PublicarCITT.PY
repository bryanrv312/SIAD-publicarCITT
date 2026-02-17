import tkinter as tk
from tkinter import filedialog, scrolledtext
import pandas as pd
import os
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager
#import getpass

# Crear ventana principal
ventana = tk.Tk()
ventana.title("Publicar CITT por NIT")
ventana.geometry("800x600")

# logs en consola
consola = scrolledtext.ScrolledText(ventana, width=100, height=30)
consola.pack(pady=10)

archivo_excel = None
resultados = []

def log(mensaje):
    consola.insert(tk.END, mensaje + "\n")
    consola.see(tk.END)
    ventana.update()

def seleccionar_archivo():
    global archivo_excel
    archivo_excel = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx")])
    log(f"📁 Archivo seleccionado: {archivo_excel}")

def transformar_citt(citt_original):
    partes = citt_original.split("-")
    if len(partes) != 4 or not partes[2].startswith("00"):
        raise ValueError(f"CITT inválido o inesperado: {citt_original}")
    citt_transformado = f"{partes[0]}{partes[1]}{partes[2][2:]}{partes[3]}"
    if len(citt_transformado) != 12:
        raise ValueError(f"CITT transformado no tiene 12 caracteres: {citt_transformado}")
    return citt_transformado


# --- NUEVO: Ventana emergente para credenciales ---
def pedir_credenciales():
    # Crear ventana secundaria
    login_win = tk.Toplevel(ventana)
    login_win.title("Credenciales de acceso")
    login_win.geometry("300x150")

    tk.Label(login_win, text="Usuario:").pack(pady=5)
    entry_usuario = tk.Entry(login_win, width=25)
    entry_usuario.pack(pady=5)

    tk.Label(login_win, text="Contraseña:").pack(pady=5)
    entry_password = tk.Entry(login_win, width=25, show="*")
    entry_password.pack(pady=5)

    def confirmar():
        usuario = entry_usuario.get()
        password = entry_password.get()
        login_win.destroy()  # cerrar ventana emergente
        publicar_citt(usuario, password)  # ejecutar el resto con credenciales

    tk.Button(login_win, text="Aceptar", command=confirmar).pack(pady=10)


def publicar_citt(usuario, password):
    if not archivo_excel:
        log("⚠️ No se ha seleccionado ningún archivo.")
        return

    df = pd.read_excel(archivo_excel)
    log(f"📊 NITs encontrados: {len(df)}")

    log("🌐 Iniciando navegador...")
    driver_path = ChromeDriverManager().install()
    service = Service(driver_path)
    driver = webdriver.Chrome(service=service)
    driver.maximize_window()
    driver.get("https://ww10.essalud.gob.pe/sgfa/index.php")

    # Login
    # driver.find_element(By.XPATH, '//*[@id="user"]').send_keys("MY-USER")
    # driver.find_element(By.XPATH, '//*[@id="pass"]').send_keys("MY-PASS")
    # driver.find_element(By.XPATH, '//*[@id="aceptoIngresar"]').click()
    # WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
    # driver.switch_to.window(driver.window_handles[-1])

    # usuario = entry_usuario.get()
    # password = entry_password.get()
    # Login 
    driver.find_element(By.XPATH, '//*[@id="user"]').send_keys(usuario) 
    driver.find_element(By.XPATH, '//*[@id="pass"]').send_keys(password)
    driver.find_element(By.XPATH, '//*[@id="aceptoIngresar"]').click()
    WebDriverWait(driver, 10).until(EC.number_of_windows_to_be(2))
    driver.switch_to.window(driver.window_handles[-1])

    for index, row in df.iterrows():
        nit = row["NIT"]
        citt = str(row["CITT"])
        log(f"🔍 Procesando NIT: {nit}")

        partes = nit.split("-")
        if len(partes) != 3:
            log(f"❌ NIT inválido: {nit}")
            resultados.append({"NIT": nit, "CITT Original": citt, "Estado": "Formato inválido"})
            continue

        area, anio, correlativo = partes
        intentos = 0
        pasos_validos = 0

        while pasos_validos == 0 and intentos < 10:
            intentos += 1
            log(f"🔁 Intento {intentos} para NIT {nit}")
            if intentos == 5:
                driver.refresh()
                time.sleep(3)

            try:
                WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="tramite_area"]'))).clear()
                driver.find_element(By.XPATH, '//*[@id="tramite_area"]').send_keys(area)
                driver.find_element(By.XPATH, '//*[@id="tramite_anio"]').clear()
                driver.find_element(By.XPATH, '//*[@id="tramite_anio"]').send_keys(anio)
                driver.find_element(By.XPATH, '//*[@id="tramite_correlativo"]').clear()
                driver.find_element(By.XPATH, '//*[@id="tramite_correlativo"]').send_keys(correlativo)
                Select(driver.find_element(By.XPATH, '//*[@id="filtroderiva"]')).select_by_visible_text("Derivado")
                driver.find_element(By.XPATH, '//*[@id="btnIr"]').click()

                xpath_em = f'//em[contains(text(), "{area}-") and contains(text(), "{anio}-NIT-") and contains(text(), "{correlativo}")]'
                elemento_em = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, xpath_em)))
                elemento_em.click()

                boton_mas = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="TablaDerivacion_1"]//img[contains(@src, "create.gif")]')))
                boton_mas.click()

                campo = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="to_2"]')))
                campo.clear()
                campo.send_keys("VISUALIZACION DEL CITT  ")
                time.sleep(0.5)
                campo.send_keys(Keys.BACKSPACE)

                sugerencia_visible = False
                for intento_sug in range(3):
                    try:
                        sugerencia = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, '//*[@id="search_suggest_2_to"]/div')))
                        sugerencia.click()
                        sugerencia_visible = True
                        log(f"✅ Sugerencia seleccionada en intento {intento_sug + 1}")
                        break
                    except:
                        campo.clear()
                        campo.send_keys("VISUALIZACION DEL CI")
                        time.sleep(0.5)
                        campo.send_keys("TT")
                        time.sleep(1)

                if not sugerencia_visible:
                    log(f"❌ No se pudo seleccionar la sugerencia para NIT {nit}")
                    resultados.append({"NIT": nit, "CITT Original": citt, "Estado": "Sin sugerencia"})
                    continue

                sumilla_input = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, '//*[@id="sumilla_2"]')))
                sumilla_input.clear()
                citt_transformado = transformar_citt(citt)
                sumilla_input.send_keys(f"[{citt_transformado}]")
                log(f"🧪 CITT publicado como: [{citt_transformado}]")

                input("⏸️ Pausa: Presiona Enter para continuar...")

                driver.find_element(By.XPATH, '//*[@id="Guardar"]').click()
                WebDriverWait(driver, 5).until(EC.alert_is_present())
                driver.switch_to.alert.accept()

                resultados.append({
                    "NIT": nit,
                    "CITT Original": citt,
                    "CITT Publicado": citt_transformado,
                    "Estado": "OK"
                })
                pasos_validos = 1

            except Exception as e:
                log(f"❌ Error en intento {intentos} para NIT {nit}: {e}")
                if intentos == 3:
                    resultados.append({
                        "NIT": nit,
                        "CITT Original": citt,
                        "CITT Publicado": "",
                        "Estado": "No publicado",
                        "Motivo": str(e)
                    })

    df_resultados = pd.DataFrame(resultados)
    nombre_base = os.path.splitext(os.path.basename(archivo_excel))[0]
    nombre_resultado = f"{nombre_base}_RES_CITT.xlsx"
    contador = 1
    while os.path.exists(nombre_resultado):
        nombre_resultado = f"{nombre_base}_RES_CITT({contador}).xlsx"
        contador += 1

    df_resultados.to_excel(nombre_resultado, index=False)
    log(f"📁 Resultados exportados a '{nombre_resultado}'")
    try:
        os.startfile(nombre_resultado)
    except Exception as e:
        log(f"⚠️ No se pudo abrir el archivo automáticamente: {e}")

    driver.quit()

# Botones
btn_seleccionar = tk.Button(ventana, text="📤 Seleccionar Excel", command=seleccionar_archivo)
btn_seleccionar.pack(pady=5)

# btn_publicar = tk.Button(ventana, text="🚀 Publicar CITT", command=publicar_citt)
btn_publicar = tk.Button(ventana, text="🚀 Publicar CITT", command=pedir_credenciales)
btn_publicar.pack(pady=5)

# --- NUEVO: Campos de usuario y contraseña ---
# frame_login = tk.Frame(ventana)
# frame_login.pack(pady=5)

# lbl_usuario = tk.Label(frame_login, text="Usuario:")
# lbl_usuario.grid(row=0, column=0, padx=5, pady=5)
# entry_usuario = tk.Entry(frame_login, width=30)
# entry_usuario.grid(row=0, column=1, padx=5, pady=5)

# lbl_password = tk.Label(frame_login, text="Contraseña:")
# lbl_password.grid(row=1, column=0, padx=5, pady=5)
# entry_password = tk.Entry(frame_login, width=30, show="*")
# entry_password.grid(row=1, column=1, padx=5, pady=5)

ventana.mainloop()
