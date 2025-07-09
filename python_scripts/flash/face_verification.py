import os
from datetime import datetime

import torch
import cv2
import numpy as np
import imageio as io
from skimage.transform import resize

from utils.face_verification_utils import dist_mat, distance

from . import net


def load_pretrained_model(adaface_models, architecture="ir_101"):
    # load model and pretrained statedict
    assert architecture in adaface_models.keys()
    model = net.build_model(architecture)
    statedict = torch.load(adaface_models[architecture])["state_dict"]
    model_statedict = {key[6:]: val for key, val in statedict.items() if key.startswith("model.")}
    model.load_state_dict(model_statedict)
    return model


class FLASHFaceVerification:
    def __init__(self, model_path, num_identities, verification_threshold=0.436, gal_add_threshold=0.3, embedding_size=512, img_size=112):
        adaface_models = {
            "ir_101": model_path,
        }

        self.model = load_pretrained_model(adaface_models, "ir_101")
        self.model.cuda()
        self.model.eval()

        self.threshold = verification_threshold
        self.gal_threshold = gal_add_threshold
        self.emb_size = embedding_size
        self.img_size = img_size
        self.num_identities = num_identities

        self.gal_update = [True] * num_identities
        self.gal_updated_time = [datetime.now() for i in range(num_identities)]

    def to_input(self, rgb_image):
        assert rgb_image.max() > 1.0
        brg_img = ((rgb_image[:, :, :, ::-1] / 255.0) - 0.5) / 0.5  # h,w,3 --> B,h,w,3
        brg_img = brg_img.transpose(0, 3, 1, 2)
        tensor = torch.from_numpy(brg_img).float().cuda()

        return tensor

    def get_face_embeddings(self, detFacesLog):
        det_emb = np.zeros((int(len(detFacesLog) / 2), self.emb_size * 1))
        detFacesLog = np.array(detFacesLog)

        if detFacesLog.shape[0] > 0:
            emb_det = []
            for fe_id in range(0, detFacesLog.shape[0], 8):
                detFaceBatch = detFacesLog[fe_id : fe_id + 8]

                emb_batch, norm = self.model(self.to_input(detFaceBatch))
                emb_batch = emb_batch * norm
                emb_batch = emb_batch.cpu().detach().numpy()

                emb_det.append(emb_batch)

            emb_det = np.vstack(emb_det)

            det_emb = emb_det[0::2, :] + emb_det[1::2, :]

            detFacesLog = detFacesLog[0::2, :, :, :]

        return det_emb, detFacesLog

    def convert_embedding_faceid(self, ref_features, test_features, mean=0):
        dist = dist_mat(ref_features, test_features, mean)  # outputs numDET x numGT

        dist_cmp = np.array([])
        num_identities = self.num_identities
        if dist.shape[0] > 0:
            dist_res = np.copy(dist) - self.threshold
            dist_res[dist_res > 0] = 0
            dist_res = -(dist_res)

            ni = num_identities
            dist_cmp = (
                dist_res[:, :ni]
                + dist_res[:, ni : ni * 2]
                + dist_res[:, ni * 2 : ni * 3]
                + dist_res[:, ni * 3 : ni * 4]
                + dist_res[:, ni * 4 : ni * 5]
                + dist_res[:, ni * 5 : ni * 6]
            )

        dist_res = dist

        idxs = [i for i in range(num_identities)]  # 0,1,2,3
        gt_idxs = [-4, -3, -2]
        pred_idxs = []

        for i in range(dist_cmp.shape[0]):
            di = dist_cmp[i]
            idx = di.argmax()

            if (idx in idxs) and dist_cmp[:, idx].max() <= di[idx] and di[idx] > 0:
                idxs.remove(idx)
                pred_idxs.append(idx)

                if idx < 3 and di[idx] > self.gal_threshold and self.gal_update[idx]:
                    ref_features[gt_idxs[idx], :] = test_features[i]
                    self.gal_update[idx] = False
                    self.gal_updated_time[idx] = datetime.now()
                    print("Updated gallery face at idx:", idx, "at", self.gal_updated_time[idx].time())
            else:
                pred_idxs.append(4)

        return pred_idxs, ref_features

    def get_gt_emb(self, fam_id, path, face_proc):
        person_ids = ["tc", "sib", "parent", "extra"]
        person_nums = ["1", "2", "3", "4", "5", "5"]
        fnames = [fam_id + "_" + i for i in person_ids]

        gt_fname = []
        for i in person_nums:
            for j in fnames:
                gt_fname.append(j + i + ".png")

        gt_fname = [str(fam_id) + "_faces/" + i for i in gt_fname]
        gt_faces = []
        for fname in gt_fname:
            face = io.imread(os.path.join(path, fname))
            face = resize(face, (self.img_size, self.img_size))
            face = np.uint8(255 * face)

            face_flip = face[:, ::-1, :]
            gt_faces.append(face)
            gt_faces.append(face_flip)

        gt_faces = np.array(gt_faces)

        gt_embedding = np.zeros((len(gt_fname), self.emb_size * 1))

        gt_faces_inp = gt_faces.copy()
        for idx, face_img in enumerate(gt_faces_inp):
            gt_faces_inp[idx] = face_proc.get_normalized_face(face_img, face=False)

        emb_gt1, n1 = self.model(self.to_input(gt_faces_inp[:24, :, :, :]))
        emb_gt1 = emb_gt1.cpu().detach().numpy()
        n1 = n1.cpu().detach().numpy()
        emb_gt2, n2 = self.model(self.to_input(gt_faces_inp[24:, :, :, :]))
        emb_gt2 = emb_gt2.cpu().detach().numpy()
        n2 = n2.cpu().detach().numpy()

        emb_gt = np.concatenate((emb_gt1 * n1, emb_gt2 * n2), axis=0)

        print("GT data ....")
        print(gt_faces_inp.shape, emb_gt.shape)

        gt_embedding = emb_gt[0::2, :] + emb_gt[1::2, :]
        gt_faces = gt_faces[0::2, :, :, :]

        return gt_embedding
