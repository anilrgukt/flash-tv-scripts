import os
import sys
import cv2
import numpy as np 

# face detection libs
#det_path_loc = '/home/'+os.getlogin()+'/insightface/detection/RetinaFace'
#sys.path.insert(1, det_path_loc)
#from retinaface import RetinaFace



class FlashFaceDetector():
    def __init__(self, det_path_loc, detector_threshold=0.15, detector_hw=[720,1280], output_hw=[342,608]):
        self.threshold = detector_threshold
        self.out_hw = output_hw
        self.det_hw = detector_hw
        gpuid=0

        sys.path.insert(1, det_path_loc)
        from retinaface import RetinaFace
        
        self.detector = RetinaFace(os.path.join(det_path_loc, 'model/retina'), 0, gpuid, 'net3', vote=False)
        self.det_path_loc = det_path_loc #'/home/'+os.getlogin()+'/insightface/detection/RetinaFace'
        
        self.hw_scale = [self.out_hw[i]/self.det_hw[i] for i in range(2)]
        self.det_scales = [1.0] # perform detection at scales x det_hw
        
        
    @property
    def get_data_path(self):
        return self.det_path_loc

    def face_detect(self, img, now_threshold=None):
        if now_threshold is None:
            det_thresh = self.threshold
        else:
            det_thresh = now_threshold 
            
        #det_scales = [720, 1280] # 720, 1280
        #det_res_img = [720, 1280]
        #det_write_img = [342, 608]
        #dhsc, dwsc = [det_write_img[0]/720.0, det_write_img[1]/1280.0]
        #det_scales = [1.0]
        
        img = cv2.resize(img, (self.det_hw[1], self.det_hw[0]))
        faces, landmarks = self.detector.detect(img, det_thresh, self.det_scales, do_flip=False)
        
        return faces, landmarks
        
    def convert_bbox(self, faces, landmarks):
        bbox_ls = []
        if faces is not None:
            for i in range(faces.shape[0]):
                score = faces[i,4]
                
                # scale det output to the req output_res
                hsc, wsc = self.hw_scale
                self.scale4 = [wsc,hsc,wsc,hsc]
                self.scale2 = [wsc,hsc]
                
                box = faces[i,:4]*np.array([wsc, hsc, wsc, hsc])
                lmarks = landmarks[i]*np.array([wsc, hsc]).reshape(1,2)

                box = box.astype(np.int32)
                lmarks = lmarks.astype(np.int32)

                bbox_ls.append({'left': box[0], 'top': box[1], 'right': box[2], 'bottom': box[3], 'prob': score, 'lmarks':lmarks})
            
        return bbox_ls
        
    
