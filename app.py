import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Privado de Turnos", layout="wide")

# --- 1. FUNCIÓN DE SEGURIDAD (LOGIN) ---
def check_password():
    """Devuelve True si el usuario ingresó credenciales válidas en Secrets."""
    def password_entered():
        if (
            st.session_state["username"] in st.secrets["passwords"]
            and st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        st.error("❌ Credenciales incorrectas.")
        return False
    else:
        return True

# --- INICIO DE LA APLICACIÓN SI EL LOGIN ES CORRECTO ---
if check_password():
    
    st.title("🗓️ Generador de Turnos: Operaciones")
    st.markdown("Configuración: **06-15 / 15-24** | Fines de semana **Dobles** | Máximo **160hs**")

    # --- SIDEBAR: PARÁMETROS Y LICENCIAS ---
    with st.sidebar:
        st.header("⚙️ Panel de Control")
        mes = st.selectbox("Mes a generar", range(1, 13), index=datetime.now().month - 1)
        anio = st.number_input("Año", value=2026)
        
        # Nombres de tus trabajadores
        nombres_defecto = "Acosta, Fuentes, Ricartez, Wiertz"
        nombres_input = st.text_input("Personal (4 nombres)", nombres_defecto)
        empleados = [e.strip() for e in nombres_input.split(",")]

        st.divider()
        st.header("🏥 Licencias y Francos")
        restricciones_data = {}
        
        for e in empleados:
            with st.expander(f"Configurar {e}"):
                # Licencia médica (Rango)
                rango = st.date_input(f"Licencia Médica - {e}", value=[], key=f"lic_{e}")
                # Días libres específicos
                fijos = st.multiselect(f"Francos solicitados - {e}", range(1, 32), key=f"fijos_{e}")
                
                fechas_licencia = []
                if len(rango) == 2:
                    fechas_licencia = pd.date_range(start=rango[0], end=rango[1]).date
                
                restricciones_data[e] = {"licencia": fechas_licencia, "francos": fijos}

    # --- LÓGICA DE ASIGNACIÓN ---
    num_dias = calendar.monthrange(anio, mes)[1]
    dias_mes = [datetime(anio, mes, d) for d in range(1, num_dias + 1)]

    if st.button("🚀 GENERAR LISTA Y CALENDARIO"):
        cronograma = []
        horas_acum = {e: 0 for e in empleados}
        quien_hizo_tarde_ayer = None

        for fecha_dt in dias_mes:
            dia_nro = fecha_dt.day
            fecha_date = fecha_dt.date()
            es_finde = fecha_dt.weekday() >= 5 # Sábado o Domingo
            hs_valor = 18 if es_finde else 9 # Cómputo doble en finde
            
            turnos_hoy = ["Mañana (06-15)", "Tarde (15-24)"]
            asignados_hoy = []

            for t in turnos_hoy:
                # Filtrar candidatos aptos
                candidatos = []
                for e in empleados:
                    # Reglas de negocio
                    en_licencia = fecha_date in restricciones_data[e]["licencia"]
                    en_franco = dia_nro in restricciones_data[e]["francos"]
                    descanso_minimo = not (t == "Mañana (06-15)" and e == quien_hizo_tarde_ayer)
                    dentro_de_horas = (horas_acum[e] + hs_valor) <= 160
                    ya_asignado = e in asignados_hoy

                    if not en_licencia and not en_franco and descanso_minimo and dentro_de_horas and not ya_asignado:
                        candidatos.append(e)

                # Priorizar al que tiene menos horas para que sea justo
                candidatos.sort(key=lambda x: horas_acum[x])

                if candidatos:
                    elegido = candidatos[0]
                    cronograma.append({
                        "Día": dia_nro, 
                        "Fecha": fecha_dt.strftime("%a %d"), 
                        "Turno": t, 
                        "Empleado": elegido,
                        "Horas": hs_valor
                    })
                    horas_acum[elegido] += hs_valor
                    asignados_hoy.append(elegido)
                    if t == "Tarde (15-24)": quien_hizo_tarde_ayer = elegido
                else:
                    cronograma.append({
                        "Día": dia_nro, 
                        "Fecha": fecha_dt.strftime("%a %d"), 
                        "Turno": t, 
                        "Empleado": "⚠️ VACANTE",
                        "Horas": 0
                    })
                    if t == "Tarde (15-24)": quien_hizo_tarde_ayer = None

        # --- MOSTRAR RESULTADOS ---
        df_resultados = pd.DataFrame(cronograma)

        # 1. Calendario Visual
        st.subheader("🗓️ Grilla Mensual")
        df_cal = df_resultados.pivot(index='Fecha', columns='Turno', values='Empleado')
        
        def estilo_vacante(v):
            return 'background-color: #ffcccc' if v == "⚠️ VACANTE" else ''
        
        st.table(df_cal.style.applymap(estilo_vacante))

        # 2. Resumen de Horas
        st.divider()
        st.subheader("📊 Control de 160 Horas Mensuales")
        cols = st.columns(len(empleados))
        for i, e in enumerate(empleados):
            hs = horas_acum[e]
            cols[i].metric(label=e, value=f"{hs} hs", delta=f"{160-hs} disp.")
            cols[i].progress(min(hs/160, 1.0))

        # 3. Descarga para Excel
        st.divider()
        csv = df_resultados.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📥 Descargar Planilla para Excel", csv, f"turnos_{mes}_{anio}.csv", "text/csv")

    else:
        st.warning("👈 Configurá licencias en el menú lateral y dale a 'Generar'.")

# --- RECORDATORIO FINAL ---
# No olvides configurar tus usuarios y contraseñas en Streamlit Cloud:
# [passwords]
# "admin" = "tu_clave"
