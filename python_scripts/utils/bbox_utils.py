from typing import Any

import numpy as np


class Bbox:
    def __init__(self, bbox) -> None:
        left, top, right, bottom = bbox["left"], bbox["top"], bbox["right"], bbox["bottom"]
        self.prob = bbox["prob"]
        self.landmarks = bbox.get("landmarks", None)

        self.left = left
        self.top = top
        self.right = right
        self.bottom = bottom

    @property
    def width(self):
        w = self.right - self.left + 1
        if not w >= 0:
            msg = "Negative values for bounding box width are not allowed"
            raise ValueError(msg)
        return w

    @property
    def height(self):
        h = self.bottom - self.top + 1
        if not h >= 0:
            msg = "Negative values for bounding box height are not allowed"
            raise ValueError(msg)
        return h

    def area(self):
        a = self.height() * self.width()
        if not a >= 0:
            msg = "Negative values for bounding box area are not allowed"
        return a

    def assert_left_top_right_bottom(self, resolution_height_and_width):
        resolution_height = resolution_height_and_width[0]
        resolution_width = resolution_height_and_width[1]

        left, top, right, bottom = self.left, self.top, self.right, self.bottom

        left = max(0, left)
        top = max(0, top)
        right = min(right, resolution_width)
        bottom = min(bottom, resolution_height)

        self.landmarks[:, 0] = self.landmarks[:, 0].clip(0, resolution_width)  # width
        self.landmarks[:, 1] = self.landmarks[:, 1].clip(0, resolution_height)  # height

        bbox = {}
        bbox["left"], bbox["top"], bbox["right"], bbox["bottom"] = [int(left), int(top), int(right), int(bottom)]
        bbox["prob"] = self.prob
        bbox["landmarks"] = self.landmarks.astype(np.int32)

        return bbox

    def return_dict(self) -> dict[str, Any]:
        return {"left": self.left, "top": self.top, "right": self.right, "bottom": self.bottom, "prob": self.prob, "landmarks": self.landmarks}

    def add_offset(self, height_and_width_offset):
        left, top, right, bottom = self.left, self.top, self.right, self.bottom

        height_offset = height_and_width_offset[0]
        width_offset = height_and_width_offset[1]

        left, top, right, bottom = (
            left - width_offset,
            top - height_offset,
            right + width_offset,
            bottom + height_offset,
        )

        if self.landmarks is not None:
            # self.landmarks[:,0] # along width
            # self.landmarks[:,1] # along height
            new_landmarks = np.zeros_like(self.landmarks)
            new_landmarks[:, 0] = self.landmarks[:, 0] + 0  # offset_hw[1]
            new_landmarks[:, 1] = self.landmarks[:, 1] + 0  # offset_hw[0]
        else:
            new_landmarks = None

        bbox = {}
        bbox["left"], bbox["top"], bbox["right"], bbox["bottom"] = left, top, right, bottom
        bbox["landmarks"] = new_landmarks
        bbox["prob"] = self.prob

        return bbox

    def scale(self, scale_hw):
        left, top, right, bottom = self.left, self.top, self.right, self.bottom
        left, top, right, bottom = left * scale_hw[1], top * scale_hw[0], right * scale_hw[1], bottom * scale_hw[0]
        left, top, right, bottom = [int(left), int(top), int(right), int(bottom)]

        # new_landmarks = np.zeros_like(self.landmarks)
        if self.landmarks is not None:
            # self.landmarks[:,0] # along width
            # self.landmarks[:,1] # along height
            new_landmarks = np.zeros_like(self.landmarks)
            new_landmarks[:, 0] = self.landmarks[:, 0] * scale_hw[1]
            new_landmarks[:, 1] = self.landmarks[:, 1] * scale_hw[0]
            new_landmarks = new_landmarks.astype(np.int32)
        else:
            new_landmarks = None

        bbox = {}
        bbox["left"], bbox["top"], bbox["right"], bbox["bottom"] = left, top, right, bottom
        bbox["landmarks"] = new_landmarks
        bbox["prob"] = self.prob

        return bbox
