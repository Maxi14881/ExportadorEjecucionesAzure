import streamlit as st
import requests
import json
import pandas as pd
from requests.auth import HTTPBasicAuth
from io import BytesIO
import base64
import time
import gc
import streamlit.components.v1 as components

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
            background-color: #4F8A10;
            color: #FFFFFF;
            padding: 10px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
        }
        .custom-error {
            background-color: #D8000C;
            color: #FFFFFF;
            padding: 10px;
            border-radius: 0px;
            font-size: 16px;
            font-weight: bold;
        }
        .custom-warning {
            background-color: #FEEFB3;
            color: #9F6000;
            padding: 10px;
            border-radius: 8px;
            font-size: 16px;
            font-weight: bold;
        }
        .custom-info {
            background-color: #D1ECF1;
            color: #0C5460;
            padding: 10px;
            border-radius: 8px;
            font-size: 14px;
        }
        div[role="radiogroup"] {
            max-width: 300px;
        }
        div[role="radiogroup"] label {
            white-space: normal !important;
            width: 100% !important;
        }
        
        /* Estilos para el tooltip del token */
        .token-tooltip {
            position: relative;
            display: inline-block;
            margin-left: 8px;
        }
        .token-tooltip .tooltip-text {
            visibility: hidden;
            width: 300px;
            background-color: #D1ECF1;
            color: #0C5460;
            text-align: left;
            border-radius: 6px;
            padding: 10px;
            position: absolute;
            z-index: 1;
            bottom: 125%;
            left: 50%;
            margin-left: -150px;
            opacity: 0;
            transition: opacity 0.3s;
            font-size: 12px;
            border: 1px solid #B8DACC;
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }
        .token-tooltip .tooltip-text::after {
            content: "";
            position: absolute;
            top: 100%;
            left: 50%;
            margin-left: -5px;
            border-width: 5px;
            border-style: solid;
            border-color: #D1ECF1 transparent transparent transparent;
        }
        .token-tooltip:hover .tooltip-text {
            visibility: visible;
            opacity: 1;
        }
        .help-symbol {
            color: #007BFF;
            cursor: help;
            font-size: 14px;
            font-weight: bold;
            background: #f0f8ff;
            border-radius: 50%;
            width: 18px;
            height: 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 1px solid #007BFF;
        }
        .token-label-container {
            display: flex;
            align-items: center;
            margin-bottom: 8px;
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

# --- Función para limpiar inputs ---
def limpiar_inputs():
    # Asignar valores por defecto en session_state para que los widgets se reinyecten correctamente
    try:
        # (snapshot eliminado) - solo limpiamos los valores

        st.session_state['org_input'] = ""
        st.session_state['token_input'] = ""
        # El radio volverá al valor por defecto: "Todos los proyectos"
        st.session_state['project_radio'] = "Todos los proyectos"
        st.session_state['proj_input'] = ""
        # Limpiar posibles estados auxiliares usados durante el procesamiento
        for aux in ['procesar', 'all_data', 'progress', 'status_text']:
            if aux in st.session_state:
                del st.session_state[aux]
    except Exception:
        # En caso de conflicto con session_state, intentar eliminar claves individualmente
        for key in ["org_input", "token_input", "project_radio", "proj_input"]:
            if key in st.session_state:
                try:
                    del st.session_state[key]
                except Exception:
                    pass

    # Forzar recarga completa de la app
    try:
        st.experimental_rerun()
    except Exception:
        # Fallback a st.rerun si experimental_rerun no está disponible
        st.rerun()


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
    """Realiza llamadas GET manejando paginación."""
    all_items = []
    params = params.copy() if params else {}
    while True:
        resp = session.get(url, auth=auth, params=params)
        if resp.status_code != 200:
            return all_items
        j = resp.json()
        items = j.get('value') or j.get('members') or []
        all_items.extend(items)

        cont = resp.headers.get('x-ms-continuationtoken') or resp.headers.get('x-ms-continuation-token') or j.get('continuationToken')
        if not cont:
            break
        params['continuationToken'] = cont
    return all_items

def _flatten_suites(nodes):
    """Aplana una estructura de suites en árbol."""
    flat = []
    for n in nodes:
        flat.append(n)
        children = n.get('children') or []
        if children:
            flat.extend(_flatten_suites(children))
    return flat

def get_test_suites(organization, project, plan_id, api_version, username, token):
    url = f"https://dev.azure.com/{organization}/{project}/_apis/testplan/plans/{plan_id}/suites?asTreeView=True&api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    suites = api_get_all(url, auth)
    if not suites:
        return []
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
    """Devuelve la lista de test case references en una suite."""
    url = f"https://dev.azure.com/{organization}/{project}/_apis/test/Plans/{plan_id}/Suites/{suite_id}/testcases?api-version={api_version}"
    auth = HTTPBasicAuth(username, token)
    items = api_get_all(url, auth)
    testcases = []
    for it in items:
        tc = it.get('testCase') or it.get('testCaseReference') or it
        tc_id = None
        tc_name = None
        if isinstance(tc, dict):
            tc_id = tc.get('id') or tc.get('testCaseId') or tc.get('workItemId')
            tc_name = tc.get('name') or (tc.get('fields') or {}).get('System.Title') or tc.get('testCaseTitle')
        else:
            tc_id = it.get('id')
            tc_name = it.get('name')

        if tc_id:
            testcases.append({'id': str(tc_id), 'name': tc_name})
    return testcases

def get_workitems_titles(organization, ids, api_version='7.0', username=None, token=None):
    """Obtiene títulos de work items en lote."""
    if not ids:
        return {}
    out = {}
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

def fetch_data_for_project(organization, project_name, plan_id, plan_name, plan_iteration, 
                          api_version_suites, api_version_runs, api_version_points, 
                          api_version_results, username, token):
    data = []
    test_suites = get_test_suites(organization, project_name, plan_id, api_version_suites, username, token)

    all_runs = get_test_runs(organization, project_name, plan_id, api_version_runs, username, token)
    run_results_map = {}
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
            existing = run_results_map.get(tc_id)
            r_date = r.get('completedDate') or r.get('dateCompleted')
            if existing:
                existing_date = existing.get('completedDate') or existing.get('dateCompleted')
                if existing_date and r_date and existing_date >= r_date:
                    continue
            r['_run_id'] = run_id
            r['_run_name'] = run.get('name')
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

        testcases = get_test_cases_in_suite(organization, project_name, plan_id, suite_id, api_version_points, username, token)
        test_points = get_test_points(organization, project_name, plan_id, suite_id, api_version_points, username, token)
        points_map = {}
        for p in test_points:
            tc_ref = p.get('testCaseReference') or p.get('testCase') or {}
            tcid = str(tc_ref.get('id')) if tc_ref else None
            if tcid:
                points_map[tcid] = p

        for tc in testcases:
            tcid = tc.get('id')
            tcname = tc.get('name')
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

    missing_ids = [str(row['Test Case ID']) for row in data if not row.get('Test Case Name')]
    if missing_ids:
        titles = get_workitems_titles(organization, missing_ids, username=username, token=token)
        for row in data:
            if not row.get('Test Case Name'):
                row['Test Case Name'] = titles.get(str(row['Test Case ID']))

    for row in data:
        if not row.get('Test Case Name'):
            rr = run_results_map.get(str(row['Test Case ID']))
            if rr and rr.get('_testcase_name'):
                row['Test Case Name'] = rr.get('_testcase_name')

    return data

# --- Interfaz de usuario ---



organization_input = st.text_input("🏢 Nombre de la Organización de Azure DevOps", key="org_input")

# Input del token con tooltip
st.markdown(
    """
    <div class="token-label-container">
        <label>🔑 Token personal (PAT)</label>
        <div class="token-tooltip">
            <span class="help-symbol">?</span>
            <div class="tooltip-text">
                <strong>🔒 Información de Seguridad:</strong><br>
                • Tu token se usa temporalmente y se borra automáticamente<br>
                • Solo se requieren permisos de lectura<br>
                • Funciona solo sobre HTTPS<br>
                • No se almacena en bases de datos<br>
                • Usa tokens con fecha de expiración
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)
# Usar un placeholder para poder eliminar el widget del DOM cuando arranque el procesamiento
token_placeholder = st.empty()
token_input = token_placeholder.text_input("🔑 Token personal (PAT)", type="password", key="token_input", label_visibility="collapsed")

project_option = st.radio("¿Qué deseas exportar?", ["Todos los proyectos", "Proyecto específico"], key="project_radio")

project_name = None
if project_option == "Proyecto específico":
    project_name = st.text_input("📁 Nombre del proyecto específico", key="proj_input")

# (panel de depuración eliminado)


username = ""

# --- Botones lado a lado ---
col1, col2 = st.columns([1, 1])

with col1:
    procesar = st.button("🔄 Procesar resultados 🧪", key="procesar")

with col2:
    st.button("🧹 Limpiar", on_click=limpiar_inputs)

# --- Ejecución ---
if procesar:
    if not organization_input or not token_input or (project_option == "Proyecto específico" and not project_name):
        st.markdown('<div class="custom-error">Por favor completá todos los campos.</div>', unsafe_allow_html=True)
    else:
        try:
            # USO LOCAL del token (leer y eliminar del session_state para que no quede en el DOM)
            organization = organization_input
            # Preferir el valor en session_state si existe (por reconciliación Streamlit)
            token = st.session_state.pop('token_input', token_input)
            # Eliminar el widget del DOM y reemplazar por mensaje para que el valor no sea inspectable
            try:
                token_placeholder.empty()
            except Exception:
                pass
            # Ejecutar JavaScript corto en el cliente para limpiar cualquier input de tipo password
            try:
                components.html(
                    """
                    <script>
                    setTimeout(function(){
                        try {
                            document.querySelectorAll('input[type=password]').forEach(function(i){ i.value = ''; });
                        } catch(e) {}
                    }, 50);
                    </script>
                    """,
                    height=0,
                )
            except Exception:
                pass
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
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
            
            if project_option == "Todos los proyectos":
                update_progress(10, "Obteniendo lista de proyectos...")
                projects = get_projects(organization, api_version, username, token)
                
                total_projects = len(projects)
                for i, project in enumerate(projects):
                    project_name_iter = project['name']
                    update_progress(10 + int(i/total_projects*60), 
                                  f"📁 Procesando proyecto: {project_name_iter} ({i+1}/{total_projects})")
                    
                    plans = get_all_test_plans(organization, project_name_iter, api_version, username, token)
                    total_plans = len(plans)
                    for j, plan in enumerate(plans):
                        update_progress(10 + int(i/total_projects*60) + int(j/total_plans*30), 
                                      f"📦 Procesando plan: {plan['name']}")
                        
                        data = fetch_data_for_project(
                            organization, project_name_iter, plan['id'], plan['name'], plan.get('iteration', "N/A"),
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
            
            if all_data:
                df = pd.DataFrame(all_data)
                
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df.to_excel(writer, index=False, sheet_name='Resultados')
                
                excel_data = output.getvalue()
                
                update_progress(100, "¡Exportación completada!")
                time.sleep(0.5)
                
                progress_bar.empty()
                status_text.empty()
                
                b64 = base64.b64encode(excel_data).decode()
                href = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}" download="test_results.xlsx" id="download-link">Descargar archivo</a>'
                st.markdown(href, unsafe_allow_html=True)
                
                st.markdown(
                    """
                    <script>
                        document.getElementById('download-link').click();
                    </script>
                    """,
                    unsafe_allow_html=True
                )
                
                st.markdown('<div class="custom-success">¡Los resultados fueron procesados correctamente!</div>', unsafe_allow_html=True)
            else:
                progress_bar.empty()
                status_text.empty()
                st.markdown('<div class="custom-warning">No se encontraron datos para exportar.</div>', unsafe_allow_html=True)
        
        except Exception as e:
            st.error(f"Error durante el procesamiento: {str(e)}")
        
        finally:
            # LIMPIEZA SEGURA - solo de variables locales
            token = ""
            organization = ""
            gc.collect()
            # Eliminar token del session_state por seguridad si quedó guardado por el widget
            try:
                if 'token_input' in st.session_state:
                    # Borrar de session_state para que no quede en la sesión del navegador
                    del st.session_state['token_input']
            except Exception:
                pass
        
        del token
