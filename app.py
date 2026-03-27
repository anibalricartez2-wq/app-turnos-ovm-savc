import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Turnos SAVC", layout="wide")

# --- FUNCIÓN DE LOGIN ---
def login():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False
    if not st.session_state["autenticado"]:
        st.title("🔐 Acceso al Sistema de Turnos")
        user = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        if st.button("Ingresar"):
            if "passwords" in st.secrets:
                if user in st.secrets["passwords"] and password == st.secrets["passwords"][user]:
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos")
            else:
                st.error("Error: Configurá 'Secrets' en Streamlit Cloud")
        return False
    return True

# --- TRADUCCIONES ---
DIAS_ES = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

# --- FUNCIÓN PDF ---
def crear_pdf(df_final, mes_nombre, anio):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    titulo = f"CRONOGRAMA DE TURNOS - {mes_nombre.upper()} {anio}"
    pdf.cell(190, 10, titulo.encode('latin-1', 'replace').decode('latin-1'), ln=True, align="C")
    pdf.ln(10)
    
    pdf.set_font("Arial", "B", 10)
    pdf.set_fill_color(0, 51, 102)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(50, 10, "FECHA", border=1, align="C", fill=True)
    pdf.cell(70, 10, "MANANA (06-15)", border=1, align="C", fill=True)
    pdf.cell(70, 10, "TARDE (15-24)", border=1, align="C", fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(0, 0, 0)
    fill = False
    for _, row in df_final.iterrows():
        pdf.set_fill_color(240, 240, 240)
        f_t = str(row['Fecha']).encode('latin-1', 'replace').decode('latin-1')
        m_t = str(row['Mañana (06-15)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        t_t = str(row['Tarde (15-24)']).replace("[VACANTE]", "VACANTE").encode('latin-1', 'replace').decode('latin-1')
        pdf.cell(50, 8, f_t, border=1, align="C", fill=fill)
        pdf.cell(70, 8, m_t, border=1, align="C", fill=fill)
        pdf.cell(70, 8, t_t, border=1, align="C", fill=fill)
        pdf.ln()
        fill = not fill
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- CUERPO PRINCIPAL ---
if login():
    st.sidebar.header("⚙️ Configuración")
    mes_nombre = st.sidebar.selectbox("Seleccionar Mes", MESES_ES, index=datetime.now().month - 1)
    mes_nro = MESES_ES.index(mes_nombre) + 1
    anio = st.sidebar.number_input("Año", value=2026)
    
    empleados = ["Sánchez", "García", "Barros", "Ricartez"]
    
    # Límite mensual y estimado semanal (160hs / 4 semanas = 40hs aprox)
    LIMITE_MENSUAL = 160
    CUOTA_SEMANAL = 45 # Un pequeño margen extra por si hay muchos feriados/findes
    
    config_per = {}
    for e in empleados:
        with st.sidebar.expander(f"Restricciones {e}"):
            rango = st.date_input(f"Licencia {e}", value=[], key=f"l_{e}")
            dias_p = st.multiselect(f"No trabaja:", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"], key=f"s_{e}")
            t_ev = st.selectbox(f"Evitar:", ["Ninguno", "Mañana (06-15)", "Tarde (15-24)"], key=f"t_{e}")
            f_fijos = st.multiselect(f"Francos fijos:", range(1, 32), key=f"f_{e}")

            fechas_l = []
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                fechas_l = pd.date_range(start=rango[0], end=rango[1]).date
            
            map_d = {"Lunes":0, "Martes":1, "Miércoles":2, "Jueves":3, "Viernes":4, "Sábado":5, "Domingo":6}
            config_per[e] = {"lic": fechas_l, "sem": [map_d[d] for d in dias_p], "t_bloq": t_ev, "f_fijos": f_fijos}

    if st.button("🚀 GENERAR PLANILLA BALANCEADA"):
        num_dias = calendar.monthrange(anio, mes_nro)[1]
        cronograma = []
        hs_totales = {e: 0 for e in empleados}
        hs_semanales = {e: 0 for e in empleados}
        tarde_ayer = None
        semana_actual = None

        for d in range(1, num_dias + 1):
            f_dt = datetime(anio, mes_nro, d)
            idx_s = f_dt.weekday()
            
            # Detectar cambio de semana (ISO week) para resetear cuota semanal
            iso_semana = f_dt.isocalendar()[1]
            if iso_semana != semana_actual:
                hs_semanales = {e: 0 for e in empleados} # Reset cuota semanal
                semana_actual = iso_semana

            hs_v = 18 if idx_s >= 5 else 9
            f_str = f"{DIAS_ES[idx_s]} {f_dt.strftime('%d/%m/%Y')}"
            
            hoy_asignados = []
            for t in ["Mañana (06-15)", "Tarde (15-24)"]:
                cand = []
                for e in empleados:
                    en_lic = f_dt.date() in config_per[e]["lic"]
                    sem_bloq = idx_s in config_per[e]["sem"]
                    t_bloq = t == config_per[e]["t_bloq"]
                    franco = d in config_per[e]["f_fijos"]
                    descanso = not (t == "Mañana (06-15)" and e == tarde_ayer)
                    
                    # DOBLE FILTRO DE HORAS: Mensual y Semanal
                    tope_mensual = hs_totales[e] + hs_v <= LIMITE_MENSUAL
                    tope_semanal = hs_semanales[e] + hs_v <= CUOTA_SEMANAL
                    
                    if not any([en_lic, sem_bloq, t_bloq, franco]) and descanso and tope_mensual and tope_semanal and e not in hoy_asignados:
                        cand.append(e)
                
                # Priorizar al que menos horas lleva en el MES
                cand.sort(key=lambda x: hs_totales[x])
                
                if cand:
                    elegido = cand[0]
                    cronograma.append({"nro_dia": d, "Fecha": f_str, "Turno": t, "Empleado": elegido})
                    hs_totales[elegido] += hs_v
                    hs_semanales[elegido] += hs_v
                    hoy_asignados.append(elegido)
                    if t == "Tarde (15-24)": tarde_ayer = elegido
                else:
                    cronograma.append({"nro_dia": d, "Fecha": f_str, "Turno": t, "Empleado": "[VACANTE]"})
                    if t == "Tarde (15-24)": tarde_ayer = None

        if cronograma:
            df = pd.DataFrame(cronograma)
            df_cal = df.pivot_table(index=['nro_dia', 'Fecha'], columns='Turno', values='Empleado', aggfunc='first').reset_index()
            df_cal = df_cal.sort_values('nro_dia').drop(columns='nro_dia')
            
            st.subheader(f"Vista Previa: {mes_nombre} (Balanceado)")
            st.dataframe(df_cal, use_container_width=True)

            try:
                pdf_bytes = crear_pdf(df_cal, mes_nombre, anio)
                st.download_button("📥 Descargar PDF Cronograma", data=pdf_bytes, file_name=f"Turnos_{mes_nombre}.pdf", mime="application/pdf")
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

            st.divider()
            st.subheader("📊 Resumen de Carga Mensual")
            col_m = st.columns(4)
            for i, e in enumerate(empleados):
                h = hs_totales[e]
                col_m[i].metric(e, f"{h} hs", f"{LIMITE_MENSUAL-h} disp.")
                col_m[i].progress(min(h/LIMITE_MENSUAL, 1.0))
