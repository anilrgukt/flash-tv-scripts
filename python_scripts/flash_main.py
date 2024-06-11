import os
import pickle 
import time
import yaml 

import cv2
import numpy as np 

from flash.face_detection import FlashFaceDetector
from flash.face_verification import FLASHFaceVerification
from flash.gaze_estimation import FLASHGazeEstimator
from flash.face_processing import FaceModelv4 as FaceProcessing
#from utils.rotate_frame import rotate_frame
from utils.bbox_utils import Bbox
from utils.visualizer import draw_rect_det, draw_rect_ver, draw_gz

with open('path_locations.yaml') as stream:
    var = yaml.safe_load(stream)

ckpt1_r50 = var['ckpt1_r50'] #'/home/'+os.getlogin()+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar'
ckpt2_r50reg = var['ckpt2_r50reg'] #'/home/'+os.getlogin()+'/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50reg.pth.tar'

model_path = var['model_path'] #"/home/"+os.getlogin()+"/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt"
det_path_loc = var['det_path_loc'] #'/home/'+os.getlogin()+'/insightface/detection/RetinaFace'

class FLASHtv():
    def __init__(self, family_id, num_identities, data_path, frame_res_hw, output_res_hw):
        self.ni = num_identities
        self.fd = FlashFaceDetector(det_path_loc)
        self.fv = FLASHFaceVerification(model_path, num_identities=self.ni)
        self.gz = FLASHGazeEstimator(ckpt1_r50, ckpt2_r50reg)
        #self.rot_frame = rotate_frame()
        self.face_processing = FaceProcessing(frame_resolution=[1080,1920], detector_resolution=[342,608], face_size=112,
                                face_crop_offset=16, small_face_padding=7, small_face_size=65)
        self.gaze_face_processing = FaceProcessing(frame_resolution=[1080,1920], detector_resolution=[342,608], face_size=160,
                                face_crop_offset=45, small_face_padding=3, small_face_size=65)          
        
        self.family_id = family_id
        self.data_path = data_path
        
        # get the GT embedding ... 
        self.gt_embedding = self.fv.get_gt_emb(fam_id=self.family_id, path=self.data_path, face_proc=self.face_processing)
        
    def run_detector(self, img_cv1080, now_threshold=None):
        
        faces, lmarks = self.fd.face_detect(img_cv1080, now_threshold)
        frame_bls = self.fd.convert_bbox(faces, lmarks)
        
        return frame_bls
        
    def run_verification(self, img_cv1080, bls):
        bbox_ls = [Bbox(b) for b in bls]
        
        cropped_aligned_faces = []
        check_faces = []
        for bbx in bbox_ls:
            
            face, bbx_ = self.face_processing.crop_face_from_frame(img_cv1080, bbx)
            check_faces.append(face)
            
            face, lmarks = self.face_processing.resize_face(face, bbx_)
            facen = self.face_processing.get_normalized_face(face, lmarks.astype(np.int).reshape(1,5,2), face=True)
            
            cropped_aligned_faces.append(facen)
            cropped_aligned_faces.append(facen[:,::-1,:])
        
        cropped_aligned_faces = np.array(cropped_aligned_faces)
        det_emb, cropped_aligned_faces = self.fv.get_face_embeddings(cropped_aligned_faces)
        pred_ids, _ = self.fv.convert_embedding_faceid(ref_features=self.gt_embedding, test_features=det_emb, mean=0)
        
        for i in range(len(bls)):
            bls[i]['idx'] = pred_ids[i]
        
        return bls
        
    def run_gaze(self, frame_ls, frame_bbox_ls):
        
        tc_imgs = []
        tc_boxs = []
        tc_id = -1
        tc_frame_id = 0
        for img, bbox_ls in zip(frame_ls, frame_bbox_ls):
            #img_cv1080 = img[:,:,::-1]
            
            tc_frame_id += 1
            for bbx in bbox_ls:
                if bbx['idx'] == 0: # target child ID
                    bbx_ = Bbox(bbx)
                    face, bbx_ = self.gaze_face_processing.crop_face_from_frame(img, bbx_) # rgb
                    face, lmarks = self.gaze_face_processing.resize_face(face, bbx_) # rgb
                    face_rot, angle, lmrks = self.gaze_face_processing.rotate_face(face, lmarks, angle=None)
                    bbx['angle'] = angle
                    bbx['new_lmrks'] = lmarks
                    #print(bbx_.return_dict())
                    #print(lmarks)
                    #print(angle)
                    #tc_faces.append(face_rot)
                    tc_face = face_rot
                    tc_bbx = bbx
                    
                    tc_imgs.append(tc_face)
                    tc_boxs.append(tc_bbx)
                    tc_id = tc_frame_id-1
        
        tc_present = False        
        gz_data = None
        #tc_boxs = None
        
        if len(tc_imgs)>0:
            tc_present = True
            gaze_input = self.gz.to_input(tc_imgs)
            output = self.gz.gaze_estimate(gaze_input)
            o1, e1 = output[0]
            o2, e2 = output[1]
            
            o1 = o1.cpu().data.numpy()
            e1 = e1.cpu().data.numpy()
            
            o2 = o2.cpu().data.numpy()
            e2 = e2.cpu().data.numpy()
            
            gz_data = [o1,e1,o2,e2]
            tc_bbx = tc_boxs[0]
            
        return tc_present, gz_data, tc_boxs, tc_id, tc_imgs
