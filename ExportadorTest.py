import streamlit as st
import requests
import json
import pandas as pd
from requests.auth import HTTPBasicAuth
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import base64
import time  # Nuevo import para manejar pausas

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

st.markdown(
    f'<a href="{youtube_link}" target="_blank">'
    f'<img src="data:image/jpeg;base64,{logo_base64}" style="width:100%;"/>'
    '</a>',
    unsafe_allow_html=True
)

# --- CSS personalizado ---
# --- CSS personalizado ---
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

def get_test_suites(organization, project, plan_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/testplan/plans/{plan_id}/suites?asTreeView=False&api-version={api_version}"
    response = session.get(url, auth=HTTPBasicAuth(username, token))
    if response.status_code == 200:
        return [s for s in response.json().get('value', []) if s.get('suiteType') == 'requirementTestSuite']
    return []

def get_test_runs(organization, project, plan_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs?planId={plan_id}&api-version={api_version}"
    response = session.get(url, auth=HTTPBasicAuth(username, token))
    return response.json().get('value', []) if response.status_code == 200 else []

def get_run_results(organization, project, run_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/test/runs/{run_id}/results?api-version={api_version}"
    response = session.get(url, auth=HTTPBasicAuth(username, token))
    return response.json().get('value', []) if response.status_code == 200 else []

def get_test_points(organization, project, plan_id, suite_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/testplan/plans/{plan_id}/Suites/{suite_id}/TestPoint?api-version={api_version}"
    response = session.get(url, auth=HTTPBasicAuth(username, token))
    return response.json().get('value', []) if response.status_code == 200 else []

def fetch_data_for_project(organization, project_name, plan_id, plan_name, plan_iteration, api_version_suites, api_version_runs, api_version_points, api_version_results, username, token):
    data = []
    processed_run_ids = set()
    test_suites = get_test_suites(organization, project_name, plan_id, api_version_suites, username, token)

    with ThreadPoolExecutor() as executor:
        for suite in test_suites:
            suite_id = suite['id']
            suite_name = suite['name']
            iteration_path = plan_iteration

            future_runs = executor.submit(get_test_runs, organization, project_name, plan_id, api_version_runs, username, token)
            future_points = executor.submit(get_test_points, organization, project_name, plan_id, suite_id, api_version_points, username, token)

            test_runs = future_runs.result()
            for run in test_runs:
                run_id = run['id']
                if run_id in processed_run_ids:
                    continue
                processed_run_ids.add(run_id)
                run_results = get_run_results(organization, project_name, run_id, api_version_runs, username, token)
                for result in run_results:
                    data.append({
                        "Project Name": project_name,
                        "Plan Name": plan_name,
                        "Plan ID": plan_id,
                        "Suite ID": suite_id,
                        "Suite Name": suite_name,
                        "Run ID": run['id'],
                        "Run Name": run['name'],
                        "Test Case ID": result.get('testCase', {}).get('id'),
                        "Test Case Name": result.get('testCase', {}).get('name'),
                        "Outcome": result.get('outcome'),
                        "Executed By": result.get('runBy', {}).get('displayName'),
                        "Execution Date": result.get('completedDate'),
                        "Iteration Path": iteration_path
                    })

            test_points = future_points.result()
            for point in test_points:
                if point.get('results', {}).get('outcome') == "unspecified":
                    data.append({
                        "Project Name": project_name,
                        "Plan Name": plan_name,
                        "Plan ID": plan_id,
                        "Suite ID": suite_id,
                        "Suite Name": suite_name,
                        "Run ID": None,
                        "Run Name": None,
                        "Test Case ID": point.get('testCaseReference', {}).get('id'),
                        "Test Case Name": point.get('testCaseReference', {}).get('name'),
                        "Outcome": "Active",
                        "Executed By": point.get('results', {}).get('lastResultDetails', {}).get('runBy', {}).get('displayName'),
                        "Execution Date": point.get('results', {}).get('lastResultDetails', {}).get('dateCompleted'),
                        "Iteration Path": iteration_path
                    })
    return data

# --- Interfaz de usuario ---
organization = st.text_input("🏢 Nombre de la Organización de Azure DevOps")
token = st.text_input("🔑 Token personal (PAT)", type="password")

project_option = st.radio("¿Qué deseas exportar?", ["Todos los proyectos", "Proyecto específico"])

project_name = None
if project_option == "Proyecto específico":
    project_name = st.text_input("📁 Nombre del proyecto específico")

username = ""

# --- Ejecución ---
if st.button("🔄 Procesar resultados 🧪"):
    if not organization or not token or (project_option == "Proyecto específico" and not project_name):

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
            st.markdown(f'<div class="custom-warning">No se encontraron datos para exportar.</div>', unsafe_allow_html=True)
        
