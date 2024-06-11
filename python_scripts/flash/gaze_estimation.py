import os
import sys 
import torch
import numpy as np 
import math

from PIL import Image

import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import torchvision.models as models
import torchvision.utils as vutils

#sys.path.insert(1, './gaze/')
from .gaze.model import GazeLSTM, GazeLSTMreg

        

class FLASHGazeEstimator():
    def __init__(self, ckpt1_r50, ckpt2_r50reg, num_gaze_models=2, img_size=224, vid_res=7):
    
        checkpoint_r50 = ckpt1_r50 #'/home/'+os.getlogin()+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar'
        checkpoint_r50reg = ckpt2_r50reg #'/home/'+os.getlogin()+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50reg.pth.tar'
        cudnn.benchmark = True

        model_v = GazeLSTM()
        model = torch.nn.DataParallel(model_v).cuda()        
        checkpoint = torch.load(checkpoint_r50)
        print('epochs', checkpoint['epoch'])
        model.load_state_dict(checkpoint['state_dict'])
        model.eval()
                
        modelregv = GazeLSTMreg()
        modelreg = torch.nn.DataParallel(modelregv).cuda()
        checkpoint = torch.load(checkpoint_r50reg)
        print('epochs', checkpoint['epoch'])
        modelreg.load_state_dict(checkpoint['state_dict'])
        modelreg.eval()

        #self.gaze_models = [model, modelreg]
    
        #self.num_gaze_models = num_gaze_models      
        self.gaze_models = [model, modelreg] #gaze_models[0:num_gaze_models]  
        self.img_size = img_size
        self.vid_res = vid_res
        
        self.image_normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        self.image_transform = transforms.Compose([transforms.Resize((self.img_size, self.img_size)),transforms.ToTensor(),self.image_normalize,])
        
    def to_input(self, tc_images):
        source_video_7fps = torch.FloatTensor(self.vid_res,3,self.img_size,self.img_size) 
        
        if len(tc_images) == 1:
            tc_images = tc_images*7
        else:
            tc_images = [tc_images[0]]*3 + tc_images + [tc_images[-1]]*2
            
        for idx, im in enumerate(tc_images):        
            im = Image.fromarray(im)
            source_video_7fps[idx,...] = self.image_transform(im)
        
        source_video_7fps = source_video_7fps.view(self.vid_res*3,self.img_size,self.img_size)
        return source_video_7fps
        
    def gaze_estimate(self, source_video):
        source_video = torch.unsqueeze(source_video, 0)
        source_frame = source_video.cuda(non_blocking=True)
        
        with torch.no_grad():
            source_frame_var = torch.autograd.Variable(source_frame)
            #output = [m(source_frame_var) for m in self.gaze_models]
            output, ang_error = self.gaze_models[0](source_frame_var)
            output_, ang_error_ = self.gaze_models[1](source_frame_var)

        return [(output, ang_error), (output_, ang_error_)]


def load_limits(file_path, setting='center-big-med'):
    loc_lims = np.load(file_path) #'4331_v3r50reg_reg_testlims_35_53_7_9.npy')
    loc_lims = loc_lims.reshape(-1,4)
    
    pos, size, height = setting.split('-')

    drl = (loc_lims[:,1]-loc_lims[:,0])/2.0
    dtb = (loc_lims[:,3]-loc_lims[:,2])/2.0

    tbshift = 0 
    lrshift = 0 
    slr = 1.1
    stb = 1.1
    rls_sc = 0.0
    tbs_sc = 0.0

    if size=='big':
	    rls_sc = 0.3 #0.3
	    tbs_sc = 0.2 #0.2
	    tbshift = 0
	    stb = 1.1
    else:
	    rls_sc = 0.1
	    tbs_sc = 0.05
	    
    if pos=='left':
	    lrshift = 0
	    slr = 1.35 #1.25
	    
    if pos=='right':
	    lrshift = -0
	    slr = 1.35 #1.25
	    
    if pos=='center':
	    lrshift = -0
	    slr = 1.1 #1.25	
	    
    if pos!='center' and size=='small':
	    rls_sc = 0.2 #0.2
	    tbs_sc = 0.1 #0.1

    rls = drl*rls_sc
    tbs = dtb*tbs_sc

    #max height, tv large corners	bottom lims -10
    #max height, tv large center	bottom lims -7
    #least height, tv large	bottom lims -3
    tbshift=0 #15
    lrshift=0

    loc_lims[:,0] = slr*(loc_lims[:,0]) -rls + lrshift # left right lower lim and upper lim
    loc_lims[:,1] = slr*(loc_lims[:,1]) +rls + lrshift 

    loc_lims[:,2] = stb*(loc_lims[:,2]) -tbs + tbshift # top bottom lower lim upper lim
    loc_lims[:,3] = stb*(loc_lims[:,3]) +tbs + tbshift
    
    return loc_lims

def get_lims(bbox, num_locs, H, W):
    #H = 342; W = 608
    pH = 35 #35 # 57 # 21
    pW = 53 #53 # 100 # 31
    eH = 7  #7 # 17 # 3
    eW = 9  #9 # 23 # 3

    xH = 2
    xW = 2

    x, y = np.meshgrid(np.arange(0,W,pW), np.arange(0,H,pH)) # y varies along row, x varies along col
    y = y.reshape(-1)
    x = x.reshape(-1)
    
    assert y.size == num_locs #locs.shape[0]
    assert x.size == num_locs #locs.shape[0]
    
    leftl = x.copy()
    rightl = x.copy()+pW+xW 
    rightl[rightl>W] = W
	
    topl = y.copy()
    bottoml = y.copy()+pH+xH
    bottoml[bottoml>H] = H #, 342)
	
    colm = (bbox['left'] + bbox['right']) / 2 #(at[:,4] + at[:,6])/2
    rowm = (bbox['top'] + bbox['bottom']) / 2 #(at[:,5] + at[:,7])/2
    
    filter_col = np.logical_and(colm>leftl, colm<rightl)
    filter_row = np.logical_and(rowm>topl, rowm<bottoml)
    filter_ = np.logical_and(filter_col, filter_row)
    
    if not filter_.sum()<3:
        print('more than one gaze loc assigned', rowm, colm, filter_.sum(), filter_)
        #raise
    
    return np.where(filter_)[0][0]
    

def eval_thrshld(phi, theta, gt_lab, lims):
	gt_gaze = gt_lab.astype(np.int32)
	
	phi_min = phi > (lims[0]/180.0)*math.pi #-0.9
	phi_min_dist= phi - (lims[0]/180.0)*math.pi
	phi_max = phi < (lims[1]/180.0)*math.pi #0.9
	phi_max_dist= (lims[1]/180.0)*math.pi - phi
	
	phi_constraint_met = np.logical_and(phi_min, phi_max)
	
	phi_min_dist[phi_min_dist>0] = 0
	phi_min_dist = -1*phi_min_dist
	
	phi_max_dist[phi_max_dist>0] = 0
	phi_max_dist = -1*phi_max_dist
	phi_dist = phi_min_dist + phi_max_dist
	
	the_min = theta > (lims[2]/180.0)*math.pi #-.75
	the_min_dist = theta - (lims[2]/180.0)*math.pi
	the_max = theta < (lims[3]/180.0)*math.pi #0.1
	the_max_dist = (lims[3]/180.0)*math.pi - theta #0.1
	
	the_min_dist[the_min_dist>0] = 0
	the_min_dist = -1*the_min_dist

	the_max_dist[the_max_dist>0] = 0
	the_max_dist = -1*the_max_dist
	the_dist = the_min_dist + the_max_dist
	
	the_constraint_met = np.logical_and(the_min, the_max)	
	
	
	phi_theta_met = np.logical_and(the_constraint_met, phi_constraint_met)
	gaze_est = np.array(phi_theta_met)*1
	gaze_est = gaze_est.astype(np.int32)
	geval = gaze_est == gt_gaze
	acc = np.array(geval).sum()/float(phi.shape[0])*100
	cmatt = None #cm(gt_gaze, gaze_est, labels=[1,0])
	
	return acc, cmatt, gaze_est, phi_dist, the_dist
	

