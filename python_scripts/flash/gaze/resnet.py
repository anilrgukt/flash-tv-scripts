from __future__ import annotations

from typing import TYPE_CHECKING

from torch.nn import AdaptiveAvgPool2d, AvgPool2d, BatchNorm2d, Conv2d, Linear, MaxPool2d, Module, ReLU, Sequential, init
from torch.utils import model_zoo

if TYPE_CHECKING:
    import torch

__all__ = ["ResNet", "resnet18", "resnet34", "resnet50", "resnet101", "resnet152"]


model_urls = {
    "resnet18": "https://download.pytorch.org/models/resnet18-5c106cde.pth",
    "resnet34": "https://download.pytorch.org/models/resnet34-333f7ec4.pth",
    "resnet50": "https://download.pytorch.org/models/resnet50-19c8e357.pth",
    "resnet101": "https://download.pytorch.org/models/resnet101-5d3b4d8f.pth",
    "resnet152": "https://download.pytorch.org/models/resnet152-b121ed2d.pth",
}


class BasicBlock(Module):
    expansion: int = 1

    def __init__(self, in_channels: int, out_channels: int, stride: int = 1, downsample: Module | None = None) -> None:
        """
        Initializes the BasicBlock.

        Args:
            in_channels (int): Number of input channels.
            out_channels (int): Number of output channels.
            stride (int, optional): Stride of the convolution. Default is 1.
            downsample (Module, optional): Downsampling layer. Default is None.
        """
        super().__init__()
        self.conv1 = Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn1 = BatchNorm2d(out_channels)
        self.relu = ReLU(inplace=True)
        self.conv2 = Conv2d(in_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = BatchNorm2d(out_channels)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for the BasicBlock.

        Args:
            x (torch.Tensor): Input tensor.

        Returns:
            torch.Tensor: Output tensor after passing through the block.
        """
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class Bottleneck(Module):
    expansion: int = 4

    def __init__(self, in_channels: int, out_channels: int, stride: int = 1, downsample: Module | None = None) -> None:
        """
        Initializes the Bottleneck block.

        Args:
            in_channels (int): Number of input channels.
            out_channels (int): Number of output channels.
            stride (int, optional): Stride of the convolution. Default is 1.
            downsample (Module, optional): Downsampling layer. Default is None.
        """
        super().__init__()
        self.conv1 = Conv2d(in_channels, out_channels, kernel_size=1, bias=False)
        self.bn1 = BatchNorm2d(out_channels)
        self.conv2 = Conv2d(out_channels, out_channels, kernel_size=3, stride=stride, padding=1, bias=False)
        self.bn2 = BatchNorm2d(out_channels)
        self.conv3 = Conv2d(out_channels, out_channels * self.expansion, kernel_size=1, bias=False)
        self.bn3 = BatchNorm2d(out_channels * self.expansion)
        self.relu = ReLU(inplace=True)
        self.downsample = downsample
        self.stride = stride

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for the Bottleneck block.

        Args:
            x (torch.Tensor): Input tensor.

        Returns:
            torch.Tensor: Output tensor after passing through the block.
        """
        residual = x

        out = self.conv1(x)
        out = self.bn1(out)
        out = self.relu(out)

        out = self.conv2(out)
        out = self.bn2(out)
        out = self.relu(out)

        out = self.conv3(out)
        out = self.bn3(out)

        if self.downsample is not None:
            residual = self.downsample(x)

        out += residual
        out = self.relu(out)

        return out


class ResNet(Module):
    def __init__(self, block: Module, layers: list[int], num_classes: int = 1000) -> None:
        """
        Initializes the ResNet model.

        Args:
            block (Module): The block type to be used (BasicBlock or Bottleneck).
            layers (list[int]): Number of blocks in each layer.
            num_classes (int, optional): Number of output classes. Default is 1000.
        """
        super().__init__()
        self.in_channels = 64
        self.conv1 = Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = BatchNorm2d(64)
        self.relu = ReLU(inplace=True)
        self.maxpool = MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = AdaptiveAvgPool2d((1, 1))
        self.fc1 = Linear(512 * block.expansion, 1000)
        self.fc2 = Linear(1000, num_classes)

        # Initialize weights
        for m in self.modules():
            if isinstance(m, Conv2d):
                init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, BatchNorm2d):
                init.constant_(m.weight, 1)
                init.constant_(m.bias, 0)

    def _make_layer(self, block: Module, out_channels: int, blocks: int, stride: int = 1) -> Sequential:
        """
        Creates a layer consisting of multiple blocks.

        Args:
            block (Module): The block type to be used (BasicBlock or Bottleneck).
            out_channels (int): Number of output channels.
            int): Number of blocks in the layer.
            stride (int, optional): Stride of the first block. Default is 1.

        Returns:
            Sequential: A sequential container of blocks.
        """
        downsample = None
        if stride != 1 or self.in_channels != out_channels * block.expansion:
            downsample = Sequential(
                Conv2d(self.in_channels, out_channels * block.expansion, kernel_size=1, stride=stride, bias=False),
                BatchNorm2d(out_channels * block.expansion),
            )

        layers = []
        layers.append(block(self.in_channels, out_channels, stride, downsample))
        self.in_channels = out_channels * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.in_channels, out_channels))

        return Sequential(*layers)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass for the ResNet model.

        Args:
            x (torch.Tensor): Input tensor.

        Returns:
            torch.Tensor: Output tensor after passing through the model.
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        x = self.layer2(x)
        x = self.layer3(x)
        x = self.layer4(x)
        x = self.avgpool(x)
        x = x.view(x.size(0), -1)
        x = self.relu(self.fc1(x))
        x = self.fc2(x)

        return x


class ResNetCAM(Module):
    def __init__(self, block: Module, layers: list[int], num_classes: int = 1000) -> None:
        """
        Initializes the ResNetCAM model.

        Args:
            block (Module): The block type to be used (BasicBlock or Bottleneck).
            layers (list[int]): Number of blocks in each layer.
            num_classes (int, optional): Number of output classes. Default is 1000.
        """
        super().__init__()
        self.in_channels = 64
        self.conv1 = Conv2d(3, 64, kernel_size=7, stride=2, padding=3, bias=False)
        self.bn1 = BatchNorm2d(64)
        self.relu = ReLU(inplace=True)
        self.maxpool = MaxPool2d(kernel_size=3, stride=2, padding=1)
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2)
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2)
        self.avgpool = AvgPool2d(7, stride=1)
        self.fc1 = Linear(512 * block.expansion, 1000)
        self.fc2 = Linear(1000, num_classes)

        # Initialize weights
        for m in self.modules():
            if isinstance(m, Conv2d):
                init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, BatchNorm2d):
                init.constant_(m.weight, 1)
                init.constant_(m.bias, 0)

    def _make_layer(self, block: Module, out_channels: int, blocks: int, stride: int = 1) -> Sequential:
        """
        Creates a layer consisting of multiple blocks.

        Args:
            block (Module): The block type to be used (BasicBlock or Bottleneck).
            out_channels (int): Number of output channels.
            blocks (int): Number of blocks in the layer.
            stride (int, optional): Stride of the first block. Default is 1.

        Returns:
            Sequential: A sequential container of blocks.
        """
        downsample = None
        if stride != 1 or self.in_channels != out_channels * block.expansion:
            downsample = Sequential(
                Conv2d(self.in_channels, out_channels * block.expansion, kernel_size=1, stride=stride, bias=False),
                BatchNorm2d(out_channels * block.expansion),
            )

        layers = []
        layers.append(block(self.in_channels, out_channels, stride, downsample))
        self.in_channels = out_channels * block.expansion
        for _ in range(1, blocks):
            layers.append(block(self.in_channels, out_channels))

        return Sequential(*layers)

    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass for the ResNetCAM model.

        Args:
            x (torch.Tensor): Input tensor.

        Returns:
            tuple[torch.Tensor, torch.Tensor]: Output tensors after passing through the model.
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)
        x = self.maxpool(x)
        x = self.layer1(x)
        feature_map = self.layer2(x)
        feature_map = self.layer3(feature_map)
        feature_map = self.layer4(feature_map)
        return x, feature_map


def resnetCAM(pretrained=False, **kwargs) -> ResNetCAM:
    """Constructs a ResNet-18 model with CAM capabilities.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNetCAM(BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls["resnet18"]), strict=False)
    return model


def resnet18(pretrained=False, **kwargs) -> ResNet:
    """Constructs a ResNet-18 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [2, 2, 2, 2], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls["resnet18"]), strict=False)
    return model


def resnet34(pretrained=False, **kwargs) -> ResNet:
    """Constructs a ResNet-34 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(BasicBlock, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls["resnet34"]), strict=False)
    return model


def resnet50(pretrained=False, **kwargs) -> ResNet:
    """Constructs a ResNet-50 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 6, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls["resnet50"]), strict=False)
    return model


def resnet101(pretrained=False, **kwargs) -> ResNet:
    """Constructs a ResNet-101 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 4, 23, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls["resnet101"]))
    return model


def resnet152(pretrained=False, **kwargs) -> ResNet:
    """Constructs a ResNet-152 model.
    Args:
        pretrained (bool): If True, returns a model pre-trained on ImageNet
    """
    model = ResNet(Bottleneck, [3, 8, 36, 3], **kwargs)
    if pretrained:
        model.load_state_dict(model_zoo.load_url(model_urls["resnet152"]))
    return model
