import os
import pickle 
import time

import cv2
import numpy as np 

from flash.face_detection import FlashFaceDetector
from flash.face_verification import FLASHFaceVerification
from flash.gaze_estimation import FLASHGazeEstimator, load_limits, get_lims, eval_thrshld
from flash.face_processing import FaceModelv4 as FaceProcessing
from utils.bbox_utils import Bbox
from utils.visualizer import draw_rect_det, draw_rect_ver, draw_gz, ts2num, num2ts, get_xticks

from utils.stream import WebcamVideoStream



from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd



plot_data = True
if plot_data:
    num_mins = 5
    window_duration = num_mins*60

    plt.figure('TV viewing behavior', figsize=(10,2))
    plt.rcParams.update({'font.size': 14})
    plt.yticks([], [])
    plt.ylim([0,1])


data_path = '/home/flashsys007/dmdm2024/data'
frame_path = '/home/flashsys007/dmdm2024/data/frames'
det_res_path = '/home/flashsys007/dmdm2024/data/detres'
det_bbx_path = '/home/flashsys007/dmdm2024/data/detres_bbx'
fv_res_path = '/home/flashsys007/dmdm2024/data/fvres'
gz_res_path = '/home/flashsys007/dmdm2024/data/gzres'


vis = True
write_image = False
cam_stream = True
save_bbx = not cam_stream
skip_detector = False

frame_ls = os.listdir(frame_path)
frame_ls.sort()

username = 'flashsys007'
ckpt1_r50 = '/home/'+username+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar'
ckpt2_r50reg = '/home/'+username+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50reg.pth.tar'

model_path = "/home/"+username+"/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt"
det_path_loc = '/home/'+username+'/insightface/detection/RetinaFace'

fd = FlashFaceDetector(det_path_loc) #detector_hw=[480,860]) #detector_hw=[720,1280]) #detector_hw=[480,860])
fv = FLASHFaceVerification(model_path, num_identities=4) #verification_threshold=0.516)
gz = FLASHGazeEstimator(ckpt1_r50, ckpt2_r50reg)

face_processing = FaceProcessing(frame_resolution=[1080,1920], detector_resolution=[342,608],
                                 face_size=112, face_crop_offset=16, small_face_padding=7, small_face_size=65)
gt_embedding = fv.get_gt_emb(fam_id='123',path=data_path,face_proc=face_processing)

gaze_face_processing = FaceProcessing(frame_resolution=[1080,1920], detector_resolution=[342,608], 
                                    face_size=160, face_crop_offset=45, small_face_padding=3, small_face_size=65)            
                                                         
loc_lims = load_limits(file_path='./4331_v3r50reg_reg_testlims_35_53_7_9.npy', setting='center-big-med')
num_locs = loc_lims.shape[0]


if not skip_detector:
    faces, lmarks = fd.face_detect(cv2.imread('frame_00000.png'))

stream = WebcamVideoStream()
stream.start(src='/dev/video0', width=1920, height=1080, fps=30)

if not cam_stream:
    time.sleep(3)
    stream.stop()

if plot_data:
    start_time = datetime.now().time().strftime("%H:%M:%S") # strftime("%Y-%m-%d %H:%M:%S")
    start_n = ts2num(start_time)
    
    h,m,s = num2ts(start_n)
    start_time_ = '%02d:%02d:00'%(h,m)
    start_n = ts2num(start_time_)
    
    plt.xlim([start_n, start_n + window_duration+5])
    
    plt.bar(start_n-3, 1, width=1, color='yellowgreen', label='Gaze')
    plt.bar(start_n-4, 1, width=1, color='deepskyblue', label='No-Gaze')
    plt.legend(bbox_to_anchor=(1.05, 1.0), loc='upper left')
    
    label_xticks = get_xticks(start_n, num_mins)
    #print(start_n, start_n + window_duration+5)
    #print(range(start_n, start_n + (num_mins+1)*60,60))
    #print(label_xticks)
    plt.xticks(ticks=range(start_n, start_n + (num_mins+1)*60,60),labels=label_xticks)
    plt.tight_layout()
    
#
#for frame_id, frame_name in enumerate(frame_ls):    
frame_id = 0
while True:
    if cam_stream:
        frame_name = 'sframe_%05d.png'%(frame_id)
        img_cv1080 = stream.read()
        frame_time = datetime.now()#.strftime("%Y-%m-%d %H:%M:%S")
    else:
        img_path = os.path.join(frame_path, frame_name)
        img_cv1080 = cv2.imread(img_path)
        frame_time = datetime.now()
    
    img_np1080 = img_cv1080[:,:,::-1]
    
    img_cv608 = cv2.resize(img_cv1080, (608,342))
    img_np608 = img_cv608[:,:,::-1]    
    
    
    if skip_detector:
        fi = open(os.path.join(det_bbx_path, frame_name+'.pickle'),'rb')
        bls = pickle.load(fi)
    else:
        faces, lmarks = fd.face_detect(img_cv1080)
        bls = fd.convert_bbox(faces, lmarks)
        
        if not cam_stream:
            fi = open(os.path.join(det_bbx_path, frame_name+'.pickle'),'wb')
            pickle.dump(bls, fi)
        
    
    bbox_ls = [Bbox(b) for b in bls]
    
    cropped_aligned_faces = []
    check_faces = []
    for bbx in bbox_ls:
        #draw_rect_det(img_np608, [bbx.return_dict()], os.path.join(det_res_path, frame_name[:-4]+'_c608.png'))
        
        face, bbx_ = face_processing.crop_face_from_frame(img_cv1080, bbx)
        #draw_rect_det(img_cv1080[:,:,::-1], [bbx_.return_dict()], os.path.join(det_res_path, frame_name[:-4]+'_c1080.png'))
        
        
        check_faces.append(face)
        face, lmarks = face_processing.resize_face(face, bbx_)
        facen = face_processing.get_normalized_face(face, lmarks.astype(np.int).reshape(1,5,2), face=True)
        
        cropped_aligned_faces.append(facen)
        cropped_aligned_faces.append(facen[:,::-1,:])
    
    #for idx, face_ in enumerate(check_faces):
    #    cv2.imwrite('./tmp/%s_%d.png'%(frame_name[:-4], idx), face_)
        
    cropped_aligned_faces = np.array(cropped_aligned_faces)
    #print(cropped_aligned_faces.shape)
    #fv_inputs = [fv.to_input(face) for face in cropped_aligned_faces]
    
    det_emb, cropped_aligned_faces = fv.get_face_embeddings(cropped_aligned_faces)
    #print(cropped_aligned_faces.shape)
    #print(det_emb.shape, gt_embedding.shape)
    
    
    pred_ids, _ = fv.convert_embedding_faceid(ref_features=gt_embedding, test_features=det_emb, mean=0)
    
    for i in range(len(bls)):
        bls[i]['idx'] = pred_ids[i]
        
    tc_face = None
    tc_bbx = None
    for bbx in bls:
        if bbx['idx'] == 0:
            bbx_ = Bbox(bbx)
            face, bbx_ = gaze_face_processing.crop_face_from_frame(img_cv1080, bbx_)
            face, lmarks = gaze_face_processing.resize_face(face, bbx_)
            face_rot, angle, lmarks = gaze_face_processing.rotate_face(face, lmarks, angle=None)
            bbx['angle'] = angle
            bbx['new_lmrks'] = lmarks
            
            #tc_faces.append(face_rot)
            tc_face = face_rot
            tc_bbx = bbx
    
    #print(frame_id, frame_name, pred_ids, tc_bbx==None)
    
    
    #draw_rect_ver(img_np608, bls, None, os.path.join(fv_res_path, frame_name))
    if tc_face is not None:
        #cv2.imwrite('./tmp/%s.png'%(frame_name[:-4]), tc_face)
        gaze_input = gz.to_input([tc_face])
        output = gz.gaze_estimate(gaze_input)
        o1, e1 = output[0]
        o2, e2 = output[1]
        
        o1 = o1.cpu().data.numpy()
        e1 = e1.cpu().data.numpy()
        
        o2 = o2.cpu().data.numpy()
        e2 = e2.cpu().data.numpy()
        
        o1 = 0.9*o1 + 0.1*o2
        lims_idx = get_lims(tc_bbx, num_locs, H=342, W=608)
        _, _, gaze_est, _, _ = eval_thrshld(np.array([o1[0,0]]), np.array([o1[0,1]]), gt_lab=np.array([0]), lims=loc_lims[lims_idx])
        
        
        result_img, result_img2 = draw_gz(img_np1080, o1, tc_bbx, os.path.join(gz_res_path, frame_name), gz_label=gaze_est[0], write_img=write_image, scale=[480, 854])
        #print(frame_id, o1[0,0], o1[0,1], 'Gaze-detected', gaze_est[0])
        print('%s, Gaze-label: %d'%(frame_time.strftime("%Y-%m-%d %H:%M:%S"), gaze_est[0]))
        
    else:
        tmp=10
        #draw_rect_det(img_np608, bls, os.path.join(det_res_path, frame_name))
        result_img = draw_rect_ver(img_np1080, bls, None, os.path.join(gz_res_path, frame_name),scale=[480, 854])
        result_img2 = np.zeros((256,256)).astype(np.uint8)
        #print(frame_id, None, None, 'Child-not-detected')
        print('%s, Gaze-label: %s'%(frame_time.strftime("%Y-%m-%d %H:%M:%S"), 'child-not-detected'))
    
    if plot_data:
        if not tc_bbx is None:
            now_time = frame_time.now().time().strftime("%H:%M:%S")
            n_now = ts2num(now_time)
            h,m,s = num2ts(n_now)
            
            plt_val = gaze_est[0]
            colors = 'yellowgreen' if plt_val==1 else 'deepskyblue'
            
            #print(now_time, n_now)
            plt.bar(n_now, 1, color=colors, width=1)
            plt.pause(0.01)
            
            if start_n + window_duration == n_now: #(n_now - 1) or start_n + window_duration == (n_now + 1):
                #plt.clf()
                start_n = n_now
                frame_id = 0
                plt.xlim([start_n, start_n + window_duration+5])

                label_xticks = get_xticks(start_n, num_mins)
                plt.xticks(ticks=range(start_n, start_n + (num_mins+1)*60,60),labels=label_xticks)
                plt.tight_layout()
    
        
    if vis:
        cv2.imshow('Gaze Result', result_img)
        #if result_img2 is not None:
        #    cv2.imshow('Gaze tracking', result_img2)
        pressedKey = cv2.waitKey(1) & 0xFF
        if pressedKey == ord('q'):
            break
    
    if cam_stream:
        frame_id = frame_id+1
    
stream.stop()
cv2.destroyAllWindows()
plt.show()
