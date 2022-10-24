#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2022 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: EPL-2.0
#

from pydoc import locate
import torch

from tlt.datasets.pytorch_dataset import PyTorchDataset
from tlt.datasets.image_classification.image_classification_dataset import ImageClassificationDataset

DATASETS = ["CIFAR10", "Food101", "CIFAR100", "Country211", "DTD", "FGVCAircraft", "RenderedSST2"]


class TorchvisionImageClassificationDataset(ImageClassificationDataset, PyTorchDataset):
    """
    An image classification dataset from the torchvision catalog
    """
    def __init__(self, dataset_dir, dataset_name, split=['train'], download=True, num_workers=0, shuffle_files=False):
        """
        Class constructor
        """
        if not isinstance(split, list):
            raise ValueError("Value of split argument must be a list.")
        for s in split:
            if not isinstance(s, str) or s not in ['train', 'validation', 'test']:
                raise ValueError('Split argument can only contain these strings: train, validation, test.')
        if dataset_name not in DATASETS:
            raise ValueError("Dataset name is not supported. Choose from: {}".format(DATASETS))
        else:
            dataset_class = locate('torchvision.datasets.{}'.format(dataset_name))
        ImageClassificationDataset.__init__(self, dataset_dir, dataset_name)
        self._num_workers = num_workers
        self._shuffle = shuffle_files
        self._preprocessed = {}
        self._dataset = None
        self._train_indices = None
        self._validation_indices = None
        self._test_indices = None

        if len(split) == 1:
            # If there is only one split, use it for _dataset and do not define any indices
            if split[0] == 'train':
                try:
                    self._dataset = dataset_class(dataset_dir, split='train', download=True)
                except TypeError:
                    self._dataset = dataset_class(dataset_dir, train=True, download=True)
            elif split[0] == 'validation':
                try:
                    self._dataset = dataset_class(dataset_dir, split='val', download=True)
                except TypeError:
                    raise ValueError('No validation split was found for this dataset: {}'.format(dataset_name))
            elif split[0] == 'test':
                try:
                    self._dataset = dataset_class(dataset_dir, split='test', download=True)
                except TypeError:
                    try:
                        self._dataset = dataset_class(dataset_dir, train=False, download=True)
                    except TypeError:
                        raise ValueError('No test split was found for this dataset: {}'.format(dataset_name))
            self._validation_type = 'recall'  # Train & evaluate on the whole dataset
        else:
            # If there are multiple splits, concatenate them for _dataset and define indices
            if 'train' in split:
                try:
                    self._dataset = dataset_class(dataset_dir, split='train', download=True)
                except TypeError:
                    self._dataset = dataset_class(dataset_dir, train=True, download=True)
                self._train_indices = range(len(self._dataset))
            if 'validation' in split:
                try:
                    validation_data = dataset_class(dataset_dir, split='val', download=True)
                    validation_length = len(validation_data)
                    if self._dataset:
                        current_length = len(self._dataset)
                        self._dataset = torch.utils.data.ConcatDataset([self._dataset, validation_data])
                        self._validation_indices = range(current_length, current_length + validation_length)
                    else:
                        self._dataset = validation_data
                        self._validation_indices = range(validation_length)
                except ValueError:
                    raise ValueError('No validation split was found for this dataset: {}'.format(dataset_name))
            if 'test' in split:
                try:
                    test_data = dataset_class(dataset_dir, split='test', download=True)
                except TypeError:
                    try:
                        test_data = dataset_class(dataset_dir, train=False, download=True)
                    except ValueError:
                        raise ValueError('No test split was found for this dataset: {}'.format(dataset_name))
                finally:
                    test_length = len(test_data)
                    if self._dataset:
                        current_length = len(self._dataset)
                        self._dataset = torch.utils.data.ConcatDataset([self._dataset, test_data])
                        self._test_indices = range(current_length, current_length + test_length)
                    else:
                        self._dataset = test_data
                        self._validation_indices = range(test_length)
            self._validation_type = 'defined_split'  # Defined by user or torchvision
        self._make_data_loaders(batch_size=1)
        self._info = {'name': dataset_name, 'size': len(self._dataset)}

    @property
    def class_names(self):
        """
        Returns the list of class names
        """
        return self._dataset.classes

    @property
    def info(self):
        """
        Returns a dictionary of information about the dataset
        """
        return {'dataset_info': self._info, 'preprocessing_info': self._preprocessed}

    @property
    def dataset(self):
        """
        Returns the framework dataset object (torch.utils.data.Dataset)
        """
        return self._dataset
