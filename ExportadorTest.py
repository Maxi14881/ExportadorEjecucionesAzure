import streamlit as st
import requests
import json
import pandas as pd
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import base64
import time  # Nuevo import para manejar pausas
import xlsxwriter

st.set_page_config(
    page_title="Test Results Exporter",
    page_icon="📤",
)

# --- Función para mostrar imagen del canal ---
def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

logo_path = "Screenshot_46.jpg"
youtube_link = "https://www.youtube.com/@QAtotheSoftware"
logo_base64 = image_to_base64(logo_path)

# --- CSS personalizado ---

st.markdown(
    f'<a href="{youtube_link}" target="_blank">'
    f'<img src="data:image/jpeg;base64,{logo_base64}" style="width:100%;"/>'
    '</a>',
    unsafe_allow_html=True
)

# --- CSS personalizado ---

st.markdown(
    """
    <style>
        /* Limitar el ancho del contenedor del radio group */
        div[role="radiogroup"] {
            max-width: 168px;  /* Ajusta este valor según necesites */
        }
        
        /* Asegurar que los labels no se desborden */
        div[role="radiogroup"] label {
            white-space: normal !important;
            width: 100% !important;
        }
        
        
        
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
        .stApp { background-color: #8FBC8B; }
        .stButton button {
            padding: 10px 15px;
            border-radius: 8px;
            font-weight: bold;
            color: white;
            border: none;
            cursor: pointer;
            transition: background-color 0.3s ease;
            background-color: #333333;
            box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.2);
        }
        .stButton button:first-of-type {
            background-color: #007BFF;
            margin-right: 2px;
        }
        .stButton button:first-of-type:hover {
            background-color: #0056b3;
        }
        .stButton button:nth-of-type(2) {
            background-color: #FF4C4C;
            margin-left: 0px;
        }
        .stButton button:nth-of-type(2):hover {
            background-color: #CC0000;
        }
        .custom-success {
            background-color: #4F8A10; /* Verde Oscuro */
            color: #FFFFFF; /* Blanco */
            padding: 10px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
        }
        .custom-error {
            background-color: #D8000C; /* Rojo oscuro */
            color: #FFFFFF; /* Blanco */
            padding: 10px;
            border-radius: 0px;
            font-size: 16px;
            font-weight: bold;
        }
        .custom-warning {
            background-color: #FEEFB3; /* Amarillo claro personalizado */
            color: #9F6000; /* Amarillo oscuro */
            padding: 10px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
        /* Labels más grandes y oscuros - Versión mejorada */
        div[data-testid="stTextInput"] label p,
        div[data-testid="stFileUploader"] label p,
        .stTextInput > label > div[data-testid="stMarkdownContainer"] > p,
        .stFileUploader > label > div[data-testid="stMarkdownContainer"] > p {
            font-size: 20px !important;
            color: #222222 !important;
            font-weight: bold !important;
        }
        
        /* Texto dentro de los inputs */
        .stTextInput input {
            font-size: 18px !important;
            padding: 12px 15px !important;
        }
        
        /* Radio buttons labels */
        div[role="radiogroup"] > label > div:first-child > div {
            font-size: 20px !important;
            color: #222222 !important;
        }
        
        /* Botón principal */
        div[data-testid="stButton"] > button {
            font-size: 18px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
        /* Título del radio group */
        div[data-testid="stMarkdownContainer"] p {
            font-size: 18px !important;
            font-weight: bold !important;
            color: #222222 !important;
        }
        
        /* Opciones del radio button */
        div[role="radiogroup"] label div p {
            font-size: 16px !important;
            color: #222222 !important;
        }
        
        /* Tamaño del círculo del radio button */
        div[role="radiogroup"] label span:first-child {
            width: 16px !important;
            height: 16px !important;
        }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class="stHeader">
        <h1 style="color: black; margin: 0; text-align: center;">Azure DevOps Test Results Exporter</h1>
    </div>
    """,
    unsafe_allow_html=True
)



# --- Sesión HTTP persistente ---
session = requests.Session()

# --- Funciones de conexión con Azure DevOps ---
def get_projects(organization, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/_apis/projects?api-version={api_version}"
    response = session.get(url, auth=HTTPBasicAuth(username, token))
    return response.json().get('value', []) if response.status_code == 200 else []

def get_all_test_plans(organization, project, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/testplan/plans?api-version={api_version}"
    response = session.get(url, auth=HTTPBasicAuth(username, token))
    return response.json().get('value', []) if response.status_code == 200 else []

def api_get_all(url, auth, params=None):
    """Realiza llamadas GET manejando paginación/continuation tokens y devuelve la lista combinada de 'value'."""
    all_items = []
    params = params.copy() if params else {}
    while True:
        resp = session.get(url, auth=auth, params=params)
        if resp.status_code != 200:
            return all_items
        j = resp.json()
        items = j.get('value') or j.get('members') or []
        all_items.extend(items)

        # Intentar detectar token de continuación (cabeceras o campo en body)
        cont = resp.headers.get('x-ms-continuationtoken') or resp.headers.get('x-ms-continuation-token') or j.get('continuationToken')
        if not cont:
            break
        # Usar param estándar continuationToken para la siguiente petición
        params['continuationToken'] = cont
    return all_items


def _flatten_suites(nodes):
    """Aplana una estructura de suites en árbol (retornada por asTreeView=True)."""
    flat = []
    for n in nodes:
        flat.append(n)
        children = n.get('children') or []
        if children:
            flat.extend(_flatten_suites(children))
    return flat


def get_test_suites(organization, project, plan_id, api_version, username, token):
    # Solicitar en modo árbol para obtener suites anidadas y luego aplanar
    url = f"https://dev.azure.com/{organization}/{project}/_apis/testplan/plans/{plan_id}/suites?asTreeView=True&api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    suites = api_get_all(url, auth)
    if not suites:
        return []
    # La respuesta con asTreeView=True puede venir en 'value' con nodos que contienen 'children'
    return _flatten_suites(suites)


def get_test_runs(organization, project, plan_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs?planId={plan_id}&api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    return api_get_all(url, auth)


def get_run_results(organization, project, run_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs/{run_id}/results?api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    return api_get_all(url, auth)


def get_test_points(organization, project, plan_id, suite_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/testplan/plans/{plan_id}/suites/{suite_id}/testpoints?api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    return api_get_all(url, auth)


def get_test_cases_in_suite(organization, project, plan_id, suite_id, api_version, username, token):
    """Devuelve la lista de test case references en una suite (id, name)."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/test/Plans/{plan_id}/Suites/{suite_id}/testcases?api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    items = api_get_all(url, auth)
    testcases = []
    for it in items:
        # El elemento puede tener varias estructuras según la versión de la API
        tc = it.get('testCase') or it.get('testCaseReference') or it
        # Intentar extraer id y nombre desde posibles ubicaciones
        tc_id = None
        tc_name = None
        if isinstance(tc, dict):
            tc_id = tc.get('id') or tc.get('testCaseId') or tc.get('workItemId')
            # Nombre puede estar en 'name' o dentro de 'fields.System.Title'
            tc_name = tc.get('name') or (tc.get('fields') or {}).get('System.Title') or tc.get('testCaseTitle')
        else:
            tc_id = it.get('id')
            tc_name = it.get('name')

        # Asegurar tipo string para id
        if tc_id:
            testcases.append({'id': str(tc_id), 'name': tc_name})
    return testcases


def get_workitems_titles(organization, ids, api_version='7.0', username=None, token=None):
    """Obtiene en lote los títulos (System.Title) de varios work items (test cases) por sus ids.
    ids: lista de strings o ints. Devuelve diccionario id->title.
    """
    if not ids:
        return {}
    out = {}
    # Azure permite consultar múltiple ids separados por comas
    chunk_size = 50
    auth = HTTPBasicAuth(username, token)
    for i in range(0, len(ids), chunk_size):
        chunk = ids[i:i+chunk_size]
        ids_param = ",".join(map(str, chunk))
        url = f"https://dev.azure.com/{organization}/_apis/wit/workitems?ids={ids_param}&fields=System.Title&api-version={api_version}"
        resp = session.get(url, auth=auth)
        if resp.status_code != 200:
            continue
        j = resp.json()
        for wi in j.get('value', []):
            wid = str(wi.get('id'))
            title = (wi.get('fields') or {}).get('System.Title')
            out[wid] = title
    return out

def fetch_data_for_project(organization, project_name, plan_id, plan_name, plan_iteration, api_version_suites, api_version_runs, api_version_points, api_version_results, username, token):
    data = []
    processed_run_ids = set()
    test_suites = get_test_suites(organization, project_name, plan_id, api_version_suites, username, token)

    # Pre-obtener todos los runs y sus resultados para mapear por testCase id -> latest result
    all_runs = get_test_runs(organization, project_name, plan_id, api_version_runs, username, token)
    run_results_map = {}  # testCaseId -> latest result dict
    run_info_map = {}
    for run in all_runs:
        run_id = run.get('id')
        run_info_map[run_id] = {'id': run_id, 'name': run.get('name')}
        results = get_run_results(organization, project_name, run_id, api_version_results, username, token)
        for r in results:
            tc = r.get('testCase') or r.get('testCaseReference') or {}
            tc_id = str(tc.get('id') or tc.get('testCaseId') or tc.get('workItemId') or tc.get('id'))
            if not tc_id:
                continue
            # Preferir resultado más reciente por fecha de completado
            existing = run_results_map.get(tc_id)
            r_date = r.get('completedDate') or r.get('dateCompleted')
            if existing:
                existing_date = existing.get('completedDate') or existing.get('dateCompleted')
                if existing_date and r_date and existing_date >= r_date:
                    continue
            # Guardar run id y run name junto al resultado
            r['_run_id'] = run_id
            r['_run_name'] = run.get('name')
            # Si el resultado contiene referencias al test case con nombre, guardar nombre
            tc_name = None
            if isinstance(tc, dict):
                tc_name = tc.get('name') or (tc.get('fields') or {}).get('System.Title') or tc.get('testCaseTitle')
            if tc_name:
                r['_testcase_name'] = tc_name
            run_results_map[tc_id] = r

    for suite in test_suites:
        suite_id = suite.get('id')
        suite_name = suite.get('name')
        iteration_path = plan_iteration

        # Obtener test cases definidos en la suite
        testcases = get_test_cases_in_suite(organization, project_name, plan_id, suite_id, api_version_points, username, token)

        # Obtener test points (estado/últimos resultados por test point)
        test_points = get_test_points(organization, project_name, plan_id, suite_id, api_version_points, username, token)
        points_map = {}
        for p in test_points:
            tc_ref = p.get('testCaseReference') or p.get('testCase') or {}
            tcid = str(tc_ref.get('id')) if tc_ref else None
            if tcid:
                points_map[tcid] = p

        # Para cada test case en la suite, asociar resultado (run) si existe, o punto si está activo
        for tc in testcases:
            tcid = tc.get('id')
            tcname = tc.get('name')
            # Chequear si hay resultado en run_results_map
            result = run_results_map.get(tcid)
            if result:
                data.append({
                    "Project Name": project_name,
                    "Plan Name": plan_name,
                    "Plan ID": plan_id,
                    "Suite ID": suite_id,
                    "Suite Name": suite_name,
                    "Run ID": result.get('_run_id'),
                    "Run Name": result.get('_run_name'),
                    "Test Case ID": tcid,
                    "Test Case Name": tcname,
                    "Outcome": result.get('outcome'),
                    "Executed By": (result.get('runBy') or {}).get('displayName'),
                    "Execution Date": result.get('completedDate') or result.get('dateCompleted'),
                    "Iteration Path": iteration_path
                })
            else:
                # Si no hay resultado, mirar test point
                p = points_map.get(tcid)
                if p:
                    last = p.get('results') or p.get('lastResultDetails') or {}
                    outcome = last.get('outcome') or ("Active" if not last else last.get('outcome'))
                    executed_by = (last.get('runBy') or {}).get('displayName')
                    date_completed = last.get('dateCompleted') or last.get('completedDate')
                else:
                    outcome = "Not Executed"
                    executed_by = None
                    date_completed = None

                # Si no tenemos nombre, intentaremos obtenerlo más tarde en lote
                data.append({
                    "Project Name": project_name,
                    "Plan Name": plan_name,
                    "Plan ID": plan_id,
                    "Suite ID": suite_id,
                    "Suite Name": suite_name,
                    "Run ID": None,
                    "Run Name": None,
                    "Test Case ID": tcid,
                    "Test Case Name": tcname,
                    "Outcome": outcome,
                    "Executed By": executed_by,
                    "Execution Date": date_completed,
                    "Iteration Path": iteration_path
                })
    # Post-procesamiento: rellenar nombres faltantes consultando work items en lote
    missing_ids = [str(row['Test Case ID']) for row in data if not row.get('Test Case Name')]
    if missing_ids:
        titles = get_workitems_titles(organization, missing_ids, username=username, token=token)
        for row in data:
            if not row.get('Test Case Name'):
                row['Test Case Name'] = titles.get(str(row['Test Case ID']))

    # También, si algún resultado en run_results_map tenía _testcase_name, usarlo cuando falte
    for row in data:
        if not row.get('Test Case Name'):
            rr = run_results_map.get(str(row['Test Case ID']))
            if rr and rr.get('_testcase_name'):
                row['Test Case Name'] = rr.get('_testcase_name')

    return data

# --- Interfaz de usuario ---
organization = st.text_input("🏢 Nombre de la Organización de Azure DevOps",key="org")
token = st.text_input("🔑 Token personal (PAT)", type="password", key="token")

project_option = st.radio("¿Qué deseas exportar?", ["Todos los proyectos", "Proyecto específico"])

project_name = None
if project_option == "Proyecto específico":
    project_name = st.text_input("📁 Nombre del proyecto específico",key="proy")

username = ""


##########

import streamlit as st

# Inicializar valores si no existen
if "org" not in st.session_state:
    st.session_state["org"] = ""
if "proy" not in st.session_state:
    st.session_state["proy"] = ""
if "token" not in st.session_state:
    st.session_state["token"] = ""
if "limpiar" not in st.session_state:
    st.session_state["limpiar"] = False

# Función para limpiar inputs
def limpiar_inputs():
    st.session_state["org"] = ""
    st.session_state["proy"] = ""
    st.session_state["token"] = ""
    st.session_state["limpiar"] = True  # Forzar recarga visual


# Botón para limpiar
#st.button("🧹 Limpiar", on_click=limpiar_inputs)


# --- Botones lado a lado ---
col1, col2 = st.columns([1, 1])

with col1:
    procesar = st.button("🔄 Procesar resultados 🧪", key="procesar")

with col2:
    st.button("🧹 Limpiar", on_click=limpiar_inputs)


# Recargar la app forzadamente (solo una vez)
if st.session_state["limpiar"]:
    st.session_state["limpiar"] = False
    st.rerun()


##########

# --- Ejecución ---
if procesar :#st.button("🔄 Procesar resultados 🧪"):
    if not organization or not token or (project_option == "Proyecto específico" and not project_name):
       # st.warning("Por favor completá todos los campos.")

        st.markdown(f'<div class="custom-error">Por favor completá todos los campos.</div>', unsafe_allow_html=True)
        
    else:
        # Creamos un espacio para la barra de progreso
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Función para actualizar el progreso
        def update_progress(progress, message):
            progress_bar.progress(progress)
            status_text.text(message)
        
        update_progress(0, "Iniciando exportación...")
        
        api_version = "7.1-preview.1"
        api_version_suites = "7.1-preview.1"
        api_version_runs = "7.1-preview.3"
        api_version_points = "7.1"
        api_version_results = "7.1-preview.3"
        all_data = []
        
        # Obtener todos los proyectos
        if project_option == "Todos los proyectos":
            update_progress(10, "Obteniendo lista de proyectos...")
            projects = get_projects(organization, api_version, username, token)
            
            total_projects = len(projects)
            for i, project in enumerate(projects):
                project_name = project['name']
                update_progress(10 + int(i/total_projects*60), 
                              f"📁 Procesando proyecto: {project_name} ({i+1}/{total_projects})")
                
                plans = get_all_test_plans(organization, project_name, api_version, username, token)
                total_plans = len(plans)
                for j, plan in enumerate(plans):
                    update_progress(10 + int(i/total_projects*60) + int(j/total_plans*30), 
                                  f"📦 Procesando plan: {plan['name']}")
                    
                    data = fetch_data_for_project(
                        organization, project_name, plan['id'], plan['name'], plan.get('iteration', "N/A"),
                        api_version_suites, api_version_runs, api_version_points, api_version_results,
                        username, token
                    )
                    all_data.extend(data)
        
        else:
            if project_name:
                update_progress(20, f"Procesando proyecto específico: {project_name}")
                plans = get_all_test_plans(organization, project_name, api_version, username, token)
                
                total_plans = len(plans)
                for j, plan in enumerate(plans):
                    update_progress(20 + int(j/total_plans*70), 
                                  f"📦 Procesando plan: {plan['name']} ({j+1}/{total_plans})")
                    
                    data = fetch_data_for_project(
                        organization, project_name, plan['id'], plan['name'], plan.get('iteration', "N/A"),
                        api_version_suites, api_version_runs, api_version_points, api_version_results,
                        username, token
                    )
                    all_data.extend(data)
        
        update_progress(95, "Generando archivo Excel...")
        
        # Crear un archivo Excel en memoria
        if all_data:
            df = pd.DataFrame(all_data)
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Resultados')
            
            excel_data = output.getvalue()
            
            update_progress(100, "¡Exportación completada!")
            time.sleep(0.5)  # Pequeña pausa para que se vea el 100%
            
            # Limpiar los elementos de progreso
            progress_bar.empty()
            status_text.empty()
            
            # Generar un enlace de descarga automático
            b64 = base64.b64encode(excel_data).decode()
            href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="test_results.xlsx" id="download-link">Descargar archivo</a>'
            st.markdown(href, unsafe_allow_html=True)
            
            # JavaScript para activar la descarga automáticamente
            st.markdown(
                """
                <script>
                    document.getElementById('download-link').click();
                </script>
                """,
                unsafe_allow_html=True
            )
            
            #st.success("¡Los resultados fueron procesados correctamente!")
            st.markdown(f'<div class="custom-success">¡Los resultados fueron procesados correctamente!</div>', unsafe_allow_html=True)
        

        else:
            progress_bar.empty()
            status_text.empty()
            #st.warning("No se encontraron datos para exportar.")
            
            #st.warning("Por favor completá todos los campos.")
            
            st.markdown(f'<div class="custom-warning">No se encontraron datos para exportar.</div>', unsafe_allow_html=True)
