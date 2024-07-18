import pm4py
from utils import llm_model_generator
from utils.general_utils import pt_to_powl_code


def execute_script():
    api_key = open("api_key.txt", "r").read()
    openai_model = "gpt-4o"
    feedback = "Can you add an activity Explode Bomb in the end"

    log = pm4py.read_xes("running-example.xes")
    process_tree = pm4py.discover_process_tree_inductive(log)
    powl_code = pt_to_powl_code.recursively_transform_process_tree(process_tree)
    obj = llm_model_generator.initialize(None, api_key=api_key,
                                   powl_model_code=powl_code, openai_model=openai_model)
    obj = llm_model_generator.update(obj, feedback)
    obj.view_bpmn("svg")


if __name__ == "__main__":
    execute_script()
