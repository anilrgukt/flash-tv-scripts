#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on  Nov 03 14:57:35 2020

@author: anil
"""

import os
#os.environ["CUDA_VISIBLE_DEVICES"]="0"
import sys
import random
import subprocess
import threading as th
from queue import Queue

from flash_utils import *

usrname = str(sys.argv[4]) #os.getlogin()

# face detection libs
sys.path.insert(1, os.path.join('/home/'+usrname+'/insightface/detection/RetinaFace'))
from retinaface import RetinaFace
gpuid = 0
detector = RetinaFace('/home/'+usrname+'/insightface/detection/RetinaFace/model/retina', 0, gpuid, 'net3', vote=False)



def face_detector(img, threshold=None):
	#print('fwd pass through the detector')
	if threshold is None:
		det_thresh = 0.15
	else:
		det_thresh = threshold #0.15
	#scales = [1024, 1980]
	#det_scales = [480, 720]
	det_scales = [720, 1280] # 720, 1280
	#scales = [608, 1080]
	#det_res_img = [480, 720]
	det_res_img = [720, 1280]
	#res_img = [480, 720]
	det_write_img = [342, 608]
	dhsc, dwsc = [det_write_img[0]/720.0, det_write_img[1]/1280.0]
	#dhsc, dwsc = [det_write_img[0]/480.0, det_write_img[1]/720.0]
	det_scales = [1.0]
	
	img = cv2.resize(img, (det_res_img[1], det_res_img[0]))
	#print('FWD pass thorugh detector .....')
	faces, landmarks = detector.detect(img,
	                                   det_thresh,
	                                   det_scales,
	                                   do_flip=False)
	bbox_ls = []
	if faces is not None:
		for i in range(faces.shape[0]):
			score = faces[i,4]
			box = faces[i,:4]*np.array([dwsc, dhsc, dwsc, dhsc])
			lmarks = landmarks[i]*np.array([dwsc, dhsc]).reshape(1,2)

			box = box.astype(np.int32)
			lmarks = lmarks.astype(np.int32)

			bbox_ls.append({'left': box[0], 'top': box[1], 'right': box[2], 'bottom': box[3], 'prob': score, 'lmarks':lmarks})
		
	return bbox_ls


# face verification libs

sys.path.insert(1, '/home/'+usrname+'/insightface/deploy')
import face_model

model_ = '/home/'+usrname+'/insightface/models/model-r100-ii/model,0'
vec = model_.split(',')
model_prefix = vec[0]
model_epoch = int(vec[1])
gpuid = 0
fmodel = face_model.FaceModelv2(gpuid, model_prefix, model_epoch, batch_size=45, use_large_detector=False)

# gaze estimation libs
sys.path.insert(1, '/home/'+usrname+'/FLASH_TV/gaze_codes')
import torch.nn as nn
import torch.nn.parallel
import torch.backends.cudnn as cudnn
import torch.optim
import torch.utils.data
import torchvision.transforms as transforms
import torchvision.datasets as datasets
import torchvision.models as models
import torchvision.utils as vutils
from model import GazeLSTM, GazeLSTMreg

# image libs
import cv2
import imageio as io
from skimage.transform import resize
from skimage import exposure
from PIL import Image
#from utils import resize_image
#import KCF

# import python libs 
import glob
from datetime import datetime	
import time
import numpy as np
import pickle
import argparse
import math
import time

imgSize = [1080, 1920]
detImgSize = [342, 608]
bboxScale = [ imgSize[i] /  float(detImgSize[i]) for i in range(2)]
hsc = bboxScale[0]
wsc = bboxScale[1]

# new fv model 
import net

adaface_models = {
    #'ir_50':"pretrained/adaface_ir50_ms1mv2.ckpt",
    'ir_101':"/home/"+usrname+"/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt",
}

def load_pretrained_model(architecture='ir_101'):
    # load model and pretrained statedict
    assert architecture in adaface_models.keys()
    model = net.build_model(architecture)
    statedict = torch.load(adaface_models[architecture])['state_dict']
    model_statedict = {key[6:]:val for key, val in statedict.items() if key.startswith('model.')}
    model.load_state_dict(model_statedict)
    return model

def to_input(rgb_image):
    #np_img = np.array(pil_rgb_image)
    assert rgb_image.max()>1.0
    brg_img = ((rgb_image[:,:,:,::-1] / 255.) - 0.5) / 0.5 # h,w,3 --> B,h,w,3
    #tensor = torch.tensor(brg_img.transpose(0,3,1,2)).float() # 3,h,w --> B,c,h,w
    brg_img = brg_img.transpose(0,3,1,2)
    tensor = torch.from_numpy(brg_img).float().to(device='cuda:0')
    #tensor.to('cuda:0')
    #print(tensor.device, tensor.size())
    return tensor

nmodel = load_pretrained_model('ir_101')
nmodel.cuda()
#nmodel.to('cuda:0')
nmodel.eval()

def get_gt_emb(model, nmodel, fam_id, path, emb_size, img_size=112):

	person_ids = ['tc', 'sib', 'parent', 'poster']
	person_nums = ['1', '2', '3', '4', '5', '5']
	fnames = [fam_id + '_' + i for i in person_ids]
		
	gt_fname = []
	for i in person_nums:
		for j in fnames:
			gt_fname.append(j+i+'.png')

	#gt_fname = ['401_tc.png','401_sib.png','401_parent.png','401_poster.png',
	#			'401_tc2.png','401_sib2.png','401_parent2.png','401_poster2.png',
	#			'401_tc3.png','401_sib3.png','401_parent3.png','401_poster3.png',
	#			'401_tc4.png','401_sib4.png','401_parent4.png','401_poster4.png',
	#			'401_tc5.png','401_sib5.png','401_parent5.png','401_poster5.png']
	gt_fname = [str(fam_id)+'_faces/' + i for i in gt_fname]
	gt_faces = []
	for fname in gt_fname:
		face = io.imread(os.path.join(path, fname))
		face = resize(face, (img_size, img_size))
		face = np.uint8(255*face)
		#print(face.min(), face.max())
		
		#face = (face - 127.5) / 128.0
		#print(face.max(), face.min())
		face_flip = face[:,::-1,:]
		gt_faces.append(face)
		gt_faces.append(face_flip)

	gt_faces = np.array(gt_faces)

	embedding_size = emb_size #int(embeddings.get_shape()[1])
	gt_embedding = np.zeros((len(gt_fname), embedding_size*1))

	# GET GT FEATURES
	gt_faces_inp = gt_faces.copy()
	for idx, face_img in enumerate(gt_faces_inp):
		#print(idx)
		gt_faces_inp[idx] = model.get_input(face_img, face=False)
		cv2.imwrite('./gt_faces_inp/'+str(idx).zfill(3)+'.png', gt_faces_inp[idx][:,:,::-1])
		
	emb_gt1,n1 = nmodel(to_input(gt_faces_inp[:24,:,:,:]))
	emb_gt1 = emb_gt1.cpu().detach().numpy()
	n1 = n1.cpu().detach().numpy()
	emb_gt2,n2 = nmodel(to_input(gt_faces_inp[24:,:,:,:]))
	emb_gt2 = emb_gt2.cpu().detach().numpy()
	n2 = n2.cpu().detach().numpy()
	
	#emb_gt = emb_gt1*n1 + emb_gt2*n2#np.concatenate((emb_gt1,emb_gt2), axis=0)
	emb_gt = np.concatenate((emb_gt1*n1,emb_gt2*n2), axis=0)
	
	print('GT data ....')
	print(gt_faces_inp.shape, emb_gt.shape)

	#gt_embedding[:, :embedding_size] = emb_gt[0::2,:]
	#gt_embedding[:, embedding_size:] = emb_gt[1::2,:]
	gt_embedding = emb_gt[0::2,:] + emb_gt[1::2,:]

	gt_faces = gt_faces[0::2,:,:,:]


	return gt_embedding

def cam_id():
	dev_list = subprocess.Popen('v4l2-ctl --list-devices'.split(), shell=False, stdout=subprocess.PIPE)
	out, err = dev_list.communicate()
	out = out.decode()
	dev_paths = out.split('\n')
	dev_path = None

	# WEBCAM_NAME = 'HD Pro Webcam C920' # Logitech Webcam C930e
	WEBCAM_NAME = 'Logitech Webcam C930e'
	
	for i in range(len(dev_paths)):
		#print(i, dev_paths[i])
		if WEBCAM_NAME in dev_paths[i]:
		    dev_path = dev_paths[i+1].strip()
		    #print(dev_path, dev_path[-1])

	if dev_path is not None:
		cam_idx = int(dev_path[-1])	
	else:
		cam_idx = -1
		
	print('CAMER identified at: ', cam_idx)
	return cam_idx

embedding_size = 512

distance_metric = 1
threshold = 0.436
gal_add_thrshld = 0.3
subtract_mean = True
save_feat = True
mean = 0 #np.load('mean_lfw_1.npy')


######### gaze initialization
visualize = False
#checkpoint_test = '/media/xuchen/DATA/code_sos/FLASH_TV/gaze_codes/gaze360_model.pth.tar' # gc2_model_best_Gaze360.pth.tar, gaze360_model.pth.tar, gc3_model_best_Gaze360.pth.tar
#checkpoint_test = '/media/xuchen/DATA/code_sos/FLASH_TV/gaze_codes/model_v2_best_Gaze360.pth.tar' # gc2_model_best_Gaze360.pth.tar, gaze360_model.pth.tar
#checkpoint_test = '/media/xuchen/DATA/code_sos/FLASH_TV_v2/gaze_models/checkpoint_v3_r50regAdda.pth.tar' # gc2_model_best_Gaze360.pth.tar, gaze360_model.pth.tar
checkpoint_r50 = '/home/'+usrname+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar'
checkpoint_r50reg = '/home/'+usrname+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50reg.pth.tar'
#checkpoint_test = '/media/xuchen/DATA/code_sos/FLASH_TV_v2/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar'
network_name = 'Gaze360'

model_v = GazeLSTM()
model = torch.nn.DataParallel(model_v).cuda()
model.cuda()
checkpoint = torch.load(checkpoint_r50)
print('epochs', checkpoint['epoch'])
model.load_state_dict(checkpoint['state_dict'])
model.eval()


modelregv = GazeLSTMreg()
modelreg = torch.nn.DataParallel(modelregv).cuda()
modelreg.cuda()
checkpoint = torch.load(checkpoint_r50reg)
print('epochs', checkpoint['epoch'])
modelreg.load_state_dict(checkpoint['state_dict'])
modelreg.eval()

cudnn.benchmark = True

image_normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
image_transform = transforms.Compose([transforms.Resize((224,224)),transforms.ToTensor(),image_normalize,])


########

### cam capture 

def frame_write(q, frm_count):
	idx = cam_id()
	cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
	codec = cv2.VideoWriter_fourcc('M','J','P','G')
	cap.set(6, codec)
	cap.set(5, 30)

	cap.set(3, 1920)
	cap.set(4, 1080)

	fps = int(cap.get(5))
	#print('fps: ', fps)

	count = frm_count
	write_img = True

	global stop_capture
	stop_capture = False
	
	t_st = time.time()
	timer_sec = 0
	last_frame_time = None
	fps_count = 1
	data_list = []
	
	while(cap.isOpened() and not stop_capture): 
		ret, frame = cap.read()
		frame_time = cap.get(cv2.CAP_PROP_POS_MSEC)
		time_now = datetime.now()
		
		if last_frame_time is not None:
			timer_sec = timer_sec + (frame_time - last_frame_time)
			fps_count += 1

		if not ret:
			break
			
		if timer_sec >= 1940 and timer_sec <=2060:
			write_img = not write_img
			timer_sec = 0

		
		if write_img:
			data_list.append([frame, count, time_now])
			#cv2.imwrite(os.path.join(frm_write_path, str(count).zfill(6)+'.png')
		
		if len(data_list)==7:
			a = q.put(data_list)
			write_img = not write_img
			data_list = []
			
		count += 1
		
		if (count+1)%1000 == 0:
			tmp = 10
			print('time for captuing 1000 images:::: ', time.time()-t_st)
			t_st = time.time()
			#break
		
		last_frame_time = frame_time
	
	print('The cam for batch processing is stopped.')
	cap.release()
	cv2.destroyAllWindows()


def write_log_file(log_fname, write_line):
	fid = open(log_fname,'a')
	write_line = [str(l) for l in write_line]
	write_line = ' '.join(write_line)
	write_line = write_line + '\n'
	fid.write(write_line)
	fid.close()
	
######### check face presence:
def check_face_presence(log_file):
	print('CHECKING FACE presence')
	face_p_duration = 0
	face_np_duration = 0
	face_np_time_delay = 0.5 # num secs
	
	idx = cam_id()
	video_reader = WebcamVideoStream()
	video_reader.start(idx, width=608, height=342)

	'''
	cap_yolo = cv2.VideoCapture(idx)
	cap_yolo.set(3, 608)
	cap_yolo.set(4, 342)
	cap_yolo.set(5, 3)
	'''
	
	#cap.set(5, 15)
	#fps = int(cap_yolo.get(5))
	#print('Streaming for Face detection at {}x{} res. for {} FPS'.format(608,342,fps))
	
	frm_counter = log_file[1]
	fname_log = log_file[0]
	
	while face_p_duration < 1:
		#ret, img_cap = cap_yolo.read()
		#retr = cap_yolo.grab()
		#ret, img_cap = cap_yolo.retrieve(retr)
		img_cap = video_reader.read()
		img_cap_time = datetime.now()
		
		#print('starting face det .... ')
		dboxes = face_detector(img_cap) # face detection 
		
		#DELETE very low confidence faces if any
		ndboxes = []
		for b in dboxes:
			if b['prob'] > 0.09: 
				ndboxes.append(b)
		dboxes = ndboxes
		
		write_line = [img_cap_time, str(frm_counter).zfill(6)]
		write_line = write_line + [str(len(dboxes)), str(0), str(None), str(None), str(None), str(None), str(None), str(None), str(None)]
		if len(dboxes) < 1: # if no faces continue
			print('Face detector LOG ouput', img_cap_time, np.array([None, None]), 'No face detected')
			if face_np_duration > 45:
				face_np_time_delay = 1.03*face_np_time_delay
				face_np_time_delay = min(15.0, face_np_time_delay)

			face_np_duration += 1
			write_line.append('No-face-detected')
		else:
			face_p_duration += 1 
			print('Face detector LOG ouput', img_cap_time, np.array([None, None]), 'Init face detected')
			face_np_time_delay = 0.3
			write_line.append('Face-detected')
			
		write_log_file(fname_log, write_line)
		time.sleep(face_np_time_delay)
		frm_counter += 1
		
		imgr = cv2.resize(img_cap, (608,342))
		detimg = draw_rect_det(imgr[:,:,::-1], dboxes, 'tmp_det.png')
	
	#cap_yolo.release()
	video_reader.stop()
	cv2.destroyAllWindows()
	log_file[1] = frm_counter

	return face_p_duration, log_file

# (sess_det, gt_embedding, embeddings, img_batch, train_placeholder, dboxes, img_cap, det_thrshld, ver_thrshld)
def face_rec_one_image(model, newfmodel, gt_embedding, dboxes, img, det_thrshld, ver_thrshld):
	
	img = img[:,:,::-1] #to rgb
	detFacesLog = []
	bboxFaces = []
	for detface in dboxes:
		if area(detface)>35.00 and detface['prob']>=det_thrshld:
			face, [nsW,nsH,offW,offH,sl,st] = get_face(img, detface, wsc, hsc)
			
			if detface['lmarks'] is not None:
				#print(detface)
				facelmarks = detface['lmarks'] - np.array([detface['left'], detface['top']]).reshape(1,2)
				facelmarks[:,0] = wsc*(facelmarks[:,0] + int(sl>=0)*5) + offW #nsW*(wsc*facelmarks[:,0]+offW).astype(np.int)
				facelmarks[:,1] = hsc*(facelmarks[:,1] + int(st>=0)*5) + offH #nsH*(hsc*facelmarks[:,1]+offH).astype(np.int)
				
				ch, cw = face.shape[0], face.shape[1]
				facelmarks[:,0] = 112*(facelmarks[:,0]/float(cw))
				facelmarks[:,1] = 112*(facelmarks[:,1]/float(ch))
				
				face = resize(face, [112, 112])
				#print('after res', face.max(), face.min())
				face = np.uint8(255*face)
				#print(face.shape)
				
				facen = model.get_input(face, facelmarks.astype(np.int).reshape(1,5,2), face=True)
				
			else:
				facen = face.copy()			
			
			
			#print('det face', face.max(), face.min())
			face_flip = facen[:,::-1,:]
			detFacesLog.append(facen)
			detFacesLog.append(face_flip)
			bboxFaces.append(detface)
	
	#del img
	det_emb = np.zeros((int(len(detFacesLog)/2), embedding_size))
	detFacesLog = np.array(detFacesLog)
	
	if detFacesLog.shape[0]>0:

		emb_det = []
		local_bsize = 7
		for fe_id in range(0,detFacesLog.shape[0],local_bsize):
			detFaceBatch = detFacesLog[fe_id:fe_id+local_bsize]
			
			#feed_dict = {face_batch: detFaceBatch, face_train_placeholder: False}
			#emb_batch = sess_ver.run(face_embeddings, feed_dict=feed_dict)
			#emb_batch = model.get_feature(detFaceBatch)
			
			emb_batch, norm = newfmodel(to_input(detFaceBatch))
			emb_batch = emb_batch*norm
			emb_batch = emb_batch.cpu().detach().numpy()

			emb_det.append(emb_batch)

		emb_det = np.vstack(emb_det)

		det_emb[:, :embedding_size] = emb_det[0::2,:] + emb_det[1::2,:]
		#det_emb[:, embedding_size:] = emb_det[1::2,:]

		#print('det embedding', det_emb.shape)
		dist = dist_mat(gt_embedding, det_emb, mean)
		detFacesLog = detFacesLog[0::2,:,:,:]
	else:
		dist = np.array([]) #np.ones((1,gt_embedding.shape[0]))

	dist_cmp = np.array([])
	ni = 4
	if dist.shape[0]>0:
		dist_res = np.copy(dist) - ver_thrshld
		dist_res[dist_res>0] = 0
		dist_res = -(dist_res)
		#print(dist_cmp)
		dist_cmp = dist_res[:, :ni] + dist_res[:, ni:ni*2] + dist_res[:, ni*2:ni*3] + \
					dist_res[:, ni*3:ni*4] + dist_res[:, ni*4:ni*5] + dist_res[:, ni*5:ni*6]
					
	tc_presence = False
	
	idxs = [0,1,2,3] 
	for i in range(dist_cmp.shape[0]):
		di = dist_cmp[i]
		idx = di.argmax()
		if (idx in idxs) and dist_cmp[:,idx].max()<=di[idx] and di[idx]>0: # 
			bboxFaces[i]['idx'] = idx
			if idx==0:
				tc_presence = True
				#break
			idxs.remove(idx)
		else:
			if len(bboxFaces)>0:
				bboxFaces[i]['idx'] = 4
	
	imgr = cv2.resize(img, (608,342))
	verimg = draw_rect_ver(imgr, bboxFaces, None, 'tmp_fv.png')
	return tc_presence, verimg

	
######### Check the TC presence using single image captures with delays 
# (yolo_model, gt_embedding, embeddings, sess, image_batch, phase_train_placeholder, det_thrshld=.11, ver_thrshld=0.37)
def check_tc_presence(model, newfmodel, gt_embedding, log_file, det_thrshld, ver_thrshld):
	print('CHECKING TC presence')
	face_dur, log_file = check_face_presence(log_file)
	
	frm_counter = log_file[1]
	fname_log = log_file[0]

	tc_p_duration = 0
	tc_np_duration = 0
	face_p_duration = 0
	face_np_duration = 0
	
	tc_np_time_delay = 0.5 # num secs

	# faces were deteted continuously for so and so time 
	# Now run streaming at 1080p
	idx = cam_id()
	video_reader = WebcamVideoStream()
	video_reader.start(idx, width=1920, height=1080, fps=5)

	'''
	cap = cv2.VideoCapture(idx)
	cap.set(3, 1920)
	cap.set(4, 1080)
	cap.set(5, 5)
	fps = int(cap.get(5))
	print('Streaming for TC face detection at {}x{} res. for {} FPS'.format(1920,1080,fps))
	'''
	
	tc_present = False
	while tc_p_duration < 0:
		#ret, img_cap = cap.read()
		
		#retr = cap.grab()
		#ret, img_cap = cap.retrieve(retr)
		img_cap = video_reader.read()
		img_cap_time = datetime.now()
		
		#imgr = cv2.resize(img_cap, (608,342))
		dboxes = face_detector(img_cap) # face detection 
		
		#DELETE very low confidence faces if any
		ndboxes = []
		for b in dboxes:
			if b['prob'] > 0.09: 
				ndboxes.append(b)
		dboxes = ndboxes
		
		write_line = [img_cap_time, str(frm_counter).zfill(6)]
		if len(dboxes) < 1: # if no faces continue
			print(img_cap_time, np.array([None, None]), 'No face detected')
			write_line = write_line + [str(len(dboxes)), str(0), str(None), str(None), str(None), str(None), str(None), str(None), str(None)]
			write_line.append('No-face-detected')
			
			face_np_duration += 1

			if face_np_duration > 100:
				#cap.release()
				video_reader.stop()
				face_dur = check_face_presence(log_file)
				
				idx = cam_id()
				video_reader = WebcamVideoStream()
				video_reader.start(idx, width=1920, height=1080, fps=5)
				
				
				'''
				cap = cv2.VideoCapture(idx)
				cap.set(3, 1920)
				cap.set(4, 1080)
				cap.set(5, 5)
				fps = int(cap.get(5))
				'''
		else:
			face_p_duration += 1 
			# face_rec_one_image(model, gt_embedding, dboxes, img, det_thrshld, ver_thrshld):
			tc_present, verimg = face_rec_one_image(fmodel, newfmodel, gt_embedding, dboxes, img_cap, det_thrshld, ver_thrshld)
			#print(img_cap_time, tc_present, tc_np_time_delay)
		
			if tc_present:
				tc_p_duration += 1
				tc_np_time_delay = 0.2
				print('Face verifier LOG ouput', img_cap_time, np.array([None, None]), 'TC present initial')
				write_line = write_line + [str(len(dboxes)), str(1), str(None), str(None), str(None), str(None), str(None), str(None), str(None)]
				write_line.append('TC-face-detected')
			else:	
				tc_np_duration += 1
				if tc_np_duration > 100:
					tc_np_time_delay = 1.05*tc_np_time_delay
					tc_np_time_delay = min(25.0, tc_np_time_delay)
					
				print('Face verifier LOG ouput', img_cap_time, np.array([None, None]), 'TC not present')
				write_line = write_line + [str(len(dboxes)), str(0), str(None), str(None), str(None), str(None), str(None), str(None), str(None)]
				write_line.append('TC-face-not-detected')
				
		
		write_log_file(fname_log, write_line)
		frm_counter += 1
		time.sleep(tc_np_time_delay)
	
	print('returning to Start the batch capture sequence')
	#cap.release()
	video_reader.stop()
	cv2.destroyAllWindows()
	log_file[1] = frm_counter
	
	return tc_p_duration, log_file


#########

def rotate_transform(bbox_ls, rotate_angle, quad):
	new_bbox_ls = []

	for bbox in bbox_ls:
		xl,yt,xr,yb = [bbox['left'],bbox['top'],bbox['right'],bbox['bottom']]
		xl,yt,xr,yb = xl*(1080/608.0),yt*(640/342.0),xr*(1080/608.0),yb*(640/342.0)
		
		lmarks_ = bbox['lmarks'] # x,y
		lmarks_[:,0] = lmarks_[:,0]*(1080/608.0)
		lmarks_[:,1] = lmarks_[:,1]*(640/342.0)
		lmarks = lmarks_.copy()
		
		
		if rotate_angle == 90: # if rotated counter clockwise
			xl1 = -(yb+quad*640-1920)
			yt1 = xl
			xr1 = -(yt+quad*640-1920)
			yb1 = xr
			
			lmarks[:,0] = -(lmarks_[:,1]+quad*640-1920)
			lmarks[:,1] = lmarks_[:,0]
			
		else:
			xl1 = yt + quad*640
			yt1 = -(xr-1080)
			xr1 = yb + quad*640
			yb1 = -(xl-1080)
			
			lmarks[:,1] = -(lmarks_[:,0]-1080)
			lmarks[:,0] = lmarks_[:,1] + quad*640
			
		xl,yt,xr,yb = xl1*(608/1920.0),yt1*(342/1080.0),xr1*(608/1920.0),yb1*(342/1080.0)
		lmarks[:,0] = lmarks[:,0]*(608/1920.0)
		lmarks[:,1] = lmarks[:,1]*(342/1080.0)
		
		bbox['left'],bbox['top'],bbox['right'],bbox['bottom'] = xl,yt,xr,yb
		bbox['lmarks'] = lmarks
		new_bbox_ls.append(bbox)
	return new_bbox_ls
	

def pipe_frames_data_to_faces(model, bbox_ls, img_ls, area_threshold=65, det_threshold=0.11):
	faces_log = []
	bbox_log = []
	idx_log = []
	for idx, bbox in enumerate(bbox_ls):
		for detface in bbox:
			if area(detface)>area_threshold and detface['prob']>=det_threshold:
				face, [nsW,nsH,offW,offH,sl,st] = get_face(img_ls[idx], detface, wsc, hsc)

				if detface['lmarks'] is not None:
					#print(detface)
					facelmarks = detface['lmarks'] - np.array([detface['left'], detface['top']]).reshape(1,2)
					facelmarks[:,0] = wsc*(facelmarks[:,0] + int(sl>=0)*5) + offW #nsW*(wsc*facelmarks[:,0]+offW).astype(np.int) # column
					facelmarks[:,1] = hsc*(facelmarks[:,1] + int(st>=0)*5) + offH #nsH*(hsc*facelmarks[:,1]+offH).astype(np.int) # row
					
					ch, cw = face.shape[0], face.shape[1]
					facelmarks[:,0] = 112*(facelmarks[:,0]/float(cw))
					facelmarks[:,1] = 112*(facelmarks[:,1]/float(ch))
					facelmarks = facelmarks.reshape(5,2) #+ np.array([-2,2,0,-2,+2]).reshape(5,1)
					
					face = resize(face, (112, 112))
					#print('after res', face.max(), face.min())
					face = np.uint8(255*face)
					#print(face.shape)
					
					facen = model.get_input(face, facelmarks.astype(np.int).reshape(1,5,2), face=True)
					
				else:
					facen = face.copy()				
				
				face_img_flip = facen[:,::-1,:]
				
				faces_log.append(facen)
				faces_log.append(face_img_flip)
				bbox_log.append(detface)
				idx_log.append(idx)
			else:
				print('Area threshold or det threshold failed!!', area(detface),  detface['prob'])
	return faces_log, bbox_log, idx_log

def get_face_embeddings(model, nmodel, detFacesLog, mean):

	det_emb = np.zeros((int(len(detFacesLog)/2), embedding_size*1))
	detFacesLog = np.array(detFacesLog)
	
	if detFacesLog.shape[0]>0:
		emb_det = []
		for fe_id in range(0,detFacesLog.shape[0],8):
			detFaceBatch = detFacesLog[fe_id:fe_id+8]
			
			#feed_dict = {image_batch: detFaceBatch, phase_train_placeholder:False}
			#emb_batch = sess.run(embeddings, feed_dict=feed_dict)
			#emb_batch = model.get_feature(detFaceBatch)
			emb_batch, norm = nmodel(to_input(detFaceBatch))
			emb_batch = emb_batch*norm
			emb_batch = emb_batch.cpu().detach().numpy()

			emb_det.append(emb_batch)
		
		emb_det = np.vstack(emb_det)
		
		#det_emb[:, :embedding_size] = emb_det[0::2,:]
		#det_emb[:, embedding_size:] = emb_det[1::2,:]
		det_emb = emb_det[0::2,:] + emb_det[1::2,:]

		dist = dist_mat(gt_embedding, det_emb, mean)
		detFacesLog = detFacesLog[0::2,:,:,:]
	else:
		dist = np.array([]) #np.ones((1,gt_embedding.shape[0]))
		
	return dist, detFacesLog, det_emb


famid = str(sys.argv[1])
savePath = str(sys.argv[2])
writeImg = True if sys.argv[3]=='save-image' else False


tmp_fname = str(datetime.now().strftime("%Y-%m-%d %H-%M-%S"))
tmp_fname = '_'.join(tmp_fname.split(' '))

fname_log = os.path.join(savePath, str(famid) + '_flash_log_'+tmp_fname+'.txt') 
frame_counter = 1

frames_path = os.path.join(savePath, str(famid)+'_frames')
results_path = os.path.join(savePath, str(famid)+'_test_res') # '/media/FLASH_SSD/525_test_res/'

if not os.path.exists(frames_path):
	os.makedirs(frames_path)

if not os.path.exists(results_path):
	os.makedirs(results_path)

log_file = [fname_log, frame_counter]
print('log file', log_file)

# get_gt_emb(model, fam_id, path, emb_size, img_size=112):		
gt_embedding = get_gt_emb(fmodel, nmodel, famid, savePath, embedding_size)

save_img_data = True
write_img_data = writeImg
tc_seen_last_time = None
face_seen_last_time = None

gal_update = [True, True, True, True]
gal_updated_time = [datetime.now() for i in range(4)]

#tc_presence_duration, log_file = check_tc_presence(fmodel, gt_embedding, log_file, det_thrshld=.11, ver_thrshld=0.39)
frm_counter = 1 #log_file[1]
log_fname = fname_log #log_file[0]

frames_list = []
time_stamps_list = []
gaze_list = []

batch10_frames = []
batch10_faces = []
batch10_tcpos = []
batch10_imgs = []	
batch10_ts = []				

batch7_list = []

batch7_count = 0
t_batch_start = time.time()
batch7_write = True

rotate_tofindtc = True
rotate_flip = None
rotate_angle = None
rotate_count = 0
rotate_count_tc = 0
rotate_bool = [[0,0],[0,1],[0,2],[1,0],[1,1],[1,2]] #,[-1,-1]]
rotate_status = 0
quad = None

while True:
    #check face_presence and tc_presence from individual image capture 
	#if tc present for more than some time trigger batch video capture
	print('*************************************************************************************')
	print('*************************************************************************************')
	print('INITIALIZING THE DETECTOR AND VERIFICATION ALGORITHM')
	print('GIVE 5 minutes for this step')
	print('*************************************************************************************')
	print('*************************************************************************************')
	tc_presence_duration, log_file = check_tc_presence(fmodel, nmodel, gt_embedding, log_file, det_thrshld=.11, ver_thrshld=0.39)
	frm_counter = log_file[1]
	log_fname = log_file[0]
	
	tc_seen_last_time = datetime.now()
	face_seen_last_time = datetime.now()

	# intiate the capture process 
	print('starting the batch cam', frm_counter)
	q = Queue(maxsize=500)
	stop_capture = False
	p1 = th.Thread(target=frame_write, args=(q, frm_counter,))
	p1.start()
		
	frames_list = []
	time_stamps_list = []
	gaze_list = []

	batch10_frames = []
	batch10_faces = []
	batch10_tcpos = []
	batch10_imgs = []	
	batch10_ts = []				
	
	batch7_list = []
	
	batch7_count = 0
	t_batch_start = time.time()
	batch7_write = True
	qempty_start = None


	while True:
		if (batch7_count+1) % 100 == 0:
			#stop_capture = True
			if batch7_write:
				print('############################################################')
				print('Time for processing 100 batch7s: ', time.time()-t_batch_start)
				print('############################################################')
				t_batch_start = time.time()
			batch7_write = False
			
		tc_check_time_now = datetime.now()
		time_diff = tc_check_time_now - tc_seen_last_time
		
		if time_diff.total_seconds() >= 1500:
			stop_capture = True
			break
		
		ni=4
		for idx in range(ni):
			time_diff = datetime.now() - gal_updated_time[idx]
			if time_diff.total_seconds() >= 150.0:
				gal_update[idx] = True
				
				
		if not q.empty():
			qempty_start = None
			batch7_list = q.get()
		
			batch7_count+=1 
			batch7_write = True
			
			frame_1080p_ls = [b[0] for b in batch7_list]
			frame_counts = [b[1] for b in batch7_list]
			frame_stamps = [b[2] for b in batch7_list]
			
			frm_counter = frame_counts[-1]
			tdet = time.time()
			if write_img_data:
				tmp = [cv2.imwrite(os.path.join(frames_path, str(frame_counts[k]).zfill(6)+'.png'), frame_1080p_ls[k]) for k in range(3,5)]
				del tmp
			
			
			frames_list.append(frame_counts[3])
			time_stamps_list.append(frame_stamps[3])
			gaze_list.append(np.array([None, None]))
			
			frame_1080p_ls = [cv2.cvtColor(img1080, cv2.COLOR_BGR2RGB) for img1080 in frame_1080p_ls]
			frame_608p_ls = [cv2.resize(img1080, (608,342)) for img1080 in frame_1080p_ls]
			
			frame_1080p_ls = [frame_1080p_ls[3],frame_1080p_ls[4]]
			frame_608p_ls = [frame_608p_ls[3],frame_608p_ls[4]]
				
			# run face detector
			if rotate_tofindtc:
				img2 = frame_1080p_ls[1]
				img1 = frame_1080p_ls[0]
				rotate_flip, quad = rotate_bool[rotate_status]
				
				if rotate_flip >= 0:
					if rotate_flip:
						img2 = cv2.rotate(img2[:,:,::-1], cv2.ROTATE_90_CLOCKWISE)
						#img1 = cv2.rotate(img1[:,:,::-1], cv2.ROTATE_90_CLOCKWISE)
						rotate_angle = -90
					else:
						img2 = cv2.rotate(img2[:,:,::-1], cv2.ROTATE_90_COUNTERCLOCKWISE)
						#img1 = cv2.rotate(img1[:,:,::-1], cv2.ROTATE_90_COUNTERCLOCKWISE)
						rotate_angle = 90
					
					#img2 = cv2.resize(img2, (1920, 1080))
					img2 = img2[quad*640:(quad+1)*640,:,::-1]
					#img1 = img1[quad*640:(quad+1)*640,:,::-1]
					#img2 = img2[840:,:,::-1]
				
				#img1 = frame_1080p_ls[0]
				frame_bbox_ls = [face_detector(img1[:,:,::-1]), face_detector(img2[:,:,::-1], threshold=0.11)] # rgb to bgr for face detector input
				#frame_bbox_ls[0] = rotate_transform(frame_bbox_ls[0], rotate_angle, quad)
				if rotate_flip >= 0:
					frame_bbox_ls[1] = rotate_transform(frame_bbox_ls[1], rotate_angle, quad)
				rotate_count +=1
			else:
				frame_bbox_ls = [face_detector(frame[:,:,::-1]) for frame in frame_1080p_ls] # rgb to bgr for face detector input
				rotate_count = 0
				rotate_count_tc = 0
				rotate_flip = False
			#print('for face detector', time.time()-tdet)
			#print(frm_counter, len(frame_bbox_ls[0]), len(frame_bbox_ls[1]), rotate_angle, rotate_flip, quad) #, frame_bbox_ls[1])
			
			tfv = time.time()
			# pipe per frame dets to batch of facial images for faster face rec 
			detFacesLog, bboxFaces, idxFaces = pipe_frames_data_to_faces(fmodel, frame_bbox_ls, frame_1080p_ls, area_threshold=35, det_threshold=0.11)
			
			#for face_count, face in enumerate(detFacesLog[::2]):
			#	#print('saving', face.shape, frame_counts[3])
			#	cv2.imwrite(os.path.join(aux_path, str(frame_counts[3]).zfill(6)+'_'+str(face_count).zfill(2)+'.png'), face[:,:,::-1])
		
		
			dist, detFacesLog, det_emb = get_face_embeddings(fmodel, nmodel, detFacesLog, mean)
			
			if detFacesLog.shape[0]>0:
				face_seen_last_time = datetime.now()

			thrs = threshold
			dist_cmp = np.array([])
			ni = 4
			if dist.shape[0]>0:
				dist_res = np.copy(dist) - thrs
				dist_res[dist_res>0] = 0
				dist_res = -(dist_res)
				#print(dist_cmp)
				dist_cmp = dist_res[:, :ni] + dist_res[:, ni:ni*2] + dist_res[:, ni*2:ni*3] + \
							dist_res[:, ni*3:ni*4] + dist_res[:, ni*4:ni*5] + dist_res[:, ni*5:ni*6]
						
			dist_res = dist
		
			frame_ver_bbox_ls = []
			tc_bbox_ls = []
			tc_faces_ls = []
			angle=None
			for frm_idx in range(2):
				#frm_boxes = [bboxFaces[cidx] for cidx, i in enumerate(idxFaces) if i==frm_idx]
				face2frm_idx = [cidx for cidx, i in enumerate(idxFaces) if i==frm_idx]
				frm_boxes = [bboxFaces[i] for i in face2frm_idx]
				frm_distcmp = [dist_cmp[i] for i in face2frm_idx]
				frm_distcmp = np.array(frm_distcmp)

				idxs = [0,1,2,3]
				gt_idxs = [-4,-3,-2]
				for i in range(frm_distcmp.shape[0]):
					di = frm_distcmp[i]
					idx = di.argmax()
					if save_feat:
						frm_boxes[i]['feat'] = det_emb[face2frm_idx[i],:]
					else:
						frm_boxes[i]['feat'] = np.array([])
					
					face_i = detFacesLog[face2frm_idx[i]]
						
					if (idx in idxs) and frm_distcmp[:,idx].max()<=di[idx] and di[idx]>0: # 
						frm_boxes[i]['idx'] = idx
						idxs.remove(idx)
						
						if idx==0:
							#print(face_i.shape, face_i.max())
							face_tc, [nsW,nsH,offW,offH,sl,st] = get_tc_face(frame_1080p_ls[frm_idx], frm_boxes[i], wsc, hsc)
							rotated_face_tc, angle = rotate_tc_face(face_tc, frm_boxes[i], wsc, hsc, sl, st, offW, offH,angle)
							
							#print(frm_idx, frm_boxes[i])
							#cv2.imwrite(os.path.join(aux_path, str(frame_counts[3]).zfill(6)+'_'+str(frm_idx).zfill(2)+'_unrot.png'), face_tc[:,:,::-1])
							#cv2.imwrite(os.path.join(aux_path, str(frame_counts[3]).zfill(6)+'_'+str(frm_idx).zfill(2)+'_rot.png'), rotated_face_tc[:,:,::-1])
							frm_boxes[i]['angle'] = angle
							#print(frame_counts[3], frm_idx, angle)
							
							#imsave('tmp_tc_'+str(frame_counts[3]).zfill(6)+'.png', rotated_face_tc)
							tc_faces_ls.append(rotated_face_tc)
							#tc_faces_ls.append(face_tc)
							tc_bbox_ls.append(frm_boxes[i])
							if rotate_tofindtc and frm_idx==1:
								rotate_count_tc += 1
								#print('rotated tc detected')
							
						if idx<3 and di[idx]>gal_add_thrshld and gal_update[idx]:
							tmp = 10
							gt_embedding[gt_idxs[idx],:] = frm_boxes[i]['feat']
							gal_update[idx] = False
							gal_updated_time[idx] = datetime.now()
							print('Updated gallery at idx:', idx, 'at', gal_updated_time[idx].time())
							#upFace = detFacesLog[face2frm_idx[i]]
							#fi_name = fis[0][:6]+'_update_'+str(idx)+'.png'
							#imsave(os.path.join(savePath, fi_name), upFace)
						#if (idx==0):
						#continue
						#imsave(tcPath+fi[:-7]+'.png', detFacesLog[i])
						#np.save(featPath+fi[:-7]+'.npy', det_emb[i, :embedding_size])
					else:
						if len(frm_boxes)>0:
							frm_boxes[i]['idx'] = 4
							
				#print('Frame appends', frm_idx, len(frm_boxes), idxs)
				frame_ver_bbox_ls.append(frm_boxes)
				
				if rotate_tofindtc and frm_idx==1:
					#if 0 in idxs:
					if rotate_flip<0:
						if 0 in idxs:
							rotate_status = rotate_count%6
					else:
						if len(frm_boxes)<1:
							#rotate_flip = not rotate_flip
							rotate_status = rotate_count%6
							#print('changing rot stat', rotate_status, rotate_count)

			if len(tc_faces_ls)>=1:
				
				tc_seen_last_time = datetime.now()
				#frames_ls.append(frames_ls[-1])
				if len(tc_faces_ls)<=1:
					for i in range(7-len(tc_faces_ls)):
						tc_faces_ls.append(tc_faces_ls[-1])
				else:
					#print('going for 2', len(tc_faces_ls))
					tc_faces_ls = [tc_faces_ls[0]]*3 + tc_faces_ls + [tc_faces_ls[-1]]*2
					#tc_faces_ls = [tc_faces_ls[1]]*7 # + tc_faces_ls + [tc_faces_ls[-1]]*2
				
				source_video_7fps = torch.FloatTensor(7,3,224,224) 
				for idx, img in enumerate(tc_faces_ls):
					#print('image max', img.min(), img.max())
					img_ar = 1*img
					im = Image.fromarray(np.uint8(img_ar))
					source_video_7fps[idx,...] = image_transform(im)
					
				source_video_7fps = source_video_7fps.view(21,224,224)
				
				batch10_frames.append(frame_counts[3])
				batch10_faces.append(source_video_7fps)
				batch10_imgs.append(frame_608p_ls[0])
				batch10_tcpos.append([tc_bbox_ls[0], len(frame_ver_bbox_ls[0])])
				batch10_ts.append(frame_stamps[3])
			else:
				output_name = str(frame_counts[3]).zfill(6)+'.png'
				if len(frame_608p_ls)>=0:
					#sid = len(frame_608p_ls)-1
					sid = 0
				idx = -1
				print(frame_counts[3], frame_stamps[3], [None, None])
				
				if sid>=0:
					Nfaces = len(frame_ver_bbox_ls[sid])
				else:
					Nfaces = 0
				TC_ident = 0
				fid = open(log_fname,'a')
				write_line = ' '.join([str(frame_stamps[3]), str(frame_counts[3]).zfill(6), str(Nfaces), str(TC_ident), str(None), str(None), str(None), str(None), str(None), str(None), str(None), 'Gaze-no-det'])
				write_line = write_line + '\n'
				fid.write(write_line)
				fid.close()
				
				fid = open(log_fname[:-4]+'_reg.txt','a')
				write_line = ' '.join([str(frame_stamps[3]), str(frame_counts[3]).zfill(6), str(Nfaces), str(TC_ident), str(None), str(None), str(None), str(None), str(None), str(None), str(None), 'Gaze-no-det'])
				write_line = write_line + '\n'
				fid.write(write_line)
				fid.close()
				
				fid = open(log_fname[:-4]+'_rot.txt','a')
				write_line = ' '.join([str(frame_stamps[3]), str(frame_counts[3]).zfill(6), str(Nfaces), str(TC_ident), str(None), str(None), str(None), str(None), str(None), str(None), str(None), 'Gaze-no-det'])
				write_line = write_line + '\n'
				fid.write(write_line)
				fid.close()
				
				
				if write_img_data and sid>=0:
					#print(frame_ver_bbox_ls[sid])
					draw_rect_ver(frame_608p_ls[sid], frame_ver_bbox_ls[sid], None, os.path.join(results_path, output_name))
			
			#print('for face vern', time.time()-tfv)	
		else:
		    #print('asdf queue is empty')
			if qempty_start is None:
				qempty_start = time.time()
			else:
				empty_duration = time.time()-qempty_start
				if empty_duration > 45:
					print('*************************************************************************************')
					print('*************************************************************************************')
					print('CAMERA QUEUE DID NOT LOAD')
					#print('QUIT THE CODE')
					print('RESTARTING')
					print('*************************************************************************************')
					print('*************************************************************************************')
					stop_capture = True
					p1.join()
					time.sleep(3)
					break
		
	
		tc_batch_size = len(batch10_faces)
		if tc_batch_size == 10:
			tmp = 10
			print('running the gaze estimation .... ')
			tg_start = time.time()
			
			source_video = torch.FloatTensor(10,21,224,224) 
			for idx, vid_7fps in enumerate(batch10_faces):
	 			source_video[idx,...] = vid_7fps
	 		
			source_frame = source_video.cuda(non_blocking=True)

			with torch.no_grad():
				source_frame_var = torch.autograd.Variable(source_frame)
				# compute output
				output,ang_error = model(source_frame_var)
				output2,ang_error2 = modelreg(source_frame_var)
			
			print('gaze run time:', time.time()-tg_start)
			output_varr = output.cpu().data.numpy()
			ang_error_np = ang_error.cpu().data.numpy()
			
			output_varr2 = output2.cpu().data.numpy()
			ang_error_np2 = ang_error2.cpu().data.numpy()
			
			fid = open(log_fname,'a')
			for i in range(10):
				print(batch10_frames[i], batch10_ts[i], output_varr[i,:2])
				tcpos = batch10_tcpos[i][0]
				Nfaces = batch10_tcpos[i][1]
				
				write_line = ' '.join([str(batch10_ts[i]), str(batch10_frames[i]).zfill(6), str(Nfaces), str(1), str(output_varr[i,0]), str(output_varr[i,1]), str(ang_error_np[i,0]), str(tcpos['angle']), str(tcpos['top']), str(tcpos['left']), str(tcpos['bottom']), str(tcpos['right']), 'Gaze-det'])
				write_line = write_line + '\n'
				fid.write(write_line)
				
			fid.close()
			
			fid = open(log_fname[:-4]+'_reg.txt','a')
			for i in range(10):
				#print(batch10_frames[i], batch10_ts[i], output_varr[i,:2])
				tcpos = batch10_tcpos[i][0]
				Nfaces = batch10_tcpos[i][1]
				
				write_line = ' '.join([str(batch10_ts[i]), str(batch10_frames[i]).zfill(6), str(Nfaces), str(1), str(output_varr2[i,0]), str(output_varr2[i,1]), str(ang_error_np2[i,0]), str(tcpos['angle']), str(tcpos['top']), str(tcpos['left']), str(tcpos['bottom']), str(tcpos['right']), 'Gaze-det'])
				write_line = write_line + '\n'
				fid.write(write_line)
				
			fid.close()
			
			fid = open(log_fname[:-4]+'_rot.txt','a')
			if save_img_data:
				tg_start = time.time()
				for i in range(10):
					tcpos = batch10_tcpos[i][0]
					Nfaces = batch10_tcpos[i][1]
					
					output_name = str(batch10_frames[i]).zfill(6)+'.png'
					output_name2 = str(batch10_frames[i]).zfill(6)+'_2.png'
					
					s0 = output_varr[i,0]
					s1 = output_varr[i,1]
					
					sx = (tcpos['left'] + tcpos['right'])/2 # 
					sy = (tcpos['top'] + tcpos['bottom'])/2
					
					x = math.cos(s1)*math.sin(s0) # -40*
					y = math.sin(s1) # -40*
					z = -math.cos(s1)*math.cos(s0)
					
					tangle = -(tcpos['angle']/180)*math.pi
					xt = math.cos(tangle)*x + math.sin(tangle)*y
					yt = -math.sin(tangle)*x + math.cos(tangle)*y
					zt = z
					
					vt = np.array([xt,yt,zt])
					vtnorm = (vt*vt).sum()
					vt = vt / np.sqrt(vtnorm)
					ns0 = math.atan2(vt[0],-vt[2])
					ns1 = math.asin(vt[1])
					
					nx = -40*vt[0]
					ny = -40*vt[1]
					x = -40*x
					y = -40*y
					
					ws0 = s0
					ws1 = s1
					
					color=2
					if write_img_data:
						draw_rect_gz(batch10_imgs[i], batch10_frames[i], (int(sx),int(sy)), (int(sx+x),int(sy+y)), color, os.path.join(results_path, output_name))
					
					color=0
					if abs(tcpos['angle'])>=30:
						if write_img_data:
							draw_rect_gz(batch10_imgs[i], batch10_frames[i], (int(sx),int(sy)), (int(sx+nx),int(sy+ny)), color, os.path.join(results_path, output_name2))
						ws0 = ns0
						ws1 = ns1
						
					write_line = ' '.join([str(batch10_ts[i]), str(batch10_frames[i]).zfill(6), str(Nfaces), str(1), str(ws0), str(ws1), str(ang_error_np[i,0]), str(tcpos['angle']), str(tcpos['top']), str(tcpos['left']), str(tcpos['bottom']), str(tcpos['right']), 'Gaze-det'])
					write_line = write_line + '\n'
					fid.write(write_line)
				
			fid.close()
					
				#print('save run time:', time.time()-tg_start)
			batch10_frames = []
			batch10_faces = []
			batch10_tcpos = []
			batch10_imgs = []
			batch10_ts = []
		
	log_file[1] = frm_counter
	p1.join()
	del q
	#print('id pass', time.time()-t)	
	#print('iter pass', time.time()-t_iter)	
		
print('1000 images time', time.time()-t_start)
