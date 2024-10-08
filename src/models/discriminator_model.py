import torch
import torch.nn as nn
from src.utils import print_info
import config as c
import numpy as np

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


class CNNBlock(nn.Module):
    def __init__(self, in_channels, out_channels, stride):
        super(CNNBlock, self).__init__()

        self.conv = nn.Sequential(
            nn.Conv2d(
                in_channels, out_channels, 4, stride, 1, bias=False, padding_mode="reflect"
            ),
            nn.BatchNorm2d(out_channels),
            nn.LeakyReLU(0.2),
        )

    def forward(self, x):
        return self.conv(x)


class Discriminator(nn.Module):
    def __init__(self, in_channels_x=1, in_channels_y=3, features=[64, 128, 256, 512, 1024]):
        super().__init__()

        # because of flattening
        in_channels_y = 1
        # faster this way:
        self.sqrt = int(np.sqrt(c.NEAR_SQUARE))

        # conv to first feature amount
        self.initial = nn.Sequential(
            nn.Conv2d(
                in_channels_x + in_channels_y,
                features[0],
                kernel_size=4,
                stride=2,
                padding=1,
                padding_mode="reflect",
            ),
            nn.LeakyReLU(0.2),
        )

        # more and more features
        layers = []
        in_channels = features[0]
        for feature in features[1:]:
            layers.append(
                CNNBlock(in_channels, feature, stride=1 if feature == features[-1] else 2).to(device),
            )
            in_channels = feature

        # conv to just one feature, the probability of realness
        layers.append(
            nn.Conv2d(
                in_channels, 1, kernel_size=4, stride=1, padding=1, padding_mode="reflect"
            ).to(device),
        )

        self.model = layers

    def forward(self, x, y):
        # Reshuffling the CB images into artificial spatial diffractive pattern
        diff = c.NEAR_SQUARE - c.SHAPE_Y[0]
        y = nn.functional.pad(y, (0,0,0,0,0,diff), mode='replicate', value=0) # 121x42x42 (mode=replicate or constant)
        y = nn.functional.pixel_shuffle(y, self.sqrt) # 1x462x462
        if y.shape[-1] < x.shape[-1]: # interpolate smaller tensor to bigger tensor
            y = nn.functional.interpolate(y, x.shape[2:], mode='nearest') # 1x900x900
        else:
            x = nn.functional.interpolate(x, y.shape[2:], mode='nearest') # 1x900x900
        x = torch.cat([x, y], dim=1) # 2x900x900
        x = self.initial(x) # 64x450x450
        x0 = []
        for layer in self.model:
            # 128x225x255
            # 256x112x112
            # 512x56x56
            # 1024x55x55
            # 1x54x54 at the end
            x0.append(x)
            x = layer(x) 
        x0.append(x)
        return x, x0 # outputs end tensor and all the previous tensors in an array

def test():
    x = torch.randn((1, 1, 900, 900))
    y = torch.randn((1, 106, 104, 104))
    c.SHAPE_Y = (106,104,104)
    c.NEAR_SQUARE = 121
    model = Discriminator(in_channels_x=1, in_channels_y=106)
    preds = model(x, y)
    #print("\nModel:\n", model)
    for p in preds:
        try:
            print("\nShape of prediction:", p.shape)
            print_info(p, "Preds")
        except:
            for p0 in p:
                print("\nP0: Shape of prediction:", p0.shape)
                print_info(p0, "Preds")


if __name__ == "__main__":
    test()
