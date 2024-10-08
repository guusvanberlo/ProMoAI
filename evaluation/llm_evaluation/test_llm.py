import csv
import os
import pm4py
import json
from utils import llm_model_generator, shared
from utils.general_utils import connection_utils

# Read API configurations
api_url = open("../api_url.txt", "r").read().strip()
api_key = open("../api_key.txt", "r").read().strip()
openai_model = open("../api_model.txt", "r").read().strip()

# Define directories for reading input and saving results
description_folder = "../testfiles/long_descriptions"
ground_truth_pn_folder = "../testfiles/ground_truth_pn"
ground_truth_log_folder = "../testfiles/ground_truth_xes"
base_dir = f"llm_com/{openai_model.replace('/', '_')}"

# Ensure base directories exist for saving results
if not os.path.exists(base_dir):
    os.makedirs(base_dir)

pn_folder = os.path.join(base_dir, 'pn')
if not os.path.exists(pn_folder):
    os.makedirs(pn_folder)

conv_folder = os.path.join(base_dir, 'conv')
if not os.path.exists(conv_folder):
    os.makedirs(conv_folder)

# Results table to collect statistics
results_table = []

statistics_csv_file = os.path.join(base_dir, "results_statistics.csv")
with open(statistics_csv_file, "w", newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    # Write the header
    csv_writer.writerow([
        "log_name",
        "conversation_length",
        "visible_transitions_ground_truth",
        "visible_transitions_generated",
        "shared_activities",
        "percFitTraces",
        "averageFitness",
        "percentage_of_fitting_traces",
        "average_trace_fitness",
        "log_fitness",
        "precision"
    ])

# Loop through each process description file
for proc_file in os.listdir(description_folder):
    # Get process ID from file name (e.g., "01.txt")
    proc_id = os.path.splitext(proc_file)[0]

    # Define paths for ground truth Petri net and log
    ground_truth_pn_path = os.path.join(ground_truth_pn_folder, f"{proc_id}_ground_truth_petri.pnml")
    ground_truth_log_path = os.path.join(ground_truth_log_folder, f"{proc_id}_ground_truth_log.xes")

    # Check if the corresponding ground truth files exist
    if not os.path.exists(ground_truth_pn_path) or not os.path.exists(ground_truth_log_path):
        raise Exception(f"Ground truth files not found for {proc_file}, skipping.")

    # Load process description
    proc_descr = open(os.path.join(description_folder, proc_file), "r").read().strip()

    # Load ground truth Petri net and log
    ground_truth_net, ground_truth_im, ground_truth_fm = pm4py.read_pnml(ground_truth_pn_path)
    ground_truth_log = pm4py.read_xes(ground_truth_log_path, return_legacy_log_object=True)
    activities_in_ground_truth = [x for x in ground_truth_net.transitions if x.label is not None]

    # Setting up output paths
    # output_file = os.path.join(results_folder, clean_model_name, f"{proc_file}.csv")

    # Extract activities from ground truth log and append to process description
    log_activities = set(event["concept:name"] for trace in ground_truth_log for event in trace)
    proc_descr += "\n\nEnsure the generated model uses the following activity labels (please also note upper and lower case): " + ", ".join(
        log_activities)

    # Initialize LLM model generation
    try:
        obj = llm_model_generator.initialize(process_description=proc_descr, api_key=api_key, openai_model=openai_model,
                                             api_url=api_url, debug=False)
    except:
        # Extract statistics
        stats = {
            "log_name": proc_file,
            "conversation_length": "Error",
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": "None",
            "shared_activities": "None",
            "fitness": "None",
            "precision": "None"
        }

    else:
        # Convert resulting model to Petri net
        conversation_history = obj.conversation
        powl = obj.process_model
        net, im, fm = pm4py.convert_to_petri_net(powl)
        activities_in_generated = [x for x in net.transitions if x.label is not None]

        # Save Petri net
        pnml_path = os.path.join(pn_folder, f"{proc_file}.pnml")
        pm4py.write_pnml(net, im, fm, pnml_path)

        # Save conversation history
        conversation_path = os.path.join(conv_folder, f"{proc_file}.txt")
        with open(conversation_path, "w", encoding="utf-8") as conv_file:
            conv_file.write(str(conversation_history))

        # Compare with ground truth
        shared_activities = len(set(t.label for t in net.transitions if t.label) & set(
            t.label for t in ground_truth_net.transitions if t.label))
        fitness = pm4py.fitness_alignments(ground_truth_log, net, im, fm)
        precision = pm4py.precision_alignments(ground_truth_log, net, im, fm)

        # Extract statistics
        stats = {
            "log_name": proc_file,
            "conversation_length": len(conversation_history),
            "visible_transitions_ground_truth": len(activities_in_ground_truth),
            "visible_transitions_generated": len(activities_in_generated),
            "shared_activities": shared_activities,
            "fitness": fitness,
            "precision": precision
        }

    # Save statistics
    results_table.append(stats)

    # Append to CSV for every iteration
    with open(statistics_csv_file, "a", newline='', encoding="utf-8") as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow([
            stats["log_name"],
            stats["conversation_length"],
            stats["visible_transitions_ground_truth"],
            stats["visible_transitions_generated"],
            stats["shared_activities"],
            stats["fitness"]["percFitTraces"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["averageFitness"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["percentage_of_fitting_traces"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["average_trace_fitness"] if stats["fitness"] != "None" else "None",
            stats["fitness"]["log_fitness"] if stats["fitness"] != "None" else "None",
            stats["precision"] if stats["precision"] != "None" else "None"
        ])

    # Save the statistics table
    statistics_file = os.path.join(base_dir, "results_statistics.json")
    with open(statistics_file, "w") as stats_file:
        json.dump(results_table, stats_file, indent=4)
