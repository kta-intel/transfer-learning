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

import os
import tensorflow as tf

from tlt.datasets.tf_dataset import TFDataset
from tlt.datasets.image_classification.image_classification_dataset import ImageClassificationDataset


class TFCustomImageClassificationDataset(ImageClassificationDataset, TFDataset):
    """
    A custom image classification dataset that can be used with TensorFlow models. Note that the
    directory of images is expected to be organized with subfolders for each image class. Each subfolder should
    contain .jpg images for the class. The name of the subfolder will be used as the class label.

    .. code-block:: text

        dataset_dir
          ├── class_a
          ├── class_b
          └── class_c

    Args:
        dataset_dir (str): Directory where the data is located. It should contain subdirectories with images for
                           each class.
        dataset_name (str): optional; Name of the dataset. If no dataset name is given, the dataset_dir folder name
                            will be used as the dataset name.
        color_mode (str): optional; Specify the color mode as "greyscale", "rgb", or "rgba". Defaults to "rgb".
        shuffle_files (bool): optional; Whether to shuffle the data. Defaults to False.
        seed (int): optional; Random seed for shuffling

    Raises:
        FileNotFoundError if dataset directory does not exist

    """

    def __init__(self, dataset_dir, dataset_name=None, color_mode="rgb", shuffle_files=False, seed=None):
        """
        Class constructor
        """
        if not os.path.exists(dataset_dir):
            raise FileNotFoundError("The dataset directory ({}) does not exist".format(dataset_dir))

        # The dataset name is only used for informational purposes. If one isn't given, use the directory name
        if not dataset_name:
            dataset_name = os.path.basename(dataset_dir)

        ImageClassificationDataset.__init__(self, dataset_dir, dataset_name, dataset_catalog=None)

        self._info = {
            "name": dataset_name,
            "dataset_dir": dataset_dir,
            "color_mode": color_mode
        }
        self._preprocessed = None

        self._dataset = tf.keras.utils.image_dataset_from_directory(
            self._dataset_dir,
            batch_size=None,
            shuffle=shuffle_files,
            seed=seed,
            color_mode=color_mode)
        self._class_names = self._dataset.class_names

        self._train_pct = 1.0
        self._val_pct = 0
        self._test_pct = 0
        self._validation_type = 'recall'
        self._train_subset = None
        self._validation_subset = None
        self._test_subset = None

    @property
    def class_names(self):
        """
        Returns the list of class names
        """
        return self._class_names

    @property
    def info(self):
        """
        Returns a dictionary of information about the dataset
        """
        return {'dataset_info': self._info, 'preprocessing_info': self._preprocessed}

    @property
    def dataset(self):
        """
        Returns the framework dataset object (tf.data.Dataset)
        """
        return self._dataset

    def preprocess(self, image_size, batch_size):
        """
        Preprocess the dataset to convert to float32, resize, and batch the images

            Args:
                image_size (int): desired square image size
                batch_size (int): desired batch size

            Raises:
                ValueError if the dataset is not defined or has already been processed
        """
        if self._preprocessed:
            raise ValueError("Data has already been preprocessed: {}".format(self._preprocessed))

        if not isinstance(batch_size, int) or batch_size < 1:
            raise ValueError("batch_size should be an positive integer")

        if not isinstance(image_size, int) or image_size < 1:
            raise ValueError("image_size should be an positive integer")

        normalization_layer = tf.keras.layers.Rescaling(1. / 255)

        def preprocess_image(image, label):
            image = tf.image.resize_with_pad(image, image_size, image_size)
            image = normalization_layer(image)
            return (image, label)

        if not (self._dataset or self._train_subset or self._validation_subset or self._test_subset):
            raise ValueError("Unable to preprocess, because the dataset hasn't been defined.")

        # Get the non-None splits
        split_list = ['_dataset', '_train_subset', '_validation_subset', '_test_subset']
        subsets = [s for s in split_list if getattr(self, s, None)]
        for subset in subsets:
            if not self._preprocessed:
                setattr(self, subset, getattr(self, subset).map(preprocess_image))
                setattr(self, subset, getattr(self, subset).cache())
            setattr(self, subset, getattr(self, subset).batch(batch_size))
            setattr(self, subset, getattr(self, subset).prefetch(tf.data.AUTOTUNE))
        self._preprocessed = {'image_size': image_size, 'batch_size': batch_size}
