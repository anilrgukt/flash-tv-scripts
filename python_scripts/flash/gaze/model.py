import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import torchvision.models as models
import numpy as np
from torch.nn.init import normal, constant
import math

from .resnet import resnet18, resnet34, resnet50




class GazeLSTM(nn.Module):
    def __init__(self):
        super(GazeLSTM, self).__init__()
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame

        self.base_model = resnet50(pretrained=False)

        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)

        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim,bidirectional=True,num_layers=2,batch_first=True)

        # The linear layer that maps the LSTM with the 3 outputs
        self.last_layer = nn.Linear(2*self.img_feature_dim, 3)


    def forward(self, input):

        base_out = self.base_model(input.view((-1, 3) + input.size()[-2:]))

        base_out = base_out.view(input.size(0),7,self.img_feature_dim)

        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:,3,:]
        output = self.last_layer(lstm_out).view(-1,3)


        angular_output = output[:,:2]
        angular_output[:,0:1] = math.pi*nn.Tanh()(angular_output[:,0:1])
        angular_output[:,1:2] = (math.pi/2)*nn.Tanh()(angular_output[:,1:2])

        var = math.pi*nn.Sigmoid()(output[:,2:3])
        var = var.view(-1,1).expand(var.size(0),2)

        return angular_output,var

class GazeLSTMreg(nn.Module):
    def __init__(self):
        super(GazeLSTMreg, self).__init__()
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame

        self.base_model = resnet34(pretrained=False)

        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)

        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim,bidirectional=True,num_layers=2,batch_first=True)

        # The linear layer that maps the LSTM with the 3 outputs
        self.last_layer = nn.Linear(2*self.img_feature_dim, 3)


    def forward(self, input):

        base_out = self.base_model(input.view((-1, 3) + input.size()[-2:]))

        base_out = base_out.view(input.size(0),7,self.img_feature_dim)

        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:,3,:]
        output = self.last_layer(lstm_out).view(-1,3)


        angular_output = output[:,:2]
        angular_output[:,0:1] = math.pi*nn.Tanh()(angular_output[:,0:1])
        angular_output[:,1:2] = (math.pi/2)*nn.Tanh()(angular_output[:,1:2])

        var = math.pi*nn.Sigmoid()(output[:,2:3])
        var = var.view(-1,1).expand(var.size(0),2)

        return angular_output,var



class GazeLSTMFlash(nn.Module):
    def __init__(self):
        super(GazeLSTMFlash, self).__init__()
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame

        self.base_model = resnet18(pretrained=True)

        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)

        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim,bidirectional=True,num_layers=2,batch_first=True)

        # The linear layer that maps the LSTM with the 3 outputs
        self.last_layer = nn.Linear(2*self.img_feature_dim, 3)
        
        self.flash_linlayer = nn.Linear(self.img_feature_dim, 32)
        self.flash_lastlayer = nn.Linear(32, 1)
        self.sigmoid = nn.Sigmoid()
        # from base model fc2 (256) -> 128 -> sigmoid()


    def forward(self, input):

        base_out = self.base_model(input.view((-1, 3) + input.size()[-2:]))

        base_out = base_out.view(input.size(0),7,self.img_feature_dim)

        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:,3,:]
        output = self.last_layer(lstm_out).view(-1,3)
        
        fc1 = self.flash_linlayer(base_out[:,3,:]).view(-1,32)
        fc1_relu = F.relu(fc1)
        
        fc2 = self.flash_lastlayer(fc1_relu).view(-1,1)
        fc2_sigmoid = self.sigmoid(fc2)
        
        angular_output = output[:,:2]
        angular_output[:,0:1] = math.pi*nn.Tanh()(angular_output[:,0:1])
        angular_output[:,1:2] = (math.pi/2)*nn.Tanh()(angular_output[:,1:2])

        var = math.pi*nn.Sigmoid()(output[:,2:3])
        var = var.view(-1,1).expand(var.size(0),2)

        return angular_output, var, fc2_sigmoid


class PinBallLoss(nn.Module):
    def __init__(self):
        super(PinBallLoss, self).__init__()
        self.q1 = 0.1
        self.q9 = 1-self.q1

    def forward(self, output_o,target_o,var_o): # (output, target_var,ang_error)
        q_10 = target_o-(output_o-var_o)
        q_90 = target_o-(output_o+var_o)

        loss_10 = torch.max(self.q1*q_10, (self.q1-1)*q_10)
        loss_90 = torch.max(self.q9*q_90, (self.q9-1)*q_90)
        

        loss_10 = torch.mean(loss_10)
        loss_90 = torch.mean(loss_90)

        return loss_10+loss_90

class PinBallLossFlash(nn.Module):
    def __init__(self):
        super(PinBallLossFlash, self).__init__()
        self.q1 = 0.1
        self.q9 = 1-self.q1
        self.bce = nn.BCELoss()

    def forward(self, output_o,target_o,var_o, pred_gaze, gt_gaze): # (output, target_var,ang_error, gazes)
        q_10 = target_o-(output_o-var_o)
        q_90 = target_o-(output_o+var_o)

        loss_10 = torch.max(self.q1*q_10, (self.q1-1)*q_10)
        loss_90 = torch.max(self.q9*q_90, (self.q9-1)*q_90)
        

        loss_10 = torch.mean(loss_10)
        loss_90 = torch.mean(loss_90)
        
        bce_loss = torch.mean(self.bce(pred_gaze, gt_gaze))

        return loss_10+loss_90+bce_loss

