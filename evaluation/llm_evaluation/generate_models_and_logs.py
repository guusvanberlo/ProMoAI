import os
import pm4py

from utils.model_generation.code_extraction import execute_code_and_get_variable
from utils.model_generation.validation import validate_partial_orders_with_missing_transitive_edges

folder = '../testfiles/long_descriptions'
for proc_file in os.listdir(folder):
    proc_id = os.path.splitext(proc_file)[0]
    ground_truth_file = f"../testfiles/models_as_code/{proc_id}.txt"

    if not os.path.exists(ground_truth_file):
        print(f"Ground truth file not found for {proc_file}, skipping.")
        continue

    # Load process description and ground truth model
    proc_descr = open(os.path.join(folder, proc_file), "r").read().strip()
    code = open(ground_truth_file, "r").read()

    # Generate ground truth Petri net
    variable_name = 'final_model'
    ground_truth_powl = execute_code_and_get_variable(code, variable_name)
    validate_partial_orders_with_missing_transitive_edges(ground_truth_powl)
    ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.convert_to_petri_net(ground_truth_powl)

    ground_truth_dir = f"../testfiles/ground_truth_pn"
    if not os.path.exists(ground_truth_dir):
        os.makedirs(ground_truth_dir)
    pm4py.write_pnml(ground_truth_net, ground_truth_im, ground_truth_fm,
                     os.path.join(ground_truth_dir, f"{proc_id}_ground_truth_petri.pnml"))

    ground_truth_dir = f"../testfiles/ground_truth_xes"
    if not os.path.exists(ground_truth_dir):
        os.makedirs(ground_truth_dir)
    ground_truth_log = pm4py.algo.simulation.playout.petri_net.algorithm.apply(ground_truth_net, ground_truth_im,
                                                                               ground_truth_fm)
    pm4py.write_xes(ground_truth_log, os.path.join(ground_truth_dir, f"{proc_id}_ground_truth_log.xes"))
