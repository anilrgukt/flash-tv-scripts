import math

import torch
import torch.nn.functional as F
import torch.nn.parallel
import torch.optim
import torch.utils.data
from torch import nn

from .resnet import resnet18, resnet34, resnet50


class GazeLSTM(nn.Module):
    """
    GazeLSTM model using ResNet50 as the base model and LSTM for sequence processing.

    Attributes:
        img_feature_dim (int): Dimension of the CNN feature to represent each frame.
        base_model (nn.Module): Pretrained ResNet50 model.
        lstm (nn.LSTM): LSTM layer for sequence processing.
        last_layer (nn.Linear): Linear layer to map LSTM output to 3 outputs.
    """

    def __init__(self) -> None:
        super().__init__()
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame

        self.base_model = resnet50(pretrained=False)
        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)

        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim, bidirectional=True, num_layers=2, batch_first=True)

        # The linear layer that maps the LSTM with the 3 outputs
        self.last_layer = nn.Linear(2 * self.img_feature_dim, 3)

    def forward(self, input_: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass for the GazeLSTM model.

        Args:
            input_ (torch.Tensor): Input tensor.

        Returns:
            tuple[torch.Tensor, torch.Tensor]: Angular output and variance.
        """
        base_out = self.base_model(input_.view((-1, 3) + input_.size()[-2:]))
        base_out = base_out.view(input_.size(0), 7, self.img_feature_dim)

        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:, 3, :]
        output = self.last_layer(lstm_out).view(-1, 3)

        angular_output = output[:, :2]
        angular_output[:, 0:1] = math.pi * nn.Tanh()(angular_output[:, 0:1])
        angular_output[:, 1:2] = (math.pi / 2) * nn.Tanh()(angular_output[:, 1:2])

        var = math.pi * nn.Sigmoid()(output[:, 2:3])
        var = var.view(-1, 1).expand(var.size(0), 2)

        return angular_output, var


class GazeLSTMreg(nn.Module):
    """
    GazeLSTMreg model using ResNet34 as the base model and LSTM for sequence processing.

    Attributes:
        img_feature_dim (int): Dimension of the CNN feature to represent each frame.
        base_model (nn.Module): Pretrained ResNet34 model.
        lstm (nn.LSTM): LSTM layer for sequence processing.
        last_layer (nn.Linear): Linear layer to map LSTM output to 3 outputs.
    """

    def __init__(self) -> None:
        super().__init__()
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame

        self.base_model = resnet34(pretrained=False)
        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)

        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim, bidirectional=True, num_layers=2, batch_first=True)

        # The linear layer that maps the LSTM with the 3 outputs
        self.last_layer = nn.Linear(2 * self.img_feature_dim, 3)

    def forward(self, input_: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass for the GazeLSTMreg model.

        Args:
            input_ (torch.Tensor): Input tensor.

        Returns:
            tuple[torch.Tensor, torch.Tensor]: Angular output and variance.
        """
        base_out = self.base_model(input_.view((-1, 3) + input_.size()[-2:]))
        base_out = base_out.view(input_.size(0), 7, self.img_feature_dim)

        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:, 3, :]
        output = self.last_layer(lstm_out).view(-1, 3)

        angular_output = output[:, :2]
        angular_output[:, 0:1] = math.pi * nn.Tanh()(angular_output[:, 0:1])
        angular_output[:, 1:2] = (math.pi / 2) * nn.Tanh()(angular_output[:, 1:2])

        var = math.pi * nn.Sigmoid()(output[:, 2:3])
        var = var.view(-1, 1).expand(var.size(0), 2)

        return angular_output, var


class GazeLSTMFlash(nn.Module):
    """
    GazeLSTMFlash model using ResNet18 as the base model and LSTM for sequence processing.

    Attributes:
        img_feature_dim (int): Dimension of the CNN feature to represent each frame.
        base_model (nn.Module): Pretrained ResNet18 model.
        lstm (nn.LSTM): LSTM layer for sequence processing.
        last_layer (nn.Linear): Linear layer to map LSTM output to 3 outputs.
        flash_linlayer (nn.Linear): Linear layer for flash output.
        flash_lastlayer (nn.Linear): Final linear layer for flash output.
        sigmoid (nn.Sigmoid): Sigmoid activation function.
    """

    def __init__(self) -> None:
        super().__init__()
        self.img_feature_dim = 256  # the dimension of the CNN feature to represent each frame

        self.base_model = resnet18(pretrained=True)
        self.base_model.fc2 = nn.Linear(1000, self.img_feature_dim)

        self.lstm = nn.LSTM(self.img_feature_dim, self.img_feature_dim, bidirectional=True, num_layers=2, batch_first=True)

        # The linear layer that maps the LSTM with the 3 outputs
        self.last_layer = nn.Linear(2 * self.img_feature_dim, 3)

        self.flash_linlayer = nn.Linear(self.img_feature_dim, 32)
        self.flash_lastlayer = nn.Linear(32, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, input_: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass for the GazeLSTMFlash model.

        Args:
            input_ (torch.Tensor): Input tensor.

        Returns:
            tuple[torch.Tensor, torch.Tensor, torch.Tensor]: Angular output, variance, and FLASH output.
        """
        # Pass the input through the base model (ResNet18)
        base_out = self.base_model(input_.view((-1, 3) + input_.size()[-2:]))
        base_out = base_out.view(input_.size(0), 7, self.img_feature_dim)

        # Pass the base model output through the LSTM
        lstm_out, _ = self.lstm(base_out)
        lstm_out = lstm_out[:, 3, :]  # Select the output at the middle time step
        output = self.last_layer(lstm_out).view(-1, 3)

        # Process the base model output for the flash output
        fc1 = self.flash_linlayer(base_out[:, 3, :]).view(-1, 32)
        fc1_relu = F.relu(fc1)

        fc2 = self.flash_lastlayer(fc1_relu).view(-1, 1)
        fc2_sigmoid = self.sigmoid(fc2)

        # Calculate the angular output
        angular_output = output[:, :2]
        angular_output[:, 0:1] = math.pi * nn.Tanh()(angular_output[:, 0:1])
        angular_output[:, 1:2] = (math.pi / 2) * nn.Tanh()(angular_output[:, 1:2])

        # Calculate the variance
        var = math.pi * nn.Sigmoid()(output[:, 2:3])
        var = var.view(-1, 1).expand(var.size(0), 2)

        return angular_output, var, fc2_sigmoid


class PinBallLoss(nn.Module):
    """
    Custom PinBall loss function.

    Attributes:
        q1 (float): Quantile for the lower bound (0.1).
        q9 (float): Quantile for the upper bound (0.9).
    """

    def __init__(self) -> None:
        super().__init__()
        self.q1 = 0.1
        self.q9 = 1 - self.q1

    def forward(self, output_o: torch.Tensor, target_o: torch.Tensor, var_o: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for the PinBall loss function.

        Args:
            output_o (torch.Tensor): Model output.
            target_o (torch.Tensor): Target values.
            var_o (torch.Tensor): Variance of the output.

        Returns:
            torch.Tensor: Combined loss value.
        """
        q_10 = target_o - (output_o - var_o)
        q_90 = target_o - (output_o + var_o)

        loss_10 = torch.max(self.q1 * q_10, (self.q1 - 1) * q_10)
        loss_90 = torch.max(self.q9 * q_90, (self.q9 - 1) * q_90)

        loss_10 = torch.mean(loss_10)
        loss_90 = torch.mean(loss_90)

        return loss_10 + loss_90


class PinBallLossFlash(nn.Module):
    """
    Custom loss function combining pinball loss and binary cross-entropy (BCE) loss.

    Attributes:
        q1 (float): Quantile for the lower bound (0.1).
        q9 (float): Quantile for the upper bound (0.9).
        bce (nn.BCELoss): Binary cross-entropy loss function.
    """

    def __init__(self) -> None:
        super().__init__()
        self.q1: float = 0.1
        self.q9: float = 1 - self.q1
        self.bce: nn.BCELoss = nn.BCELoss()

    def forward(
        self, output_o: torch.Tensor, target_o: torch.Tensor, var_o: torch.Tensor, pred_gaze: torch.Tensor, gt_gaze: torch.Tensor
    ) -> torch.Tensor:
        """
        Forward pass for the custom loss function.

        Args:
            output_o (torch.Tensor): Model output.
            target_o (torch.Tensor): Target values.
            var_o (torch.Tensor): Variance of the output.
            pred_gaze (torch.Tensor): Predicted gaze values.
            gt_gaze (torch.Tensor): Ground truth gaze values.

        Returns:
            torch.Tensor: Combined loss value.
        """
        # Calculate the quantile losses
        q_10 = target_o - (output_o - var_o)
        q_90 = target_o - (output_o + var_o)

        loss_10 = torch.max(self.q1 * q_10, (self.q1 - 1) * q_10)
        loss_90 = torch.max(self.q9 * q_90, (self.q9 - 1) * q_90)

        # Mean of the quantile losses
        loss_10 = torch.mean(loss_10)
        loss_90 = torch.mean(loss_90)

        # Binary cross-entropy loss
        bce_loss = torch.mean(self.bce(pred_gaze, gt_gaze))

        # Combined loss
        return loss_10 + loss_90 + bce_loss
