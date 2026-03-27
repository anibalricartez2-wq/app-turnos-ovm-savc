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

# --- TRADUCCIONES Y FORMATOS ---
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
        # Limpieza de texto para evitar errores de codificación
        f_t = str(row['Fecha']).encode('latin-1', 'replace').decode('latin-1')
        m_t = str(row['Mañana (06-15)']).replace("⚠️ ", "").encode('latin-1', 'replace').decode('latin-1')
        t_t = str(row['Tarde (15-24)']).replace("⚠️ ", "").encode('latin-1', 'replace').decode('latin-1')
        
        pdf.cell(50, 8, f_t, border=1, align="C", fill=fill)
        pdf.cell(70, 8, m_t, border=1, align="C", fill=fill)
        pdf.cell(70, 8, t_t, border=1, align="C", fill=fill)
        pdf.ln()
        fill = not fill
    return pdf.output(dest='S').encode('latin-1', 'ignore')

# --- APLICACIÓN PRINCIPAL ---
if login():
    st.sidebar.header("⚙️ Configuración")
    mes_nombre = st.sidebar.selectbox("Mes", MESES_ES, index=datetime.now().month - 1)
    mes_nro = MESES_ES.index(mes_nombre) + 1
    anio = st.sidebar.number_input("Año", value=2026)
    
    empleados = ["Sánchez", "García", "Barros", "Ricartez"]
    config_per = {}

    for e in empleados:
        with st.sidebar.expander(f"Restricciones {e}"):
            rango = st.date_input(f"Licencia {e}", value=[], key=f"l_{e}")
            dias_p = st.multiselect(f"No trabaja los días:", ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"], key=f"s_{e}")
            t_ev = st.selectbox(f"Evitar turno:", ["Ninguno", "Mañana (06-15)", "Tarde (15-24)"], key=f"t_{e}")
            f_fijos = st.multiselect(f"Francos fijos (nro día):", range(1, 32), key=f"f_{e}")

            fechas_l = pd.date_range(start=rango[0], end=rango[1]).date if len(rango) == 2 else []
            map_d = {"Lunes": 0, "Martes": 1, "Miércoles": 2, "Jueves": 3, "Viernes": 4, "Sábado": 5, "Domingo": 6}
            config_per[e] = {
                "lic": fechas_l, 
                "sem": [map_d[d] for d in dias_p], 
                "t_bloq": t_ev, 
                "f_fijos": f_fijos
            }

    if st.button("🚀 GENERAR PLANILLA"):
        num_dias = calendar.monthrange(anio, mes_nro)[1]
        cronograma = []
        hs_acum = {e: 0 for e in empleados}
        tarde_ayer = None

        for d in range(1, num_dias + 1):
            f_dt = datetime(anio, mes_nro, d)
            idx_s = f_dt.weekday()
            hs_v = 18 if idx_s >= 5 else 9
            f_str = f"{DIAS_ES[idx_s]} {f_dt.strftime('%d/%m/%Y')}"
            
            hoy_asignados = []
            for t in ["Mañana (06-15)", "Tarde (15-24)"]:
                cand = []
                for e in empleados:
                    en_licencia = f_dt.date() in config_per[e]["lic"]
                    dia_semana_bloq = idx_s in config_per[e]["sem"]
                    turno_bloq = t == config_per[e]["t_bloq"]
                    dia_franco = d in config_per[e]["f_fijos"]
                    descanso_ok = not (t == "Mañana (06-15)" and e == tarde_ayer)
                    tope_hs = hs_acum[e] + hs_v <= 160
                    
                    if not any([en_licencia, dia_semana_bloq, turno_bloq, dia_franco]) and descanso_ok and tope_hs and e not in hoy_asignados:
                        cand.append(e)
                
                cand.sort(key=lambda x: hs_acum[x])
                
                if cand:
                    elegido = cand[0]
                    cronograma.append({"nro_dia": d, "Fecha": f_str, "Turno": t, "Empleado": elegido})
                    hs_acum[elegido] += hs_v
                    hoy_asignados.append(elegido)
                    if t == "Tarde (15-24)": tarde_ayer = elegido
                else:
                    cronograma.append({"nro_dia": d, "Fecha": f_str, "Turno": t, "Empleado": "[VACANTE]"})
                    if t == "Tarde (15-24)": tarde_ayer = None

        # --- PROCESAMIENTO Y ORDENAMIENTO ---
        df = pd.DataFrame(cronograma)
        # Aseguramos el orden cronológico usando n
