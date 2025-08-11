from __future__ import annotations

# Initialize STRICT GPU memory management BEFORE any model imports
from utils.gpu_memory_manager_v2 import initialize_strict_gpu_memory
manager = initialize_strict_gpu_memory()

import os
import pickle
import time

import cv2
import numpy as np
from flash.face_detection import FlashFaceDetector
from flash.face_processing import FaceModelv4 as FaceProcessing
from flash.face_verification import FLASHFaceVerification
from flash.gaze_estimation import FLASHGazeEstimator

from utils.bbox_utils import Bbox
from utils.visualizer import draw_gz, draw_rect_det, draw_rect_ver
from utils.gpu_memory_manager_v2 import GPUMemoryManagerV2


class FLASHtv:
    def __init__(self, username, family_id, num_identities, data_path, frame_res_hw, output_res_hw) -> None:
        ckpt1_r50 = "/home/" + username + "/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar"
        ckpt2_r50reg = "/home/" + username + "/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50reg.pth.tar"

        model_path = "/home/" + username + "/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt"
        det_path_loc = "/home/" + username + "/insightface/detection/RetinaFace"

        self.ni = num_identities
        
        # Load models with memory monitoring
        print("\nInitializing FLASH-TV Models with GPU Memory Management...")
        
        # 1. Load RetinaFace (uses MXNet memory pool) - STRICT MONITORING
        self.fd = GPUMemoryManagerV2.monitor_model_loading_v2(
            "RetinaFace Detector",
            lambda: FlashFaceDetector(det_path_loc)
        )
        
        # 2. Load AdaFace (largest PyTorch model) - STRICT MONITORING
        self.fv = GPUMemoryManagerV2.monitor_model_loading_v2(
            "AdaFace Verification", 
            lambda: FLASHFaceVerification(model_path, num_identities=self.ni)
        )
        
        # 3. Load Gaze Estimator (dual ResNet models) - STRICT MONITORING
        self.gz = GPUMemoryManagerV2.monitor_model_loading_v2(
            "Gaze Estimation Models",
            lambda: FLASHGazeEstimator(ckpt1_r50, ckpt2_r50reg)
        )
        self.face_processing = FaceProcessing(
            frame_resolution=[1080, 1920],
            detector_resolution=[342, 608],
            face_size=112,
            face_crop_offset=16,
            small_face_padding=7,
            small_face_size=65,
        )
        self.gaze_face_processing = FaceProcessing(
            frame_resolution=[1080, 1920],
            detector_resolution=[342, 608],
            face_size=160,
            face_crop_offset=45,
            small_face_padding=3,
            small_face_size=65,
        )

        self.family_id = family_id
        self.data_path = data_path

        self.gt_embedding = self.fv.get_gt_emb(fam_id=self.family_id, path=self.data_path, face_proc=self.face_processing)
        
        # Final comprehensive memory status after all models loaded
        GPUMemoryManagerV2.print_comprehensive_memory_status("All Models Loaded")

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
            facen = self.face_processing.get_normalized_face(face, lmarks.astype(np.int32).reshape(1, 5, 2), face=True)

            cropped_aligned_faces.append(facen)
            cropped_aligned_faces.append(facen[:, ::-1, :])

        cropped_aligned_faces = np.array(cropped_aligned_faces)
        det_emb, cropped_aligned_faces = self.fv.get_face_embeddings(cropped_aligned_faces)
        pred_ids, _ = self.fv.convert_embedding_faceid(ref_features=self.gt_embedding, test_features=det_emb, mean=0)

        for i in range(len(bls)):
            bls[i]["idx"] = pred_ids[i]

        return bls

    def run_gaze(self, frame_ls, frame_bbox_ls):
        tc_imgs = []
        tc_boxs = []
        tc_id = -1
        tc_frame_id = 0
        for img, bbox_ls in zip(frame_ls, frame_bbox_ls):
            tc_frame_id += 1
            for bbx in bbox_ls:
                if bbx["idx"] == 0:
                    bbx_ = Bbox(bbx)
                    face, bbx_ = self.gaze_face_processing.crop_face_from_frame(img, bbx_)  # rgb
                    face, lmarks = self.gaze_face_processing.resize_face(face, bbx_)  # rgb
                    face_rot, angle, lmrks = self.gaze_face_processing.rotate_face(face, lmarks, angle=None)
                    bbx["angle"] = angle
                    bbx["new_lmrks"] = lmarks
                    # print(bbx_.return_dict())
                    # print(lmarks)
                    tc_face = face_rot
                    tc_bbx = bbx

                    tc_imgs.append(tc_face)
                    tc_boxs.append(tc_bbx)
                    tc_id = tc_frame_id - 1

        tc_present = False
        gz_data = None

        if len(tc_imgs) > 0:
            tc_present = True
            gaze_input = self.gz.to_input(tc_imgs)
            output = self.gz.gaze_estimate(gaze_input)
            o1, e1 = output[0]
            o2, e2 = output[1]

            o1 = o1.cpu().data.numpy()
            e1 = e1.cpu().data.numpy()

            o2 = o2.cpu().data.numpy()
            e2 = e2.cpu().data.numpy()

            gz_data = [o1, e1, o2, e2]
            tc_bbx = tc_boxs[0]

        return tc_present, gz_data, tc_boxs, tc_id, tc_imgs
