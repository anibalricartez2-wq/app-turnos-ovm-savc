import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema Control de Turnos", layout="wide")

# Diccionarios de traducción manual
DIAS_ES = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
MESES_ES = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
]

def check_password():
    if "password_correct" not in st.session_state:
        st.title("🔐 Acceso Restringido")
        st.text_input("Usuario", on_change=password_entered, key="username")
        st.text_input("Contraseña", type="password", on_change=password_entered, key="password")
        return False
    return st.session_state.get("password_correct", False)

def password_entered():
    if (st.session_state["username"] in st.secrets["passwords"] and 
        st.session_state["password"] == st.secrets["passwords"][st.session_state["username"]]):
        st.session_state["password_correct"] = True
    else:
        st.session_state["password_correct"] = False

if check_password():
    st.title("🗓️ Generador de Turnos - Operaciones")
    
    # --- SIDEBAR: CONFIGURACIÓN ---
    with st.sidebar:
        st.header("⚙️ Configuración")
        mes_nombre = st.selectbox("Seleccionar Mes", MESES_ES, index=datetime.now().month - 1)
        mes_nro = MESES_ES.index(mes_nombre) + 1
        anio = st.number_input("Año", value=2026)
        
        empleados = ["Sánchez", "García", "Barros", "Ricartez"]
        
        st.divider()
        st.header("🚫 Restricciones por Persona")
        config_per = {}
        
        for e in empleados:
            with st.expander(f"Opciones de {e}"):
                rango = st.date_input(f"Licencia Médica {e}", value=[], key=f"lic_{e}")
                dias_prohibidos = st.multiselect(f"No trabaja los días:", 
                                                 ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"],
                                                 key=f"sem_{e}")
                turno_evitar = st.selectbox(f"Evitar turno:", ["Ninguno", "Mañana (06-15)", "Tarde (15-24)"], key=f"t_ev_{e}")
                francos = st.multiselect(f"Francos fijos (nro día):", range(1, 32), key=f"f_{e}")

                fechas_lic = pd.date_range(start=rango[0], end=rango[1]).date if len(rango) == 2 else []
                map_dias = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}
                indices_dias = [map_dias[d] for d in dias_prohibidos]
                
                config_per[e] = {
                    "licencia": fechas_lic,
                    "dias_semana": indices_dias,
                    "turno_bloqueado": turno_evitar,
                    "francos_fijos": francos
                }

    # --- LÓGICA DE ASIGNACIÓN ---
    num_dias = calendar.monthrange(anio, mes_nro)[1]
    dias_mes = [datetime(anio, mes_nro, d) for d in range(1, num_dias + 1)]

    if st.button("🚀 GENERAR PLANILLA"):
        cronograma = []
        horas_acum = {e: 0 for e in empleados}
        quien_hizo_tarde_ayer = None

        for fecha_dt in dias_mes:
            idx_sem = fecha_dt.weekday()
            dia_nro = fecha_dt.day
            es_finde = idx_sem >= 5
            hs_valor = 18 if es_finde else 9
            
            fecha_str = f"{DIAS_ES[idx_sem]} {fecha_dt.strftime('%d/%m/%Y')}"
            
            turnos = ["Mañana (06-15)", "Tarde (15-24)"]
            asignados_hoy = []

            for t in turnos:
                candidatos = []
                for e in empleados:
                    lic = fecha_dt.date() in config_per[e]["licencia"]
                    dia_sem = idx_sem in config_per[e]["dias_semana"]
                    turno_off = t == config_per[e]["turno_bloqueado"]
                    franco = dia_nro in config_per[e]["francos_fijos"]
                    descanso = not (t == "Mañana (06-15)" and e == quien_hizo_tarde_ayer)
                    horas_ok = (horas_acum[e] + hs_valor) <= 160
                    ya_asignado = e in asignados_hoy
                    
                    if not any([lic, dia_sem, turno_off, franco]) and descanso and horas_ok and not ya_asignado:
                        candidatos.append(e)

                candidatos.sort(key=lambda x: (horas_acum[x], x))

                if candidatos:
                    elegido = candidatos[0]
                    cronograma.append({
                        "Fecha": fecha_str,
                        "Turno": t,
                        "Empleado": elegido,
                        "Hs": hs_valor
                    })
                    horas_acum[elegido] += hs_valor
                    asignados_hoy.append(elegido)
                    if t == "Tarde (15-24)": 
                        quien_hizo_tarde_ayer = elegido
                else:
                    cronograma.append({
                        "Fecha": fecha_str,
                        "Turno": t,
                        "Empleado": "⚠️ VACANTE",
                        "Hs": 0
                    })
                    if t == "Tarde (15-24)": 
                        quien_hizo_tarde_ayer = None

        # --- MOSTRAR RESULTADOS ---
        if cronograma:
            df = pd.DataFrame(cronograma)  # <--- Paréntesis cerrado correctamente
            st.subheader(f"📋 Calendario de Turnos - {mes_nombre} {anio}")
            
            df_cal = df.pivot(index='Fecha', columns='Turno', values='Empleado')
            df_cal.index = pd.Categorical(df_cal.index, categories=df['Fecha'].unique(), ordered=True)
            df_cal = df_cal.sort_index()
            
            st.table(df_cal.style.applymap(lambda v: 'background-color: #ffcccc' if v == "⚠️ VACANTE" else ''))

            st.divider()
            st.subheader("📊 Resumen de Horas (Tope 160hs)")
            cols = st.columns(4)
            for i, e in enumerate(empleados):
                h = horas_acum[e]
                cols[i].metric(e, f"{h} hs", f"{160-h} libres")
                cols[i].progress(min(h/160, 1.0))

            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Descargar Planilla para Excel", csv, f"turnos_{mes_nombre}.csv", "text/csv")
    else:
        st.warning("👈 Configurá las restricciones en el menú lateral y dale a 'Generar'.")
