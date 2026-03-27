import streamlit as st
import pandas as pd
import calendar
from datetime import datetime

st.set_page_config(page_title="Sistema de Turnos 24/7", layout="wide")

# --- ESTILO PERSONALIZADO ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

st.title("📅 Gestor de Turnos: 06-15 / 15-24")
st.info("Reglas: Fines de semana computan x2 (18hs). Máximo 160hs mensuales por trabajador.")

# --- SIDEBAR: CONFIGURACIÓN Y LICENCIAS ---
with st.sidebar:
    st.header("⚙️ Configuración")
    mes = st.selectbox("Mes", range(1, 13), index=datetime.now().month - 1)
    anio = st.number_input("Año", value=2026)
    
    nombres_input = st.text_input("Personal (4 trabajadores)", "Acosta, Fuentes, Ricartez, Wiertz")
    empleados = [e.strip() for e in nombres_input.split(",")]

    st.divider()
    st.header("🏥 Licencias y Francos")
    licencias = {}
    for e in empleados:
        st.subheader(f"Configurar {e}")
        rango = st.date_input(f"Rango Licencia {e}", value=[], key=f"lic_{e}")
        fijos = st.multiselect(f"Días Libres {e}", range(1, 32), key=f"dias_{e}")
        
        # Procesar fechas de licencia
        fechas_licencia = []
        if len(rango) == 2:
            fechas_licencia = pd.date_range(start=rango[0], end=rango[1]).date
        licencias[e] = {"rango": fechas_licencia, "fijos": fijos}

# --- LÓGICA DE GENERACIÓN ---
num_dias = calendar.monthrange(anio, mes)[1]
dias_mes = [datetime(anio, mes, d) for d in range(1, num_dias + 1)]

if st.button("🚀 GENERAR CRONOGRAMA Y CALENDARIO"):
    cronograma = []
    horas_acum = {e: 0 for e in empleados}
    quien_hizo_tarde_ayer = None

    for fecha_dt in dias_mes:
        dia_nro = fecha_dt.day
        fecha_date = fecha_dt.date()
        es_finde = fecha_dt.weekday() >= 5
        hs_turno = 18 if es_finde else 9
        
        turnos = ["Mañana (06-15)", "Tarde (15-24)"]
        asignados_hoy = []

        for t in turnos:
            candidatos = []
            for e in empleados:
                # Validaciones
                esta_de_licencia = fecha_date in licencias[e]["rango"]
                tiene_franco_fijo = dia_nro in licencias[e]["fijos"]
                descanso_ok = not (t == "Mañana (06-15)" and e == quien_hizo_tarde_ayer)
                tiene_horas = (horas_acum[e] + hs_turno) <= 160
                
                if not esta_de_licencia and not tiene_franco_fijo and descanso_ok and tiene_horas and e not in asignados_hoy:
                    candidatos.append(e)

            # Prioridad al que menos horas tiene
            candidatos.sort(key=lambda x: horas_acum[x])

            if candidatos:
                elegido = candidatos[0]
                cronograma.append({"Día": dia_nro, "Fecha": fecha_dt.strftime("%a %d"), "Turno": t, "Empleado": elegido})
                horas_acum[elegido] += hs_turno
                asignados_hoy.append(elegido)
                if t == "Tarde (15-24)": quien_hizo_tarde_ayer = elegido
            else:
                cronograma.append({"Día": dia_nro, "Fecha": fecha_dt.strftime("%a %d"), "Turno": t, "Empleado": "⚠️ VACANTE"})
                if t == "Tarde (15-24)": quien_hizo_tarde_ayer = None

    # --- RENDERIZADO DE RESULTADOS ---
    df_raw = pd.DataFrame(cronograma)

    # 1. Crear el Calendario Visual (Pivot Table)
    st.subheader("🗓️ Vista de Calendario Mensual")
    df_calendario = df_raw.pivot(index='Fecha', columns='Turno', values='Empleado')
    
    # Aplicar colores para que se vea profesional
    def highlight_vacante(s):
        return ['background-color: #ffcccc' if v == "⚠️ VACANTE" else '' for v in s]
    
    st.table(df_calendario.style.apply(highlight_vacante))

    # 2. Resumen de Horas (Métricas)
    st.divider()
    st.subheader("📊 Control de Carga Horaria (Tope 160hs)")
    m_cols = st.columns(len(empleados))
    for i, e in enumerate(empleados):
        total = horas_acum[e]
        m_cols[i].metric(label=e, value=f"{total} hs", delta=f"{160-total} disp.", delta_color="normal")

    # 3. Descarga
    st.divider()
    csv = df_raw.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 Descargar Planilla Completa (CSV/Excel)", csv, f"turnos_{mes}_{anio}.csv", "text/csv")

else:
    st.warning("Configurá las licencias en el panel izquierdo y presioná el botón para generar.")
