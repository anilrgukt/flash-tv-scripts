import os
import sys

import cv2
import numpy as np
import math
import time

import threading
import subprocess
from subprocess import Popen, PIPE
import fcntl

from skimage.transform import resize
from imageio import imread, imsave
from datetime import datetime

def draw_rect_det(img, dboxes, save_file):
    cv_img = np.copy(img)
    tmp_channel = np.copy(cv_img[:,:,0])
    cv_img[:,:,0] = cv_img[:,:,2]
    cv_img[:,:,2] = tmp_channel  
    for i, dbox in enumerate(dboxes):
        if dbox['prob']>0.03:
            cv2.rectangle(cv_img, (int(dbox["left"]), int(dbox["top"])), (int(dbox["right"]), int(dbox["bottom"])), (0,0,255), 2) 
        #cv2.circle(cv_img, (int(0.5 * (int(dbox["left"]) + int(dbox["right"]))), int(0.5 * (int(dbox["top"]) + int(dbox["bottom"])))), 2, (0,0,255))

    cv2.imwrite(save_file, cv_img)
    return cv_img
    
def draw_rect_ver(img, dboxes1, dboxes2, save_file):
    cv_img = np.copy(img)
    tmp_channel = np.copy(cv_img[:,:,0])
    cv_img[:,:,0] = cv_img[:,:,2]
    cv_img[:,:,2] = tmp_channel
    
    l = [(0,255,0),(255,0,0),(255,255,0),(255,0,255),(0,0,255)]

    draw_lmarks = True
    for i, dbox in enumerate(dboxes1):
        cv2.rectangle(cv_img, (int(dbox["left"]), int(dbox["top"])), (int(dbox["right"]), int(dbox["bottom"])), l[dbox['idx']], 2) 
        lmarks = dbox['lmarks']
        lmcolor = [(0,0,255),(0,255,0),(255,0,0),(255,255,0),(0,0,0)] #rgbc,black
        if draw_lmarks:
            for lm in range(lmarks.shape[0]):  
                color = (0, 0, 255)
                if lm == 0 or lm == 3:
                    color = (0, 255, 0)
                cv2.circle(cv_img, (lmarks[lm,0], lmarks[lm,1]), 1, color, 2)

    if dboxes2 is not None:
        for i, dbox in enumerate(dboxes2):
               cv2.rectangle(cv_img, (int(dbox["left"])+2, int(dbox["top"])+2), (int(dbox["right"])+2, int(dbox["bottom"])+2), (0,255,0), 1) 

    cv2.imwrite(save_file, cv_img)
    return cv_img
    
#draw_rect_gz(batch10_img608[i], (int(sx),int(sy)), (int(sx+x),int(sy+y)), color, os.path.join(BASE_PATH_IMG,output_name))
def draw_rect_gz(img, frm, start, end, color, save_file):
    cv_img = np.copy(img)
    tmp_channel = np.copy(cv_img[:,:,0])
    cv_img[:,:,0] = cv_img[:,:,2]
    cv_img[:,:,2] = tmp_channel

    #l = [(0,255,0),(255,0,0),(255,255,0),(255,0,255),(0,0,255)]
    l = [(255,0,0),(0,255,0),(0,0,255),(255,0,255),(0,0,255)]

    if start is not None:
        cv2.arrowedLine(cv_img, start, end, l[color], 3, tipLength=0.5) 
    
    cv2.putText(cv_img,str(frm), (455,30), cv2.FONT_HERSHEY_PLAIN, 2, 255)
    cv2.imwrite(save_file, cv_img)
    return cv_img
    
def draw_rect_gz(img, frm, start, end, color, save_file):
    cv_img = np.copy(img)
    tmp_channel = np.copy(cv_img[:,:,0])
    cv_img[:,:,0] = cv_img[:,:,2]
    cv_img[:,:,2] = tmp_channel

    #l = [(0,255,0),(255,0,0),(255,255,0),(255,0,255),(0,0,255)]
    l = [(255,0,0),(0,255,0),(0,0,255),(255,0,255),(0,0,255)]

    if start is not None:
        cv2.arrowedLine(cv_img, start, end, l[color], 3, tipLength=0.5) 
    
    cv2.putText(cv_img,str(frm), (455,30), cv2.FONT_HERSHEY_PLAIN, 2, 255)
    cv2.imwrite(save_file, cv_img)
    return cv_img    
    
def area(boxA):
    boxAArea = (boxA['right'] - boxA['left'] + 1) * (boxA['bottom'] - boxA['top'] + 1)
    return boxAArea

def remove_prob(d):
    r = dict(d)
    del r['prob']
    return r

def dist_mat(gt, det, mean=0):
    mean = np.expand_dims(mean,0)
    mat = np.zeros((det.shape[0], gt.shape[0]))
    for i in range(det.shape[0]):
        emb1 = det[i:i+1, :]
        for j in range(gt.shape[0]):
            emb2 = gt[j:j+1, :]
            dist = distance(emb1-mean, emb2-mean, distance_metric=1)
            mat[i,j] = dist
            #mat[i,j] = np.cos(dist*math.pi)
    return mat

def distance(embeddings1, embeddings2, distance_metric=0):
    if distance_metric==0:
        # Euclidian distance
        diff = np.subtract(embeddings1, embeddings2)
        dist = np.sum(np.square(diff),1)
    elif distance_metric==1:
        # Distance based on cosine similarity
        dot = np.sum(np.multiply(embeddings1, embeddings2), axis=1)
        norm = np.linalg.norm(embeddings1, axis=1) * np.linalg.norm(embeddings2, axis=1)
        similarity = dot / norm
        dist = np.arccos(similarity) / math.pi
    else:
        raise 'Undefined distance metric %d' % distance_metric 
        
    return dist


def get_face(img, detface, wsc, hsc):
    off = 5
    dl = detface['left'] - off
    dr = detface['right'] + off
    dt = detface['top'] - off
    db = detface['bottom'] + off
                    
    w = dr-dl
    h = db-dt
    w = w*wsc
    h = h*hsc

    offW = 0 #max((100-w)/2.0, 0)
    if w < 65:
        offW = 7
    offH = 0 #max((100-h)/2.0, 0)
    if h < 65:
        offH = 7

    y1 = max(0, int(dt*hsc-offH))
    y2 = min(int(db*hsc+offH), 1080)
    x1 = max(0, int(dl*wsc-offW))
    x2 = min(int(dr*wsc+offW), 1920)
    face = img[y1:y2, x1:x2, :]
    
    #face = (face - 0.5)/0.5
    #print('processed face', face.min(), face.max())
    return face, [x2-x1,y2-y1,offW,offH,dl,dt]    


def get_tc_face(img, detface, wsc, hsc):
    off = 15
    dl = detface['left'] - off
    dr = detface['right'] + off
    dt = detface['top'] - off
    db = detface['bottom'] + off
                    
    w = dr-dl
    h = db-dt
    w = w*wsc
    h = h*hsc

    offW = 0 #max((100-w)/2.0, 0)
    if w < 65:
        offW = 3
    offH = 0 #max((100-h)/2.0, 0)
    if h < 65:
        offH = 3

    y1 = max(0, int(dt*hsc-offH))
    y2 = min(int(db*hsc+offH), 1080)
    x1 = max(0, int(dl*wsc-offW))
    x2 = min(int(dr*wsc+offW), 1920)
    if img is not None:
        face = img[y1:y2, x1:x2, :]
        return face, [x2-x1,y2-y1,offW,offH,dl,dt]
    else:
        return x2-x1, y2-y1, x1, y1
        
def rotate_tc_face(tcface, face, wsc, hsc, sl, st, offW, offH,angle_pre):
    facecenter = face['lmarks'].mean(axis=0).astype(np.int32)
    facecenter = facecenter.reshape(1,2)

    #print(detface)
    #facelmarks = face['lmarks'] - np.array([face['left'], face['top']]).reshape(1,2)

    facelmarks = np.concatenate((face['lmarks'],facecenter),axis=0) - np.array([face['left'], face['top']]).reshape(1,2)


    facelmarks[:,0] = wsc*(facelmarks[:,0]+int(sl>=0)*15) + offW #nsW*(wsc*facelmarks[:,0]+offW).astype(np.int)
    facelmarks[:,1] = hsc*(facelmarks[:,1]+int(st>=0)*15) + offH #nsH*(hsc*facelmarks[:,1]+offH).astype(np.int)
    #facelmarks6 = facelmarks.copy()
    
    ch, cw = tcface.shape[0], tcface.shape[1]

    #facelmarks[:,0] = 160*(facelmarks[:,0]/float(cw))
    #facelmarks[:,1] = 160*(facelmarks[:,1]/float(ch))

    facelmarks = facelmarks[:5,:]
    facecenter = facelmarks[-1].astype(np.int32)

    curr_landmarks = facelmarks.astype(np.int32)
    leye = (curr_landmarks[0,0], curr_landmarks[0,1])
    reye = (curr_landmarks[1,0], curr_landmarks[1,1])

    dY = reye[1] - leye[1]
    dX = reye[0] - leye[0]
    if angle_pre is None:
        angle = np.degrees(np.arctan2(dY, dX)) #-180,180
    else:
        angle = angle_pre

    
    if abs(angle) >= 30:
        center_ = ((leye[0] + reye[0]) // 2, (leye[1] + reye[1]) // 2)
        #print(center_)
        M = cv2.getRotationMatrix2D((int(center_[0]), int(center_[1])), angle, scale=1.0)
        warped = cv2.warpAffine(tcface[:,:,::-1], M, (cw, ch), borderMode=cv2.BORDER_REFLECT_101)
        warped = warped[15:-15,15:-15,::-1]
        tcface = resize(warped, (160, 160))
        tcface = np.uint8(255*tcface)
    else:
        tcface = tcface[15:-15,15:-15,:]
        tcface = resize(tcface, (160, 160))
        tcface = np.uint8(255*tcface)
    return tcface, angle


def rotate_tc_face_with_angle(tcface, angle):

    ch, cw = tcface.shape[0], tcface.shape[1]
    center_ = (ch // 2, cw // 2)
    if abs(angle) >= 30:
        #print(center_)
        M = cv2.getRotationMatrix2D((int(center_[0]), int(center_[1])), angle, scale=1.0)
        warped = cv2.warpAffine(tcface[:,:,::-1], M, (cw, ch), borderValue=0.0)
        warped = warped[22:-22,22:-22,::-1]
        tcface = resize(warped, (160, 160))
        tcface = np.uint8(255*tcface)
    else:
        tcface = resize(tcface, (160, 160))
        tcface = np.uint8(255*tcface)

    return tcface, angle

class WebcamVideoStream:
    """
    Reference:
    https://www.pyimagesearch.com/2015/12/21/increasing-webcam-fps-with-python-and-opencv/
    """

    def __init__(self):
        self.vid = None
        self.running = False
        return

    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()
        return
        
    def start(self, src, width=None, height=None, fps=None, set_codec=True):
        # initialize the video camera stream and read the first frame
        self.vid = cv2.VideoCapture(src, cv2.CAP_V4L2)
        
        if not self.vid.isOpened():
            # camera failed
            print('THE camera could not be opened', datetime.now())
            raise IOError(("Couldn't open video file or webcam at", str(datetime.now())))
        
        if set_codec:
            codec = cv2.VideoWriter_fourcc('M','J','P','G')
            self.vid.set(6, codec)
        
        if width is not None and height is not None:
            self.vid.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.vid.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            
        if fps is not None:
            self.vid.set(5, fps)
            
            
        self.ret, self.frame = self.vid.read()
        if not self.ret:
            self.vid.release()
            print("Couldn't open video frame.", str(datetime.now()))
            raise IOError(("Couldn't open video frame.", str(datetime.now())))

        # initialize the variable used to indicate if the thread should
        # check camera vid shape
        self.real_width = int(self.vid.get(3))
        self.real_height = int(self.vid.get(4))
        self.real_fps = int(self.vid.get(5))
        print("Start video stream with shape and fps: {},{},{}".format(self.real_width, self.real_height, self.real_fps))
        self.running = True

        # start the thread to read frames from the video stream
        t = threading.Thread(target=self.update, args=())
        t.setDaemon(True)
        t.start()
        return self

    def update(self):
        try:
            # keep looping infinitely until the stream is closed
            while self.running:
                # otherwise, read the next frame from the stream
                self.ret, self.frame = self.vid.read()
        except:
            import traceback
            traceback.print_exc()
            self.running = False
        finally:
            # if the thread indicator variable is set, stop the thread
            self.vid.release()
        return

    def read(self):
        # return the frame most recently read
        return self.frame

    def stop(self):
        self.running = False
        time.sleep(5)
        if self.vid.isOpened():
            self.vid.release()
            time.sleep(5)
        return
        
def create_usb_list():
    device_list = list()
    try:
        lsusb_out = Popen('lsusb -v', shell=True, bufsize=64, stdin=PIPE, stdout=PIPE, close_fds=True).stdout.read().strip().decode('utf-8')
        usb_devices = lsusb_out.split('%s%s' % (os.linesep, os.linesep))
        for device_categories in usb_devices:
            if not device_categories:
                continue
            categories = device_categories.split(os.linesep)
            device_stuff = categories[0].strip().split()
            bus = device_stuff[1]
            device = device_stuff[3][:-1]
            device_dict = {'bus': bus, 'device': device}
            device_info = ' '.join(device_stuff[6:])
            device_dict['description'] = device_info
            for category in categories:
                if not category:
                    continue
                categoryinfo = category.strip().split()
                if categoryinfo[0] == 'iManufacturer':
                    manufacturer_info = ' '.join(categoryinfo[2:])
                    device_dict['manufacturer'] = manufacturer_info
                if categoryinfo[0] == 'iProduct':
                    device_info = ' '.join(categoryinfo[2:])
                    device_dict['device'] = device_info
            path = '/dev/bus/usb/%s/%s' % (bus, device)
            device_dict['path'] = path

            device_list.append(device_dict)
    except Exception as ex:
        print('Failed to list usb devices! Error: %s' % ex)
        sys.exit(-1)
    return device_list

def reset_usb_device(dev_path):
    USBDEVFS_RESET = 21780
    try:
        f = open(dev_path, 'w', os.O_WRONLY)
        fcntl.ioctl(f, USBDEVFS_RESET, 0)
        print('Successfully reset %s' % dev_path)
        sys.exit(0)
    except Exception as ex:
        print('Failed to reset device! Error: %s' % ex)
        sys.exit(-1)

def cam_id():
    dev_list = subprocess.Popen('v4l2-ctl --list-devices'.split(), shell=False, stdout=subprocess.PIPE)
    out, err = dev_list.communicate()
    out = out.decode()
    dev_paths = out.split('\n')
    dev_path = None

    # WEBCAM_NAME = 'HD Pro Webcam C920' # Logitech Webcam C930e
    WEBCAM_NAME1 = 'Logitech Webcam C930e'
    #WEBCAM_NAME2 = 'USB  Live camera: USB  Live cam'
    WEBCAM_NAME2 = 'Anker PowerConf C300: Anker Pow'
    
    dev_name = {WEBCAM_NAME1:'C930e', WEBCAM_NAME2: 'C300'}
    
    which_webcam = None
    for i in range(len(dev_paths)):
        #print(i, dev_paths[i])
        if (WEBCAM_NAME1 in dev_paths[i]):  
            dev_path = dev_paths[i+1].strip()
            which_webcam = WEBCAM_NAME1
            break
            #print(dev_path, dev_path[-1])
        elif (WEBCAM_NAME2 in dev_paths[i]):
            dev_path = dev_paths[i+1].strip()
            which_webcam = WEBCAM_NAME2
            break

    if dev_path is not None:
        cam_idx = int(dev_path[-1])    
    else:
        cam_idx = -1
        
    print('CAMER identified at: ', cam_idx)
    
    usb_list = create_usb_list()
    usb_path = None
    for device in usb_list:
        text = '%s %s %s' % (device['description'], device['manufacturer'], device['device'])
        #print(text)
        if dev_name[which_webcam] in text:
            print(dev_name[which_webcam], device['path'])
            usb_path = device['path']
            reset_usb_device(device['path'])
    
    if usb_path is None:   
        print('Failed to find the the usb path for the camera!', dev_name[which_webcam])
    
    return cam_idx

