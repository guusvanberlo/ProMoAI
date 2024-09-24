import subprocess

import streamlit as st
import textwrap
import pm4py

from utils import llm_model_generator
from utils.general_utils import improve_descr
from pm4py.objects.conversion.powl.variants.to_petri_net import apply as powl_to_pn

from pm4py.util import constants
from pm4py.objects.petri_net.exporter.variants.pnml import export_petri_as_string
from pm4py.visualization.petri_net import visualizer as pn_visualizer
from pm4py.visualization.bpmn import visualizer as bpmn_visualizer
from pm4py.objects.conversion.wf_net.variants.to_bpmn import apply as pn_to_bpmn
from pm4py.objects.bpmn.layout import layouter
from pm4py.objects.bpmn.exporter.variants.etree import get_xml_string
from utils.general_utils import pt_to_powl_code
from tempfile import NamedTemporaryFile


def run_model_generator_app():
    subprocess.run(['streamlit', 'run', __file__])


def run_app():
    st.title('🤖 ProMoAI')

    st.subheader(
        "Process Model Generator with Generative AI"
    )

    if 'selected_mode' not in st.session_state:
        st.session_state['selected_mode'] = "Model Generation"

    selected_mode = st.radio("Select Mode:", ["Model Generation", "Model Re-design"], horizontal=True)

    if selected_mode != st.session_state['selected_mode']:
        st.session_state['selected_mode'] = selected_mode
        st.session_state['model_gen'] = None
        st.session_state['feedback'] = []
        st.experimental_rerun()

    with st.form(key='model_gen_form'):
        col1, col2 = st.columns(2)

        with col1:
            open_ai_model = st.text_input("Enter the OpenAI model name:", value="gpt-4o-mini",
                                          help="You can check the latest models under: https://openai.com/pricing")

        with col2:
            api_key = st.text_input("Enter your OpenAI API key:", type="password")

        if selected_mode == "Model Generation":
            redesign = False
            description = st.text_area("For **process modeling**, enter the process description:")

        else:
            redesign = True
            uploaded_file = st.file_uploader("For **process model re-design**, upload a block-structured BPMN 2.0 XML",
                                             type=["bpmn"],
                                             help="Block-structured workflow.")
        with st.expander("Show optional settings"):
            api_url = st.text_input(
                "Enter the API URL (optional):",
                value="https://api.openai.com/v1",
                help="Specify the API URL if needed."
            )
            prompt_improvement = st.checkbox(
                "Enable self-improvement of the input prompt",
                value=False
            )
            model_improvement = st.checkbox(
                "Enable self-improvement of the generated model",
                value=False
            )
            num_candidates = st.number_input(
                "Number of different candidates to consider (>=1):",
                min_value=1,
                value=1
            )

        submit_button = st.form_submit_button(label='Run')

    if submit_button:
        if redesign:
            if uploaded_file is None:
                st.error(body="No file is selected!", icon="⚠️")
                return
            try:
                contents = uploaded_file.read()
                F = open("temp.bpmn", "wb")
                F.write(contents)
                F.close()

                bpmn_graph = pm4py.read_bpmn("temp.bpmn")
                process_tree = pm4py.convert_to_process_tree(bpmn_graph)
                powl_code = pt_to_powl_code.recursively_transform_process_tree(process_tree)
                obj = llm_model_generator.initialize(None, api_key=api_key,
                                                     powl_model_code=powl_code, openai_model=open_ai_model, api_url=api_url,
                                                     debug=False)
                st.session_state['model_gen'] = obj
                st.session_state['feedback'] = []
            except Exception as e:
                st.error(body="Please upload a block-structured workflow!", icon="⚠️")
                return
        else:
            try:
                if prompt_improvement:
                    description = improve_descr.improve_process_description(description, api_key=api_key, openai_model=open_ai_model, api_url=api_url)

                obj = llm_model_generator.initialize(description, api_key, open_ai_model, api_url=api_url,
                                               n_candidates=num_candidates)

                if model_improvement:
                    feedback = "Please improve the process model. For example, typical improvement steps include additional activities, managing a greater number of exceptions, or increasing the concurrency in the execution of the process."
                    obj = llm_model_generator.update(obj, feedback, n_candidates=num_candidates)

                st.session_state['model_gen'] = obj
                st.session_state['feedback'] = []
            except Exception as e:
                st.error(body=str(e), icon="⚠️")
                return

    if 'model_gen' in st.session_state and st.session_state['model_gen']:

        st.success("Model generated successfully!", icon="🎉")

        col1, col2 = st.columns(2)

        try:
            with col1:

                with st.form(key='feedback_form'):
                    feedback = st.text_area("Feedback:", value="")
                    if st.form_submit_button(label='Update Model'):
                        try:
                            st.session_state['model_gen'] = llm_model_generator.update(st.session_state['model_gen'], feedback, n_candidates=num_candidates)
                        except Exception as e:
                            raise Exception("Update failed! " + str(e))
                        st.session_state['feedback'].append(feedback)

                    if len(st.session_state['feedback']) > 0:
                        with st.expander("Feedback History", expanded=True):
                            i = 0
                            for f in st.session_state['feedback']:
                                i = i + 1
                                st.write("[" + str(i) + "] " + f + "\n\n")

            with col2:
                st.write("Export Model")
                powl = st.session_state['model_gen'].get_powl()
                pn, im, fm = powl_to_pn(powl)
                bpmn = pn_to_bpmn(pn, im, fm)
                bpmn = layouter.apply(bpmn)

                download_1, download_2 = st.columns(2)
                with download_1:
                    bpmn_data = get_xml_string(bpmn,
                                               parameters={"encoding": constants.DEFAULT_ENCODING})
                    st.download_button(
                        label="Download BPMN",
                        data=bpmn_data,
                        file_name="process_model.bpmn",
                        mime="application/xml"
                    )

                with download_2:
                    pn_data = export_petri_as_string(pn, im, fm)
                    st.download_button(
                        label="Download PNML",
                        data=pn_data,
                        file_name="process_model.pnml",
                        mime="application/xml"
                    )

            view_option = st.selectbox("Select a view:", ["BPMN", "Petri net"])

            image_format = str("svg").lower()
            # if view_option == "POWL":
            #     from pm4py.visualization.powl import visualizer
            #     visualization = visualizer.apply(powl,
            #                                      parameters={'format': image_format})
            if view_option == "Petri net":
                visualization = pn_visualizer.apply(pn, im, fm,
                                                    parameters={'format': image_format})
            else:  # BPMN
                visualization = bpmn_visualizer.apply(bpmn,
                                                      parameters={'format': image_format})

            with st.expander("View Image", expanded=True):
                st.image(visualization.pipe(format='svg').decode('utf-8'))

        except Exception as e:
            st.error(icon='⚠', body=str(e))


def add_footer():
    st.markdown("\n\n")

    st.markdown(textwrap.dedent("""
            [![LinkedIn](https://img.shields.io/badge/Humam%20Kourani-gray?logo=linkedin&labelColor=blue)](https://www.linkedin.com/in/humam-kourani-98b342232/)
            [![Email](https://img.shields.io/badge/Email-gray?logo=minutemailer&logoColor=white&labelColor=green)](mailto:humam.kourani@fit.fraunhofer.de)
        """), unsafe_allow_html=True)
    st.markdown(textwrap.dedent("""
            [![LinkedIn](https://img.shields.io/badge/Alessandro%20Berti-gray?logo=linkedin&labelColor=blue)](https://www.linkedin.com/in/alessandro-berti-2a483766/)
            [![Email](https://img.shields.io/badge/Email-gray?logo=minutemailer&logoColor=white&labelColor=green)](mailto:a.berti@pads.rwth-aachen.de)
        """), unsafe_allow_html=True)
    st.markdown(textwrap.dedent("""
            [![Paper](https://img.shields.io/badge/ProMoAI:%20Process%20Modeling%20with%20Generative%20AI-gray?logo=adobeacrobatreader&labelColor=red)](https://doi.org/10.24963/ijcai.2024/1014)
        """), unsafe_allow_html=True)


if __name__ == "__main__":
    st.set_page_config(
        page_title="ProMoAI",
        page_icon="🤖"
    )
    run_app()
    add_footer()
