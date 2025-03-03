#copyright (c) 2019 PaddlePaddle Authors. All Rights Reserve.
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.

import os
import functools
import numpy as np
import paddle
import paddle.fluid as fluid
import random

from img_tool import process_image
DATA_DIR=""

THREAD=4
BUF_SIZE=4000

def _reader_creator(settings,
                    file_list,
                    mode,
                    shuffle=False,
                    color_jitter=False,
                    rotate=False,
                    data_dir=DATA_DIR,
                    pass_id_as_seed=0):
    def reader():
        with open(file_list) as flist:
            full_lines = [line.strip() for line in flist]
            if shuffle:
                random.Random(pass_id_as_seed).shuffle(full_lines)
            
            if mode == 'train':
                trainer_id = int(os.getenv("PADDLE_TRAINER_ID", "0"))
                if os.getenv("PADDLE_TRAINER_ENDPOINTS"):
                    trainer_count = len(os.getenv("PADDLE_TRAINER_ENDPOINTS").split(","))
                else:
                    trainer_count = int(os.getenv("PADDLE_TRAINERS", "1"))

                per_node_lines = len(full_lines) // trainer_count
                lines = full_lines[trainer_id * per_node_lines:(trainer_id + 1)
                                   * per_node_lines]
                print("trainerid, trainer_count", trainer_id, trainer_count)
                print(
                    "read images from %d, length: %d, lines length: %d, total: %d"
                    % (trainer_id * per_node_lines, per_node_lines, len(lines),
                       len(full_lines)))
            else:
                print("mode is not train")
                lines = full_lines

            for line in lines:
                if mode == 'train':
                    img_path, label = line.split()
                    img_path = img_path.replace("JPEG", "jpeg")
                    img_path = os.path.join(data_dir, "train", img_path)
                    yield (img_path, int(label))
                elif mode == 'val':
                    img_path, label = line.split()
                    img_path = img_path.replace("JPEG", "jpeg")
                    img_path = os.path.join(data_dir, "val", img_path)
                    yield (img_path, int(label))
                elif mode == 'test':
                    img_path = os.path.join(data_dir, line)
                    yield [img_path]


    image_mapper = functools.partial(
        process_image,
        settings=settings,
        mode=mode,
        color_jitter=color_jitter,
        rotate=rotate,
        crop_size=224)
    reader = paddle.reader.xmap_readers(
        image_mapper, reader, THREAD, BUF_SIZE, order=False)
    return reader

def train(settings, data_dir=DATA_DIR, pass_id_as_seed=0):
    file_list = os.path.join(data_dir, 'train.txt')
    reader =  _reader_creator(
        settings,
        file_list,
        'train',
        shuffle=True,
        color_jitter=False,
        rotate=False,
        data_dir=data_dir,
        pass_id_as_seed=pass_id_as_seed,
        )
    return reader

def val(settings,data_dir=DATA_DIR):
    file_list = os.path.join(data_dir, 'val.txt')
    return _reader_creator(settings ,file_list, 'val', shuffle=False, 
            data_dir=data_dir)


def test(data_dir=DATA_DIR):
    file_list = os.path.join(data_dir, 'val.txt')
    return _reader_creator(file_list, 'test', shuffle=False,
            data_dir=data_dir)
