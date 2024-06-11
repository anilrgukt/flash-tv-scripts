import cv2
import numpy as np

import insightface

from utils import face_align
from utils.bbox_utils import Bbox
from skimage.transform import resize

'''
facelmarks = detface['lmarks'] - np.array([detface['left'], detface['top']]).reshape(1,2)
facelmarks[:,0] = wsc*(facelmarks[:,0] + int(sl>=0)*5) + offW #nsW*(wsc*facelmarks[:,0]+offW).astype(np.int) # column
facelmarks[:,1] = hsc*(facelmarks[:,1] + int(st>=0)*5) + offH #nsH*(hsc*facelmarks[:,1]+offH).astype(np.int) # row
					
ch, cw = face.shape[0], face.shape[1]
facelmarks[:,0] = 112*(facelmarks[:,0]/float(cw))
facelmarks[:,1] = 112*(facelmarks[:,1]/float(ch))
facelmarks = facelmarks.reshape(5,2) #+ np.array([-2,2,0,-2,+2]).reshape(5,1)
'''

class FaceModelv4():
    def __init__(self, frame_resolution, detector_resolution, face_size, face_crop_offset, small_face_padding, small_face_size):
        self.frame_hw = frame_resolution
        self.det_hw = detector_resolution
        self.crop_offset = face_crop_offset
        self.face_padding = small_face_padding
        self.small_face_size = small_face_size
        self.face_size = face_size
        
        self.scale_hw = [self.frame_hw[i]/self.det_hw[i] for i in range(2)]
        
        use_large_detector = False
        if use_large_detector:
            self.detector = insightface.model_zoo.get_model('retinaface_r50_v1')
        else:
            self.detector = insightface.model_zoo.get_model('retinaface_mnet025_v2')
        
        ctx_id=0
        self.detector.prepare(ctx_id=ctx_id)
        
        
    def crop_face_from_frame(self, frame, detface):
        hsc, wsc = self.scale_hw
        
        det_scaled = detface.scale(self.scale_hw)
        det_scaled = Bbox(det_scaled)
        
        det_off = det_scaled.add_offset(offset_hw=[self.crop_offset, self.crop_offset])
        det_off = Bbox(det_off)
        
        w = det_off.width
        h = det_off.height 
        
        offW = 0 
        if w < self.small_face_size:
            offW = self.face_padding
        
        offH = 0 
        if h < self.small_face_size:
            offH = self.face_padding        
        
        # small face padding
        det_off2 = det_off.add_offset(offset_hw=[offH, offW])
        det_off2 = Bbox(det_off2)
        
        bbox = det_off2.assert_ltrb(self.frame_hw)
        face = frame[bbox['top']:bbox['bottom'], bbox['left']:bbox['right'], :]
        
        bbox = Bbox(bbox)
        return face, bbox
        
    def resize_face(self, face, bbx):

        ch, cw = face.shape[0], face.shape[1]
        # facelmarks = detface['lmarks'] - np.array([detface['left'], detface['top']]).reshape(1,2)
        facelmarks = bbx.lmarks - np.array([bbx.l, bbx.t]).reshape(1,2)
        
        facelmarks[:,0] = self.face_size*(facelmarks[:,0]/cw)
        facelmarks[:,1] = self.face_size*(facelmarks[:,1]/ch)
        facelmarks = facelmarks.reshape(5,2)
        
        face = resize(face, (self.face_size, self.face_size))
        face = np.uint8(255*face)
        
        return face, facelmarks
        
    def rotate_face(self, face_img, land_marks, angle=None):
        facecenter = land_marks.mean(axis=0).astype(np.int32)
        facecenter = facecenter.reshape(1,2)
        
        facelmarks = land_marks.astype(np.int32)
        
        #facelmarks = np.concatenate((land_marks, facecenter), axis=0)
        #facelmarks = facelmarks[:5,:]
        #facecenter = facelmarks[-1].astype(np.int32)
        
        ch, cw = face_img.shape[0], face_img.shape[1]

        curr_landmarks = facelmarks
        leye = (curr_landmarks[0,0], curr_landmarks[0,1])
        reye = (curr_landmarks[1,0], curr_landmarks[1,1])

        dY = reye[1] - leye[1]
        dX = reye[0] - leye[0]
        if angle is None:
            angle = np.degrees(np.arctan2(dY, dX)) #-180,180
        else:
            angle = angle_pre
        
        crop = 15
        face_imgcv = face_img[:,:,::-1] # rgb to bgr
        if abs(angle) >= 30:
            center_ = ((leye[0] + reye[0]) // 2, (leye[1] + reye[1]) // 2)
            #print(center_)
            M = cv2.getRotationMatrix2D((int(center_[0]), int(center_[1])), angle, scale=1.0)
            warped = cv2.warpAffine(face_imgcv, M, (cw, ch), borderMode=cv2.BORDER_REFLECT_101)
            warped = warped[crop:-crop,crop:-crop,::-1]
            face_img = resize(warped, (self.face_size, self.face_size))
            face_img = np.uint8(255*face_img)
        else:
            face_img = face_img[crop:-crop,crop:-crop,:]
            face_img = resize(face_img, (self.face_size, self.face_size))
            face_img = np.uint8(255*face_img)        
        
        return face_img, angle, curr_landmarks-crop
        
    def get_normalized_face(self, face_img, pts5=None, face=True):
        
        if not face:
            bbox, pts5 = self.detector.detect(face_img[:,:,[2,1,0]], threshold=0.28)
            if bbox.size==0 and pts5 is None:
                return face_img

        if pts5 is None or pts5.size==0:
            return face_img
        else:
            pts5 = pts5[0]
            #print(pts5, 'doing norm')
        
        # CONVERT RGB TO BGR image for opencv
        face_img_bgr = face_img[:,:,[2,1,0]]
        #print(face_img_bgr.shape, pts5.shape)
        nimg = face_align.norm_crop(face_img_bgr, pts5)
        
        # CONVERT BGR TO RGB back again
        nimg = nimg[:,:,[2,1,0]]
        #imsave('nface.png',nimg)
        #imsave('face.png',face_img)
        
        return nimg #face_img

