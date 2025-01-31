from __future__ import print_function

import numpy as np

import argparse
import torch
import torch.nn as nn
import pdb
import os
import pandas as pd
from utils.utils import *
from math import floor
import matplotlib.pyplot as plt
from dataset_modules.dataset_generic import Generic_WSI_Classification_Dataset, Generic_MIL_Dataset, save_splits
import h5py
from utils.eval_utils import *
from utils.file_utils import save_pkl

# Training settings
parser = argparse.ArgumentParser(description='CLAM Evaluation Script')
parser.add_argument('--data_root_dir', type=str, default=None,
                    help='data directory')
parser.add_argument('--results_dir', type=str, default='./results',
                    help='relative path to results folder, i.e. '+
                    'the directory containing models_exp_code relative to project root (default: ./results)')
parser.add_argument('--save_exp_code', type=str, default=None,
                    help='experiment code to save eval results')
parser.add_argument('--models_exp_code', type=str, default=None,
                    help='experiment code to load trained models (directory under results_dir containing model checkpoints')
parser.add_argument('--splits_dir', type=str, default=None,
                    help='splits directory, if using custom splits other than what matches the task (default: None)')
parser.add_argument('--model_size', type=str, choices=['small', 'big','mini128','miniLayer','microLayer','nanoLayer', 'picoLayer'], default='small',
                    help='size of model (default: small)')
parser.add_argument('--model_type', type=str, choices=['clam_sb', 'clam_mb', 'mil'], default='clam_sb', 
                    help='type of model (default: clam_sb)')
parser.add_argument('--k', type=int, default=10, help='number of folds (default: 10)')
parser.add_argument('--k_start', type=int, default=-1, help='start fold (default: -1, last fold)')
parser.add_argument('--k_end', type=int, default=-1, help='end fold (default: -1, first fold)')
parser.add_argument('--fold', type=int, default=-1, help='single fold to evaluate')
parser.add_argument('--micro_average', action='store_true', default=False, 
                    help='use micro_average instead of macro_avearge for multiclass AUC')
parser.add_argument('--split', type=str, choices=['train', 'val', 'test', 'all'], default='test')
parser.add_argument('--task', type=str, choices=['task_1_tumor_vs_normal',  'task_2_tumor_subtyping', 'biomarker_ER_256','biomarker_ER_1024','biomarker_ER_HUS_256','biomarker_ER_HUS_1024','biomarker_ER_2048','biomarker_ER_HUS_2048'])
parser.add_argument('--drop_out', type=float, default=0.25, help='dropout')
parser.add_argument('--embed_dim', type=int, default=1024)
args = parser.parse_args()

device=torch.device("cuda" if torch.cuda.is_available() else "cpu")

args.save_dir = str(args.save_exp_code)
args.models_dir = os.path.join(args.results_dir, str(args.models_exp_code))

os.makedirs(args.save_dir, exist_ok=True)

if args.splits_dir is None:
    args.splits_dir = args.models_dir

assert os.path.isdir(args.models_dir)
assert os.path.isdir(args.splits_dir)

settings = {'task': args.task,
            'split': args.split,
            'save_dir': args.save_dir, 
            'models_dir': args.models_dir,
            'model_type': args.model_type,
            'drop_out': args.drop_out,
            'model_size': args.model_size}

with open(args.save_dir + '/eval_experiment.txt', 'w') as f:
    print(settings, file=f)
f.close()

print(settings)
if args.task == 'task_1_tumor_vs_normal':
    args.n_classes=2
    dataset = Generic_MIL_Dataset(csv_path = 'dataset_csv/tumor_vs_normal_dummy_clean.csv',
                            data_dir= os.path.join(args.data_root_dir, 'tumor_vs_normal_resnet_features'),
                            shuffle = False, 
                            print_info = True,
                            label_dict = {'normal_tissue':0, 'tumor_tissue':1},
                            patient_strat=False,
                            ignore=[])

elif args.task == 'task_2_tumor_subtyping':
    args.n_classes=3
    dataset = Generic_MIL_Dataset(csv_path = 'dataset_csv/tumor_subtyping_dummy_clean.csv',
                            data_dir= os.path.join(args.data_root_dir, 'tumor_subtyping_resnet_features'),
                            shuffle = False, 
                            print_info = True,
                            label_dict = {'subtype_1':0, 'subtype_2':1, 'subtype_3':2},
                            patient_strat= False,
                            ignore=[])

elif args.task == 'biomarker_ER_256':
    args.n_classes = 2
    dataset = Generic_MIL_Dataset(csv_path='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_256/train_256.csv',
                                  data_dir='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_256/features',
                                  shuffle=False,
                                  print_info=True,
                                  label_col='ER',
                                  label_dict={1: 1, 0: 0},
                                  patient_strat=False,
                                  ignore=['Ki67', 'HER2', 'PR', 'histological subtype', 'histological grade'])

elif args.task == 'biomarker_ER_1024':
    args.n_classes = 2
    dataset = Generic_MIL_Dataset(csv_path='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_1024/train_1024.csv',
                                  data_dir='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_1024/features',
                                  shuffle=False,
                                  print_info=True,
                                  label_col='ER',
                                  label_dict={1: 1, 0: 0},
                                  patient_strat=False,
                                  ignore=['Ki67', 'HER2', 'PR', 'histological subtype', 'histological grade'])

elif args.task == 'biomarker_ER_HUS_1024':
    args.n_classes = 2
    dataset = Generic_MIL_Dataset(csv_path='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_1024_HUS/train_1024_HUS.csv',
                                  data_dir='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_1024_HUS/features',
                                  shuffle=False,
                                  print_info=True,
                                  label_col='ER',
                                  label_dict={1: 1, 0: 0},
                                  patient_strat=False,
                                  ignore=['Ki67', 'HER2', 'PR', 'histological subtype', 'histological grade'])
elif args.task == 'biomarker_ER_HUS_256':
    args.n_classes = 2
    dataset = Generic_MIL_Dataset(csv_path='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_256_HUS/train_256_HUS.csv',
                                  data_dir='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_256_HUS/features',
                                  shuffle=False,
                                  print_info=True,
                                  label_col='ER',
                                  label_dict={1: 1, 0: 0},
                                  patient_strat=False,
                                  ignore=['Ki67', 'HER2', 'PR', 'histological subtype', 'histological grade'])
elif args.task == 'biomarker_ER_2048':
    args.n_classes = 2
    dataset = Generic_MIL_Dataset(csv_path='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_2048/train_2048.csv',
                                  data_dir='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_2048/features',
                                  shuffle=False,
                                  print_info=True,
                                  label_col='ER',
                                  label_dict={1: 1, 0: 0},
                                  patient_strat=False,
                                  ignore=['Ki67', 'HER2', 'PR', 'histological subtype', 'histological grade'])
elif args.task == 'biomarker_ER_HUS_2048':
    args.n_classes = 2
    dataset = Generic_MIL_Dataset(csv_path='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_2048_HUS/train_2048_HUS.csv',
                                  data_dir='/mnt/EncryptedDisk2/BreastData/Studies/CLAM/patchsize_2048_HUS/features',
                                  shuffle=False,
                                  print_info=True,
                                  label_col='ER',
                                  label_dict={1: 1, 0: 0},
                                  patient_strat=False,
                                  ignore=['Ki67', 'HER2', 'PR', 'histological subtype', 'histological grade'])
else:
    raise NotImplementedError

if args.k_start == -1:
    start = 0
else:
    start = args.k_start
if args.k_end == -1:
    end = args.k
else:
    end = args.k_end

if args.fold == -1:
    folds = range(start, end)
else:
    folds = range(args.fold, args.fold+1)
# ckpt_paths = [os.path.join(args.models_dir, 's_{}_checkpoint.pt'.format(fold)) for fold in folds]
ckpt_paths = [os.path.join(args.models_dir, 'averaged_model.pt')]
datasets_id = {'train': 0, 'val': 1, 'test': 2, 'all': -1}

if __name__ == "__main__":
    all_results = []
    all_auc = []
    all_acc = []
    all_acc_0 = []
    all_acc_1 = []
    for ckpt_idx in range(len(ckpt_paths)):
        if datasets_id[args.split] < 0:
            split_dataset = dataset
        else:
            csv_path = '{}/splits_{}.csv'.format(args.splits_dir, folds[ckpt_idx])
            datasets = dataset.return_splits(from_id=False, csv_path=csv_path)
            split_dataset = datasets[datasets_id[args.split]]
        model, patient_results, test_error, auc, df  = eval(split_dataset, args, ckpt_paths[ckpt_idx])
        all_results.append(all_results)
        all_auc.append(auc)
        all_acc.append(1-test_error)
        df.to_csv(os.path.join(args.save_dir, 'fold_{}.csv'.format(folds[ckpt_idx])), index=False)

        class_accuracies = {}
        for cls in df['Y'].unique():  # Loop through each class
            class_data = df[df['Y'] == cls]
            correct = (class_data['Y'] == class_data['Y_hat']).sum()
            total = class_data.shape[0]
            accuracy = correct / total
            class_accuracies[cls] = accuracy
        all_acc_0.append(class_accuracies[0.0])
        all_acc_1.append(class_accuracies[1.0])


    final_df = pd.DataFrame({'folds': folds, 'test_auc': all_auc, 'test_acc': all_acc, 'acc_0':all_acc_0, 'acc_1':all_acc_1})
    if len(folds) != args.k:
        save_name = 'summary_partial_{}_{}.csv'.format(folds[0], folds[-1])
    else:
        save_name = 'summary.csv'
    final_df.to_csv(os.path.join(args.save_dir, save_name))

    try:

        if patient_results['features']:
            filename = os.path.join(args.save_dir, 'feature_results.pkl')
            save_pkl(filename, patient_results)
    except Exception as e:
        print(f"No slide level features saved")
