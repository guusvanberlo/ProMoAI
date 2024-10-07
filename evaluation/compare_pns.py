import pm4py

from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges

code = open("../testfiles/models_as_code/02.txt", "r").read()

variable_name = 'final_model'
result = execute_code_and_get_variable(code, variable_name)
validate_partial_orders_with_missing_transitive_edges(result)


pn, im, fm = pm4py.convert_to_petri_net(result)

log = pm4py.algo.simulation.playout.petri_net.algorithm.apply(pn, im, fm)

print(len(pm4py.get_variants_as_tuples(log).keys()))