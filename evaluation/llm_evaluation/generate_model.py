import pm4py

from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.model_generation import extract_model_from_response
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges
from utils.prompting import create_conversation

code = open("../testfiles/models_as_code/02.txt", "r").read()

variable_name = 'final_model'
result = execute_code_and_get_variable(code, variable_name)
validate_partial_orders_with_missing_transitive_edges(result)

from pm4py.visualization.powl import visualizer
svg = visualizer.apply(result)
visualizer.view(svg)