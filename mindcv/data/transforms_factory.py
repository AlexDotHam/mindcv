import math

import mindspore.dataset.vision as vision
from mindspore.dataset.vision import Inter
import mindspore.dataset.vision.transforms as transforms

from .constants import DEFAULT_CROP_PCT, IMAGENET_DEFAULT_MEAN, IMAGENET_DEFAULT_STD
from .auto_augment import imagenet_policy


def transforms_imagenet_train(
        image_resize=224,
        scale=(0.08, 1.0),
        ratio=(0.75, 1.333),
        hflip=0.5,
        vflip=0.0,
        color_jitter=None,
        auto_augment=False,
        interpolation='bilinear',
        mean=IMAGENET_DEFAULT_MEAN,
        std=IMAGENET_DEFAULT_STD,
        re_prob=0.,
        re_scale=(0.02, 0.33),
        re_ratio=(0.3, 3.3),
        re_value=0,
        re_max_attempts=10
):
    """Transform operation list when training on ImageNet."""
    # Define map operations for training dataset
    if hasattr(Inter, interpolation.upper()):
        interpolation = getattr(Inter, interpolation.upper())
    else:
        interpolation = Inter.BILINEAR

    trans_list = [vision.RandomCropDecodeResize(size=image_resize,
                                                scale=scale,
                                                ratio=ratio,
                                                interpolation=interpolation
                                                )]
    if hflip > 0.:
        trans_list += [vision.RandomHorizontalFlip(prob=hflip)]
    if vflip > 0.:
        trans_list += [vision.RandomVerticalFlip(prob=vflip)]

    if auto_augment:
        trans_list += [vision.RandomSelectSubpolicy(imagenet_policy)]
    elif color_jitter is not None:
        if isinstance(color_jitter, (list, tuple)):
            # color jitter shoulf be a 3-tuple/list for brightness/contrast/saturation
            # or 4 if also augmenting hue
            assert len(color_jitter) in (3, 4)
        else:
            color_jitter = (float(color_jitter),) * 3
        trans_list += [vision.RandomColorAdjust(*color_jitter)]

    trans_list += [
        vision.Normalize(mean=mean, std=std),
        vision.HWC2CHW()
    ]
    if re_prob > 0.:
        trans_list.append(
            vision.RandomErasing(prob=re_prob,
                                 scale=re_scale,
                                 ratio=re_ratio,
                                 value=re_value,
                                 max_attempts=re_max_attempts)
        )

    return trans_list


def transforms_imagenet_eval(
        image_resize=224,
        crop_pct=DEFAULT_CROP_PCT,
        mean=IMAGENET_DEFAULT_MEAN,
        std=IMAGENET_DEFAULT_STD,
        interpolation='bilinear',

):
    """Transform operation list when evaluating on ImageNet."""
    if isinstance(image_resize, (tuple, list)):
        assert len(image_resize) == 2
        if image_resize[-1] == image_resize[-2]:
            scale_size = int(math.floor(image_resize[0] / crop_pct))
        else:
            scale_size = tuple([int(x / crop_pct) for x in image_resize])
    else:
        scale_size = int(math.floor(image_resize / crop_pct))

    # Define map operations for training dataset
    if hasattr(Inter, interpolation.upper()):
        interpolation = getattr(Inter, interpolation.upper())
    else:
        interpolation = Inter.BILINEAR
    trans_list = [
        vision.Decode(),
        vision.Resize(scale_size, interpolation=interpolation),
        vision.CenterCrop(image_resize),
        vision.Normalize(mean=mean, std=std),
        vision.HWC2CHW()

    ]

    return trans_list


def transforms_cifar(resize=224, is_training=True):
    """Transform operation list when training or evaluating on cifar."""
    trans = []
    if is_training:
        trans += [
            transforms.RandomCrop((32, 32), (4, 4, 4, 4)),
            transforms.RandomHorizontalFlip(prob=0.5)
        ]

    trans += [
        transforms.Resize(resize),
        transforms.Rescale(1.0 / 255.0, 0.0),
        transforms.Normalize([0.4914, 0.4822, 0.4465], [0.2023, 0.1994, 0.2010]),
        transforms.HWC2CHW()
    ]

    return trans


def transforms_mnist(resize=224):
    """Transform operation list when training or evaluating on mnist."""
    rescale = 1.0 / 255.0
    shift = 0.0
    rescale_nml = 1 / 0.3081
    shift_nml = -1 * 0.1307 / 0.3081

    trans = [
        transforms.Resize(size=resize, interpolation=Inter.LINEAR),
        transforms.Rescale(rescale, shift),
        transforms.Rescale(rescale_nml, shift_nml),
        transforms.HWC2CHW(),
    ]
    return trans


def create_transforms(
        dataset_name='',
        image_resize=224,
        is_training=False,
        **kwargs
):
    r"""Creates a list of transform operation on image data.

    Args:
        dataset_name (str): if '', customized dataset. Currently, apply the same transform pipeline as ImageNet.
            if standard dataset name is given including imagenet, cifar10, mnist, preset transforms will be returned.
            Default: ''.
        image_resize (int): the image size after resize for adapting to network. Default: 224.
        is_training (bool): if True, augmentation will be applied if support. Default: False.
        **kwargs: additional args parsed to `transforms_imagenet_train` and `transforms_imagenet_eval`

    Returns:
        A list of transformation operations
    """

    dataset_name = dataset_name.lower()

    if dataset_name == "imagenet" or dataset_name == '':
        trans_args = dict(image_resize=image_resize, **kwargs)
        if is_training:
            return transforms_imagenet_train(**trans_args)
        else:
            return transforms_imagenet_eval(**trans_args)
    elif dataset_name == 'cifar10' or dataset_name == 'cifar100':
        trans_list = transforms_cifar(resize=image_resize,
                                      is_training=is_training)
        return trans_list
    elif dataset_name == 'mnist':
        trans_list = transforms_mnist(resize=image_resize)
        return trans_list
    else:
        raise NotImplementedError(f"Only supports creating transforms for ['imagenet'] datasets, "
                                  f"but got {dataset_name}.")
