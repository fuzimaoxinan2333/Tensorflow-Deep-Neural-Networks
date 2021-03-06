# -*- coding: utf-8 -*-
import tensorflow as tf
import numpy as np
from rbms import DBM
import sys
sys.path.append("../base")
from model import Model
from base_func import act_func,Summaries

class DBN(Model):
    def __init__(self,
                 hidden_act_func='relu',
                 output_act_func='softmax',
                 loss_func='mse', # gauss 激活函数会自动转换为 mse 损失函数
                 struct=[784, 100, 100,10],
                 lr=1e-4,
                 momentum=0.5,
                 use_for='classification',
                 bp_algorithm='adam',
                 epochs=100,
                 batch_size=32,
                 dropout=0.3,
                 rbm_v_type='gauss',
                 rbm_lr=1e-3,
                 rbm_epochs=30,
                 cd_k=1):
        Model.__init__(self,'DBN')
        self.output_act_func=output_act_func
        self.hidden_act_func=hidden_act_func
        self.loss_func=loss_func
        self.use_for=use_for
        self.bp_algorithm=bp_algorithm
        self.lr=lr
        self.momentum=momentum
        self.epochs=epochs
        self.struct = struct
        self.batch_size = batch_size
        self.dropout = dropout
        
        self.dbm_struct = struct[:-1]
        
        self.rbm_v_type=rbm_v_type
        self.cd_k = cd_k
        self.rbm_lr = rbm_lr
        self.rbm_epochs = rbm_epochs
        
         
#        if rbm_v_type=='bin':
#            self.hidden_act_func='sigmoid'
#        elif rbm_v_type=='gauss':
#            self.hidden_act_func='affine'
            
        if output_act_func=='gauss':
            self.loss_func='mse'
        self.hidden_act=act_func(self.hidden_act_func)
        self.output_act=act_func(self.output_act_func)
        
        self.build_model()
        
    ###################
    #    DBN_model    #
    ###################
    
    def build_model(self):
        print("Start building model...")
        print('DBN:')
        print(self.__dict__)
        """
        Pre-training
        """
        # 构建dbm
        self.pt_model = DBM(rbm_v_type=self.rbm_v_type,
                       dbm_struct=self.dbm_struct,
                       rbm_epochs=self.rbm_epochs,
                       batch_size=self.batch_size,
                       cd_k=self.cd_k,
                       rbm_lr=self.rbm_lr)      
        """
        Fine-tuning
        """
        with tf.name_scope('DBN'):
            # feed 变量
            self.input_data = tf.placeholder(tf.float32, [None, self.struct[0]]) # N等于batch_size（训练）或_num_examples（测试）
            self.label_data = tf.placeholder(tf.float32, [None, self.struct[-1]]) # N等于batch_size（训练）或_num_examples（测试）
            self.keep_prob = tf.placeholder(tf.float32) 
            # 权值 变量（初始化）
            self.out_W = tf.Variable(tf.truncated_normal(shape=[self.struct[-2], self.struct[-1]], stddev=np.sqrt(2 / (self.struct[-2] + self.struct[-1]))), name='W_out')
            self.out_b = tf.Variable(tf.constant(0.0,shape=[self.struct[-1]]),name='b_out')
            # 构建dbn
            # 构建权值列表（dbn结构）
            self.parameter_list = list()
            for pt in self.pt_model.pt_list:
                self.parameter_list.append(pt.W)
                self.parameter_list.append(pt.bh)
            self.parameter_list.append(self.out_W)
            self.parameter_list.append(self.out_b)
            
            # 构建训练步
            self.pred=self.transform(self.input_data)
            self.build_train_step()
            
            #****************** 记录 ******************
            cnt=2
            for i in range(len(self.parameter_list)):
                if i%cnt!=0:continue
                k=int(i/cnt+1)
                Summaries.scalars_histogram('_W'+str(k),self.parameter_list[i])
                Summaries.scalars_histogram('_b'+str(k),self.parameter_list[i+1])
            tf.summary.scalar('loss',self.loss)
            tf.summary.scalar('accuracy',self.accuracy)
            self.merge = tf.summary.merge(tf.get_collection(tf.GraphKeys.SUMMARIES,'DBN'))
            #******************************************
            
    def transform(self,data_x):
        cnt=2
        # 得到网络输出值
        next_data = data_x # 这个next_data是tf变量
        for i in range(len(self.parameter_list)):
            if i%cnt!=0:continue
            W=self.parameter_list[i]
            b=self.parameter_list[i+1]
            
            if self.dropout>0:
                next_data = tf.nn.dropout(next_data, self.keep_prob)
                
            z = tf.add(tf.matmul(next_data, W), b)
            if i==len(self.parameter_list)-cnt:
                next_data=self.output_act(z)
            else:
                next_data=self.hidden_act(z)
            
        return next_data