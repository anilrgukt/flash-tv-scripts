from __future__ import annotations

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


class FLASHtv:
    def __init__(self, username, family_id, num_identities, data_path, frame_res_hw, output_res_hw) -> None:
        ckpt1_r50 = "/home/" + username + "/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50.pth.tar"
        ckpt2_r50reg = "/home/" + username + "/gaze_models/model_v3_best_Gaze360ETHXrtGene_r50reg.pth.tar"

        model_path = "/home/" + username + "/Desktop/FLASH_TV_v3/AdaFace/pretrained/adaface_ir101_webface12m.ckpt"
        det_path_loc = "/home/" + username + "/insightface/detection/RetinaFace"

        self.ni = num_identities
        self.fd = FlashFaceDetector(det_path_loc)
        self.fv = FLASHFaceVerification(model_path, num_identities=self.ni)
        self.gz = FLASHGazeEstimator(ckpt1_r50, ckpt2_r50reg)
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

    def run_multi_gaze(self, frame_ls, frame_bbox_ls):
        """
        Run gaze estimation for all detected and verified faces, not just target child.
        Returns a dictionary mapping person IDs to their gaze data.
        """
        persons_data = {}
        
        for frame_idx, (img, bbox_ls) in enumerate(zip(frame_ls, frame_bbox_ls)):
            for bbx in bbox_ls:
                person_id = bbx["idx"]
                
                # Skip unknown faces (idx == -1 or >= num_identities)
                if person_id < 0 or person_id >= self.ni:
                    continue
                
                # Process face for gaze estimation
                bbx_ = Bbox(bbx)
                face, bbx_ = self.gaze_face_processing.crop_face_from_frame(img, bbx_)  # rgb
                face, lmarks = self.gaze_face_processing.resize_face(face, bbx_)  # rgb
                face_rot, angle, lmrks = self.gaze_face_processing.rotate_face(face, lmarks, angle=None)
                
                # Store additional info in bbox
                bbx["angle"] = angle
                bbx["new_lmrks"] = lmarks
                bbx["frame_idx"] = frame_idx
                
                # Initialize person data if not exists
                if person_id not in persons_data:
                    persons_data[person_id] = {
                        "faces": [],
                        "bboxes": [],
                        "frame_indices": []
                    }
                
                persons_data[person_id]["faces"].append(face_rot)
                persons_data[person_id]["bboxes"].append(bbx)
                persons_data[person_id]["frame_indices"].append(frame_idx)
        
        # Process gaze for each person
        results = {}
        for person_id, data in persons_data.items():
            if len(data["faces"]) > 0:
                # Prepare input for gaze estimation
                gaze_input = self.gz.to_input(data["faces"])
                output = self.gz.gaze_estimate(gaze_input)
                
                # Extract outputs from both models
                o1, e1 = output[0]
                o2, e2 = output[1]
                
                o1 = o1.cpu().data.numpy()
                e1 = e1.cpu().data.numpy()
                o2 = o2.cpu().data.numpy()
                e2 = e2.cpu().data.numpy()
                
                results[person_id] = {
                    "present": True,
                    "gaze_data": [o1, e1, o2, e2],
                    "bboxes": data["bboxes"],
                    "frame_indices": data["frame_indices"],
                    "faces": data["faces"]
                }
            else:
                results[person_id] = {
                    "present": False,
                    "gaze_data": None,
                    "bboxes": [],
                    "frame_indices": [],
                    "faces": []
                }
        
        return results
