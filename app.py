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

# --- CONSTANTES ---
DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
DIAS_ABR = ["Lun", "Mar", "Mie", "Jue", "Vie", "Sab", "Dom"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
TURNOS = ["Mañana (06-15)", "Tarde (15-24)"]

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
    mes_nombre = st.sidebar.selectbox("Mes", MESES_ES, index=datetime.now().month - 1)
    mes_nro = MESES_ES.index(mes_nombre) + 1
    anio = st.sidebar.number_input("Año", value=2026)
    
    empleados = ["Sánchez", "García", "Barros", "Ricartez"]
    LIMITE_MENSUAL, CUOTA_SEMANAL = 160, 45 
    
    config_per = {}
    for e in empleados:
        with st.sidebar.expander(f"Restricciones {e}"):
            rango = st.date_input(f"Licencia {e}", value=[], key=f"lic_{e}")
            f_fijos = st.multiselect(f"Francos fijos:", range(1, 32), key=f"fra_{e}")
            
            st.write("**Bloqueos de Turno:**")
            bloqueos_e = []
            c1, c2 = st.columns(2)
            for i, d_n in enumerate(DIAS_ES):
                col = c1 if i < 4 else c2
                if col.checkbox(f"{d_n} Mañ", key=f"m_{e}_{d_n}"): bloqueos_e.append((d_n, TURNOS[0]))
                if col.checkbox(f"{d_n} Tard", key=f"t_{e}_{d_n}"): bloqueos_e.append((d_n, TURNOS[1]))

            fechas_l = []
            if isinstance(rango, (list, tuple)) and len(rango) == 2:
                fechas_l = pd.date_range(start=rango[0], end=rango[1]).date
            
            config_per[e] = {"lic": fechas_l, "f_fijos": f_fijos, "bloqueos": bloqueos_e}

    if st.button("🚀 GENERAR PLANILLA"):
        num_dias = calendar.monthrange(anio, mes_nro)[1]
        cronograma, hs_tot, hs_sem = [], {e: 0 for e in empleados}, {e: 0 for e in empleados}
        tarde_ayer, sem_act = None, None

        for d in range(1, num_dias + 1):
            f_dt = datetime(anio, mes_nro, d)
            idx_s, nom_dia = f_dt.weekday(), DIAS_ES[f_dt.weekday()]
            iso_s = f_dt.isocalendar()[1]
            if iso_s != sem_act:
                hs_sem = {e: 0 for e in empleados}
                sem_act = iso_s

            hs_v = 18 if idx_s >= 5 else 9
            f_str = f"{DIAS_ABR[idx_s]} {f_dt.strftime('%d/%m/%Y')}"
            hoy_asig = []

            for t in TURNOS:
                cand = []
                for e in empleados:
                    lic = f_dt.date() in config_per[e]["lic"]
                    fra = d in config_per[e]["f_fijos"]
                    bloq = (nom_dia, t) in config_per[e]["bloqueos"]
                    desc = not (t == TURNOS[0] and e == tarde_ayer)
                    lim_m = hs_tot[e] + hs_v <= LIMITE_MENSUAL
                    lim_s = hs_sem[e] + hs_v <= CUOTA_SEMANAL
                    
                    if not any([lic, fra, bloq]) and desc and lim_m and lim_s and e not in hoy_asig:
                        cand.append(e)
                
                cand.sort(key=lambda x: hs_tot[x])
                
                if cand:
                    elegido = cand[0]
                    cronograma.append({"nro": d, "Fecha": f_str, "Turno": t, "Empleado": elegido})
                    hs_tot[elegido] += hs_v
                    hs_sem[elegido] += hs_v
                    hoy_asig.append(elegido)
                    if t == TURNOS[1]: 
                        tarde_ayer = elegido
                else:
                    cronograma.append({"nro": d, "Fecha": f_str, "Turno": t, "Empleado": "[VACANTE]"})
                    if t == TURNOS[1]: 
                        tarde_ayer = None

        if cronograma:
            df = pd.DataFrame(cronograma)
            df_c = df.pivot_table(index=['nro', 'Fecha'], columns='Turno', values='Empleado', aggfunc
