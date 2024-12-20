import os
import subprocess
import time
from tensorboard.backend.event_processing.event_accumulator import EventAccumulator
import logging
import ast

# Suppress TensorFlow logs
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'  # Set TensorFlow log level: 0 = ALL, 1 = INFO, 2 = WARNING, 3 = ERROR
logging.getLogger('tensorflow').setLevel(logging.ERROR)


def run_tensorboard(logdir):
    """Run TensorBoard with the specified log directory."""
    print(f"Launching TensorBoard for: {logdir}")
    return subprocess.Popen(['tensorboard', '--logdir', logdir])


def wait_for_user_input():
    """Wait for the user to signal readiness to move to the next experiment."""
    input("\nPress Enter to proceed to the next experiment...\n")


def get_max_epoch_from_subfolders(experiment_path, scalar_name='val/loss'):
    """
    Get the maximum epoch number for a scalar across all subfolders in an experiment directory.
    Returns the maximum step number or 0 if the scalar is not found.
    """
    max_epoch = 0
    try:
        for subfolder in os.listdir(experiment_path):  # Traverse through the subfolders (e.g., '0', '1', ..., '9')
            subfolder_path = os.path.join(experiment_path, subfolder)
            if os.path.isdir(subfolder_path):
                try:
                    event_accumulator = EventAccumulator(subfolder_path)
                    event_accumulator.Reload()  # Load data from the log directory
                    if scalar_name in event_accumulator.Tags().get('scalars', []):
                        scalars = event_accumulator.Scalars(scalar_name)
                        max_epoch = max(max_epoch, max(scalar.step for scalar in scalars))
                except Exception as e:
                    print(f"Error processing subfolder {subfolder_path}: {e}")
    except Exception as e:
        print(f"Error processing experiment path {experiment_path}: {e}")
    return max_epoch


def filter_experiment_by_model_size(experiment_path, model_size):
    """
    Check if the experiment matches the 'model_size' filter.

    Args:
        experiment_path (str): Path to the experiment directory.
        model_size (str): The desired model size to filter by.

    Returns:
        bool: True if the experiment matches the model size, False otherwise.
    """
    params_file = None
    for file in os.listdir(experiment_path):  # Find the 'experiment_' file
        if file.startswith("experiment_"):
            params_file = os.path.join(experiment_path, file)
            break

    if params_file and os.path.isfile(params_file):
        try:
            with open(params_file, "r") as file:
                params = ast.literal_eval(file.read())  # Parse dictionary-like syntax
                return params.get('model_size') == model_size
        except (ValueError, SyntaxError) as e:
            print(f"Error parsing parameters file {params_file}: {e}")
            return False  # Skip this experiment if content is invalid
    return False  # Skip if no parameter file is found


def print_experiment_parameters(experiment_path):
    """
    Print the parameters of the experiment from a file that begins with 'experiment_'.
    """
    params_file = None
    for file in os.listdir(experiment_path):  # Find the 'experiment_' file
        if file.startswith("experiment_"):
            params_file = os.path.join(experiment_path, file)
            break

    if params_file and os.path.isfile(params_file):
        try:
            with open(params_file, "r") as file:
                print("\nExperiment Parameters:")
                print(file.read())  # Print the content as-is
        except Exception as e:
            print(f"Error reading parameters file: {e}")
    else:
        print("\nNo parameters file found for this experiment.\n")


def main():
    # Prompt for the path to the experiments folder
    root_folder = input("\nEnter the path to the folder containing experiments: \n")

    # Validate the root folder
    if not os.path.isdir(root_folder):
        print(f"Error: {root_folder} is not a valid directory.\n")
        return

    # Prompt for the minimum number of epochs
    try:
        min_epochs = int(input("\nEnter the minimum number of epochs to consider an experiment: \n"))
    except ValueError:
        print("Error: Please enter a valid integer for the minimum number of epochs.\n")
        return

    # Prompt for the model size
    model_size = input("\nEnter the model size to filter experiments (leave empty to include all): \n").strip()

    # List all experiments (subfolders in the root folder)
    all_experiments = [
        os.path.join(root_folder, exp)
        for exp in os.listdir(root_folder)
        if os.path.isdir(os.path.join(root_folder, exp))
    ]

    # Filter experiments based on the maximum epoch count
    experiments = [
        exp for exp in all_experiments if get_max_epoch_from_subfolders(exp) >= min_epochs
    ]

    # Further filter experiments by model size
    if model_size:
        experiments = [exp for exp in experiments if filter_experiment_by_model_size(exp, model_size)]

    # Handle case where no experiments meet the criteria
    if not experiments:
        print("No experiments matching the criteria found in the specified folder.\n")
        return

    print(f"\nFound {len(experiments)} experiments matching the criteria. Starting TensorBoard...\n")

    # Iterate through the filtered experiments
    for idx, experiment in enumerate(experiments):
        print(f"Experiment {idx + 1}/{len(experiments)}: {experiment}")

        # Print experiment parameters
        print_experiment_parameters(experiment)

        # Launch TensorBoard for the experiment
        tb_process = run_tensorboard(experiment)

        try:
            # Wait for user input to proceed to the next experiment
            wait_for_user_input()
        finally:
            # Terminate TensorBoard process before moving to the next experiment
            print(f"Terminating TensorBoard for: {experiment}")
            tb_process.terminate()
            tb_process.wait()
            time.sleep(1)  # Allow TensorBoard to clean up

    print("\nFinished reviewing all experiments.\n")


if __name__ == "__main__":
    main()
