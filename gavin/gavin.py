#! /usr/bin/env python3

from ctypes import POINTER, Structure, c_char, c_int, c_short, c_ubyte
from enum import Enum


class GUIDE_USB_CODE_E(Enum):
    """ Function Return Value. """

    ERROR_NO               = 1                  # no error
    ERROR_DEVICE_NOT_FOUND = -1                 # cant find device
    ERROR_POINT_NULL       = -2                 # null point
    ERROR_POINTS_TOO_LARGE = -3                 # point too large
    ERROR_POINTS_TOO_SMALL = -4                 # point too small
    ERROR_MALLOC_FAILED    = -5                 # alloc memory failure
    ERROR_RESOLUTION       = -6                 # set resolution error
    ERROR_UNKNOW           = -999               # unknow error


class GUIDE_USB_VIDEO_MODE_E(Enum):
    """ Device Video Mode. """

    X16           = 0                           # X16
    X16_PARAM     = 1                           # X16+paraline
    Y16           = 2                           # Y16
    Y16_PARAM     = 3                           # Y16+paraline
    YUV           = 4                           # YUV
    YUV_PARAM     = 5                           # YUV+paraline
    Y16_YUV       = 6                           # Y16+YUV
    Y16_PARAM_YUV = 7                           # Y16+paraline+YUV


class GUIDE_USB_DEVICE_STATUS_E(Enum):
    """ Device Connect Mode. """

    DEVICE_CONNECT_OK    = 1                    # connect ok
    DEVICE_DISCONNECT_OK = -1                   # disconnect


class GUIDE_USB_DEVICE_INFO_T(Structure):
    """ Device Video Info. """

    _fields_ = [
        ("width", c_int),                       # video width
        ("height", c_int),                      # video height
        ("video_mode", c_int),                  # video mode (GUIDE_USB_VIDEO_MODE_E)
    ]


class GUIDE_USB_FRAME_DATA_T(Structure):
    """ Image Frame Info. """

    _fields_ = [
        ("frame_width", c_int),                 # frame width
        ("frame_height", c_int),                # frame height
        ("frame_rgb_data", POINTER(c_ubyte)),   # rgb data stream
        ("frame_rgb_data_length", c_int),       # rgb data length
        ("frame_src_data", POINTER(c_short)),   # X16/Y16 data stream
        ("frame_src_data_length", c_int),       # X16/Y16 data length
        ("frame_yuv_data", POINTER(c_short)),   # yuv data stream
        ("frame_yuv_data_length", c_int),       # yuv data length
        ("paraLine", POINTER(c_short)),         # paraline
        ("paraLine_length", c_int),             # paraline length
    ]


class DEVICE_INFO(Structure):
    """ Device Info. """

    _fields_ = [
        ("devID", c_int),                       # device ID
        ("devName", c_char * 128),              # device name
    ]


class DEVICE_INFO_LIST(Structure):
    """ Device List Info. """

    _fields_ = [
        ("devCount", c_int),                    # device count
        ("devs", DEVICE_INFO * 32),
    ]
