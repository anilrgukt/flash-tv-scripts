import os
import sys

import cv2
import numpy as np


class FrameRotator:
    def __init__(
        self,
    ):
        self.rotate_flip = None
        self.rotate_angle = None
        self.rotate_count = 0
        self.rotate_count_tc = 0
        self.rotate_bool = [[0, 0], [0, 1], [0, 2], [1, 0], [1, 1], [1, 2]]  # ,[-1,-1]]
        self.rotate_status = 0
        self.quad = None

    def rotate(self, img2):
        self.rotate_flip, self.quad = self.rotate_bool[self.rotate_status]

        if self.rotate_flip >= 0:
            if self.rotate_flip:
                img2 = cv2.rotate(img2[:, :, ::-1], cv2.ROTATE_90_CLOCKWISE)
                self.rotate_angle = -90
            else:
                img2 = cv2.rotate(img2[:, :, ::-1], cv2.ROTATE_90_COUNTERCLOCKWISE)
                self.rotate_angle = 90

            img2 = img2[self.quad * 640 : (self.quad + 1) * 640, :, ::-1]

        self.rotate_count += 1
        return img2

    def update(self, tc_present, num_faces):
        # if 0 in idxs:
        if self.rotate_flip < 0:
            if not tc_present:  # tc not found in 2nd frame
                self.rotate_status = self.rotate_count % 6
        elif num_faces < 1:
            # rotate_flip = not rotate_flip
            self.rotate_status = self.rotate_count % 6
                # print('changing rot stat', rotate_status, rotate_count)
        return None

    def rotate_transform(self, bbox_ls):
        new_bbox_ls = []
        rotate_angle = self.rotate_angle
        quad = self.quad

        for bbox in bbox_ls:
            x_left, y_top, x_right, y_bottom = [bbox["left"], bbox["top"], bbox["right"], bbox["bottom"]]
            x_left, y_top, x_right, y_bottom = x_left * (1080 / 608.0), y_top * (640 / 342.0), x_right * (1080 / 608.0), y_bottom * (640 / 342.0)

            landmarks_ = bbox["landmarks"]  # x,y
            landmarks_[:, 0] = landmarks_[:, 0] * (1080 / 608.0)
            landmarks_[:, 1] = landmarks_[:, 1] * (640 / 342.0)
            landmarks = landmarks_.copy()

            if rotate_angle == 90:  # if rotated counter clockwise
                x_left1 = -(y_bottom + quad * 640 - 1920)
                y_top1 = x_left
                x_right1 = -(y_top + quad * 640 - 1920)
                y_bottom1 = x_right

                landmarks[:, 0] = -(landmarks_[:, 1] + quad * 640 - 1920)
                landmarks[:, 1] = landmarks_[:, 0]

            else:
                x_left1 = y_top + quad * 640
                y_top1 = -(x_right - 1080)
                x_right1 = y_bottom + quad * 640
                y_bottom1 = -(x_left - 1080)

                landmarks[:, 1] = -(landmarks_[:, 0] - 1080)
                landmarks[:, 0] = landmarks_[:, 1] + quad * 640

            x_left, y_top, x_right, y_bottom = (
                x_left1 * (608 / 1920.0),
                y_top1 * (342 / 1080.0),
                x_right1 * (608 / 1920.0),
                y_bottom1 * (342 / 1080.0),
            )
            landmarks[:, 0] = landmarks[:, 0] * (608 / 1920.0)
            landmarks[:, 1] = landmarks[:, 1] * (342 / 1080.0)

            bbox["left"], bbox["top"], bbox["right"], bbox["bottom"] = x_left, y_top, x_right, y_bottom
            bbox["landmarks"] = landmarks
            new_bbox_ls.append(bbox)
        return new_bbox_ls
