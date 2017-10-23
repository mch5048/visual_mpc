import collections

import numpy as np
import tensorflow as tf
from tensorflow.contrib.layers import layer_norm

from python_visual_mpc.video_prediction.dynamic_rnn_model.layers import instance_norm
from python_visual_mpc.video_prediction.dynamic_rnn_model.lstm_ops import BasicConv2DLSTMCell
from python_visual_mpc.video_prediction.dynamic_rnn_model.ops import dense, pad2d, conv1d, conv2d, conv3d, upsample_conv2d, conv_pool2d, lrelu, instancenorm, flatten
from python_visual_mpc.video_prediction.dynamic_rnn_model.ops import sigmoid_kl_with_logits
from python_visual_mpc.video_prediction.dynamic_rnn_model.utils import preprocess, deprocess
from python_visual_mpc.video_prediction.basecls.utils.visualize import visualize_diffmotions, visualize
from python_visual_mpc.video_prediction.basecls.utils.compute_motion_vecs import compute_motion_vector_cdna, compute_motion_vector_dna

import pdb
from docile.improved_dna_model import create_model

class Base_Prediction_Model(object):
    def __init__(self,
                conf = None,
                trafo_pix = True,
                load_data = True,
                ):

        modelconfiguration = conf['modelconfiguration']

        self.iter_num = tf.placeholder(tf.float32, [])

        self.trafo_pix = trafo_pix
        self.conf = conf

        self.batch_size = conf['batch_size']

        self.train_cond = tf.placeholder(tf.int32, shape=[], name="train_cond")
        self.sdim = conf['sdim']
        self.adim = conf['adim']

        if not load_data:
            self.actions_pl = tf.placeholder(tf.float32, name='actions',
                                             shape=(conf['batch_size'], conf['sequence_length'], self.adim))
            actions = self.actions_pl

            self.states_pl = tf.placeholder(tf.float32, name='states',
                                            shape=(conf['batch_size'], conf['sequence_length'], self.sdim))
            states = self.states_pl

            self.images_pl = tf.placeholder(tf.float32, name='images',
                                            shape=(conf['batch_size'], conf['sequence_length'], 64, 64, 3))
            images = self.images_pl

            self.pix_distrib_pl = tf.placeholder(tf.float32, name='states',
                                                 shape=(conf['batch_size'], conf['sequence_length'], 64, 64, 1))
            pix_distrib1 = self.pix_distrib_pl

        else:
            if 'adim' in conf:
                from python_visual_mpc.video_prediction.read_tf_record_wristrot import \
                    build_tfrecord_input as build_tfrecord_fn
            else:
                from python_visual_mpc.video_prediction.read_tf_record_sawyer12 import \
                    build_tfrecord_input as build_tfrecord_fn
            train_images, train_actions, train_states = build_tfrecord_fn(conf, training=True)
            val_images, val_actions, val_states = build_tfrecord_fn(conf, training=False)

            images, actions, states = tf.cond(self.train_cond > 0,  # if 1 use trainigbatch else validation batch
                                              lambda: [train_images, train_actions, train_states],
                                              lambda: [val_images, val_actions, val_states])

        if 'use_len' in conf:
            print 'randomly shift videos for data augmentation'
            images, states, actions  = self.random_shift(images, states, actions)

        ## start interface

        if not trafo_pix:
            self.model = create_model(images, actions, states, **modelconfiguration)
        else:
            self.model = create_model(images, actions, states, pix_distrib1, **modelconfiguration)

        for key in self.model.__dict__.keys():
            #copy all the placeholders attributes to the current object
            setattr(self, key, self.model.__dict__[key])

    def visualize(self, sess):
        visualize(sess, self.conf, self)

    def visualize_diffmotions(self, sess):
        visualize_diffmotions(sess, self.conf, self)


    def random_shift(self, images, states, actions):
        print 'shifting the video sequence randomly in time'
        tshift = 2
        uselen = self.conf['use_len']
        fulllength = self.conf['sequence_length']
        nshifts = (fulllength - uselen) / 2 + 1
        rand_ind = tf.random_uniform([1], 0, nshifts, dtype=tf.int64)
        self.rand_ind = rand_ind

        start = tf.concat(axis=0, values=[tf.zeros(1, dtype=tf.int64), rand_ind * tshift, tf.zeros(3, dtype=tf.int64)])
        images_sel = tf.slice(images, start, [-1, uselen, -1, -1, -1])
        start = tf.concat(axis=0, values=[tf.zeros(1, dtype=tf.int64), rand_ind * tshift, tf.zeros(1, dtype=tf.int64)])
        actions_sel = tf.slice(actions, start, [-1, uselen, -1])
        start = tf.concat(axis=0, values=[tf.zeros(1, dtype=tf.int64), rand_ind * tshift, tf.zeros(1, dtype=tf.int64)])
        states_sel = tf.slice(states, start, [-1, uselen, -1])

        return images_sel, states_sel, actions_sel