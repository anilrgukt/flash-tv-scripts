import os
import sys
import numpy as np

usrname = str(sys.argv[3])
sys.path.insert(1, os.path.join('/home/'+usrname+'/FLASH_TV/python_wrapper'))

from face_detector_YOLOv2 import YoloFace
import skimage.io, skimage.transform
import imageio as io

import cv2 
import time
from datetime import datetime

import subprocess
import threading as th
from queue import Queue

def draw_rect(img, dboxes, show, save_file=None):
    cv_img = np.copy(img)
    tmp_channel = np.copy(cv_img[:,:,0])
    cv_img[:,:,0] = cv_img[:,:,2]
    cv_img[:,:,2] = tmp_channel  
    colors = {'TC':(0,255,0), 'Sib':(255,0,0), 'Par':(255,255,0)}
    if show is not None:
    	color = colors[show]
    else:
    	color = (0,0,255)
    	
    for i, dbox in enumerate(dboxes):
        if dbox['prob']>0.1:
            cv2.rectangle(cv_img, (int(dbox["left"]), int(dbox["top"])), (int(dbox["right"]), int(dbox["bottom"])), color, 2) 
        #cv2.circle(cv_img, (int(0.5 * (int(dbox["left"]) + int(dbox["right"]))), int(0.5 * (int(dbox["top"]) + int(dbox["bottom"])))), 2, (0,0,255))

    #cv2.imwrite(save_file, cv_img)
    if show is not None:
        text = show + ' being tracked'
        pos = (420,330)
        font = cv2.FONT_HERSHEY_SIMPLEX
        fontScale = 0.5
        textColor=(255, 0, 0)
        text_color_bg = (0,0,0)
        font_thickness = 1
    	
        x, y = pos
        text_size, _ = cv2.getTextSize(text, font, fontScale, font_thickness)
        text_w, text_h = text_size
        cv2.rectangle(cv_img, (x-5,y-text_h-10), (x + text_w+10, y + text_h), text_color_bg, -1)
        cv2.putText(cv_img, text, pos, font, fontScale, textColor, font_thickness)
    return cv_img


    
def area(boxA):
	boxAArea = (boxA['right'] - boxA['left'] + 1) * (boxA['bottom'] - boxA['top'] + 1)
	return boxAArea

imgSize = [1080, 1920]
detImgSize = [342, 608]
bboxScale = [ imgSize[i] /  float(detImgSize[i]) for i in range(2)]
hsc = bboxScale[0]
wsc = bboxScale[1]

def get_face(detface):
	off = 7
	dl = detface['left'] - off
	dr = detface['right'] + off
	dt = detface['top'] - off
	db = detface['bottom'] + off
                    
	w = dr-dl
	h = db-dt
	w = w*wsc
	h = h*hsc

	offW = 0 #max((100-w)/2.0, 0)
	offH = 0 #max((100-h)/2.0, 0)

	y1 = max(0, int(dt*hsc-offH))
	y2 = min(int(db*hsc+offH), 1080)
	x1 = max(0, int(dl*wsc-offW))
	x2 = min(int(dr*wsc+offW), 1920)
	#face = img[y1:y2, x1:x2, :]
	#face = skimage.transform.resize(face, [160, 160])
	return [x1,x2,y1,y2]




def cam_id():
	dev_list = subprocess.Popen('v4l2-ctl --list-devices'.split(), shell=False, stdout=subprocess.PIPE)
	out, err = dev_list.communicate()
	out = out.decode()
	dev_paths = out.split('\n')
	dev_path = None

	#WEBCAM_NAME = 'HD Pro Webcam C920'
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

def frame_write(q, frm_count, yolo):
	idx = cam_id()
	cap = cv2.VideoCapture(idx, cv2.CAP_V4L2)
	codec = cv2.VideoWriter_fourcc('M','J','P','G')
	#codec = cv2.VideoWriter_fourcc(*'MP4V')
	cap.set(6, codec)
	cap.set(5, 10)

	cap.set(3, 1920)
	cap.set(4, 1080)

	fps = int(cap.get(5))
	print('FPS: ', fps)

	count = frm_count

	global stop_capture
	stop_capture = False
	
	t_st = time.time()
	
	
	while(cap.isOpened() and not stop_capture): 
		ret, frame = cap.read()
		frame_time = cap.get(cv2.CAP_PROP_POS_MSEC)
		
		'''
		cv2.namedWindow('video_frames', cv2.WINDOW_NORMAL)
		cv2.imshow('video_frames', frame)
		#cv2.imshow(frame)
		cv2.resizeWindow('video_frames', 1280,720)
		cv2.setWindowTitle('video_frames', 'video_frames:  ' + str(count).zfill(6))
		

		if cv2.waitKey(1) & 0xFF == ord('q'):
			break
		'''

		if not ret:
			break
		
		if count%10 in [0,1]:	
			imgrgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			imgrgb = cv2.resize(imgrgb, (608,342))
			dboxes = yolo.yolo_detect_face(imgrgb)
			a = q.put([frame, count, imgrgb, dboxes])
			
		count += 1
		
		if (count+1)%100 == 0:
			tmp = 10
			print('time for captuing 100 images:::: ', time.time()-t_st)
			t_st = time.time()
			#break
		
	print('The cam for batch processing is stopped.')
	cap.release()
	cv2.destroyAllWindows()

print('starting the YoLo Face model')

yolo_model = YoloFace(os.path.join('/home/'+usrname+'/FLASH_TV/darknet_face_release'), 
                      config_path=os.path.join('/home/'+usrname+'/FLASH_TV/darknet_face_release/cfg/face-shallow-size608-anchor5.cfg'),
                      weight_path=os.path.join('/home/'+usrname+'/FLASH_TV/darknet_face_release/trained_models/face-shallow-size608-anchor5.weights')) 


print('starting the batch cam')
q = Queue(maxsize=100)
stop_capture = False
frm_counter = 0
p1 = th.Thread(target=frame_write, args=(q, frm_counter, yolo_model))
p1.start()

famId = sys.argv[1]
savePath = sys.argv[2]

imsave_dir = os.path.join(savePath, str(famId)+'_face_crops')
if not os.path.exists(imsave_dir):
	os.makedirs(imsave_dir)

frmsave_dir = os.path.join(savePath, str(famId)+'_face_frames')
if not os.path.exists(frmsave_dir):
	os.makedirs(frmsave_dir)

for idx in ['tc','sib','par']:
	tmp_path = os.path.join(imsave_dir, idx)
	tmp_path2 = os.path.join(imsave_dir, idx+'_selected')

	if not os.path.exists(tmp_path):
		os.makedirs(tmp_path)	

	if not os.path.exists(tmp_path2):
		os.makedirs(tmp_path2)	

show_face = None
sub_count = {'TC':0, 'Sib':0, 'Par':0}


cv2.namedWindow('video_frames', cv2.WINDOW_NORMAL)
cv2.resizeWindow('video_frames', 608,342)

record_frame = False
while True:
	
	if not q.empty():
		'''
		img_ls = []
		c_ls = []
		for i in range(3):
			img, c = q.get()
			img_ls.append(img)
			c_ls.append(c)
		'''
		img, c, imgrgb, dboxes = q.get()
		#cv2.imwrite('/media/FLASH_SSD/523_face_frames/'+str(c).zfill(6)+'.png', img)
		
		if c%60 == 0:
			print(c)

		#dboxes = yolo_model.yolo_detect_face(imgrgb)
		imgrgbd = draw_rect(imgrgb, dboxes, show_face)
		#tmp = [q.get() for i in range(1)]
		
		
		if show_face is not None:
			
			for detface in dboxes:
				if area(detface)>35.00 and detface['prob']>=0.11:
					[x1,x2,y1,y2] = get_face(detface)
					face = img[y1:y2, x1:x2, :]
					face = cv2.resize(face, (160,160))
					#face = np.uint8(255*face)
					output_path = os.path.join(imsave_dir, show_face.lower(), str(c).zfill(6)+'_'+str(sub_count[show_face])+'.png')  
					cv2.imwrite(output_path, face)
					if record_frame:
						fid = open(os.path.join(imsave_dir,show_face.lower()+'_frames.txt'),'a')
						fid.write(str(c).zfill(6)+'\n')
						fid.close()
						record_frame = False
					
					#skimage.io.imsave(output_path, face)
					sub_count[show_face] +=1 
		else:
			record_frame = True
				
		cv2.imshow('video_frames', imgrgbd)
		#cv2.imshow(frame)
		cv2.setWindowTitle('video_frames', 'video_frames:  ' + str(c).zfill(6))
		
		#print(q.qsize(), q.empty())
		# 
		pressedKey = cv2.waitKey(1) & 0xFF
		if pressedKey == ord('q'):
			stop_capture = True
			break
		elif pressedKey == ord('t'):
			show_face = 'TC'
			print('TC face being tracked')
		elif pressedKey == ord('s'):
			show_face = 'Sib'
			print('Sib face being tracked')
		elif pressedKey == ord('p'):
			show_face = 'Par'
			print('Parent face being tracked')
		elif pressedKey == ord('u'):
			show_face = None
			print('NO face being tracked')
	else:
		print('Queue is EMPTY')
		time.sleep(0.65)
