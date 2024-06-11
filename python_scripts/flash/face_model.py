import insightface
import cv2
from utils import face_align

# face verification libs

#sys.path.insert(1, '/home/flashsys1/insightface/deploy')
#import face_model

#model_ = '/home/flashsys1/insightface/models/model-r100-ii/model,0'
#vec = model_.split(',')
#model_prefix = vec[0]
#model_epoch = int(vec[1])
#gpuid = 0
#fmodel = face_model.FaceModelv2(gpuid, model_prefix, model_epoch, batch_size=45, use_large_detector=False)

class FaceModelv2:
    def __init__(self, use_large_detector=False):
        if use_large_detector:
            self.detector = insightface.model_zoo.get_model('retinaface_r50_v1')
        else:
            self.detector = insightface.model_zoo.get_model('retinaface_mnet025_v2')
        
        ctx_id=0
        self.detector.prepare(ctx_id=ctx_id)
        
        image_size = (112,112)
        #model_prefix, model_epoch, batch_size,
        #self.model = get_model(ctx, image_size, model_prefix, model_epoch, layer='fc1', batch_size=batch_size)
        self.image_size = image_size

    def get_input(self, face_img, pts5=None, face=True):
        
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


