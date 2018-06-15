import PySpin
import cv2


# TODO - This class may not be useful. Consider simply rolling into Camera.
class Spinnaker(object):
    def __init__(self):
        # Retrieve singleton reference to system object
        self.system = PySpin.System.GetInstance()
        # Retrieve list of cameras from the system
        self.cam_list = self.system.GetCameras()
        self.num_cameras = self.cam_list.GetSize()

    def __del__(self):
        self.cam_list.Clear()
        self.system.ReleaseInstance()

    def getCamera(self, id=0):
        if id + 1 > self.num_cameras:
            raise RuntimeError("No camera at index", id, "detected.")

        return Camera(self.cam_list[id])


class Camera(object):
    """
    Wraps a PointGrey camera using the Spinnaker SDK and yields results
    that can be used with OpenCV.
    """

    def __init__(self, cam):
        self.cam = cam
        self.nodemap_tldevice = self.cam.GetTLDeviceNodeMap()
        self.nodemap_tlstream = self.cam.GetTLStreamNodeMap()
        self.cam.Init()
        self.nodemap = self.cam.GetNodeMap()

        # In order to access the node entries, they have to be casted to a pointer type (CEnumerationPtr here)
        node_acquisition_mode = PySpin.CEnumerationPtr(self.nodemap.GetNode('AcquisitionMode'))
        if not PySpin.IsAvailable(node_acquisition_mode) or not PySpin.IsWritable(node_acquisition_mode):
            print('Unable to set acquisition mode to continuous (enum retrieval). Aborting...')
            return False
        # Retrieve entry node from enumeration node
        node_acquisition_mode_continuous = node_acquisition_mode.GetEntryByName('Continuous')
        if not PySpin.IsAvailable(node_acquisition_mode_continuous) or not PySpin.IsReadable(node_acquisition_mode_continuous):
            print('Unable to set acquisition mode to continuous (entry retrieval). Aborting...')
            return False
        # Retrieve integer value from entry node
        acquisition_mode_continuous = node_acquisition_mode_continuous.GetValue()
        # Set integer value from entry node as new value of enumeration node
        node_acquisition_mode.SetIntValue(acquisition_mode_continuous)

        # Set stream buffer to return latest image
        node_stream_buffer_handling_mode = PySpin.CEnumerationPtr(self.nodemap_tlstream.GetNode('StreamBufferHandlingMode'))
        if not PySpin.IsAvailable(node_stream_buffer_handling_mode) or not PySpin.IsWritable(node_stream_buffer_handling_mode):
            print('Unable to set buffer handling mode to newest (enum retrieval). Aborting...')
            return False
        node_stream_buffer_handling_mode_newest = node_stream_buffer_handling_mode.GetEntryByName('NewestFirstOverwrite')
        if not PySpin.IsAvailable(node_stream_buffer_handling_mode_newest) or not PySpin.IsReadable(node_stream_buffer_handling_mode_newest):
            print('Unable to set buffer handling mode to newest (enum retrieval). Aborting...')
            return False
        stream_buffer_handling_mode_newest = node_stream_buffer_handling_mode_newest.GetValue()
        node_stream_buffer_handling_mode.SetIntValue(stream_buffer_handling_mode_newest)

        self.cam.BeginAcquisition()

    def __del__(self):
        self.cam.EndAcquisition()
        self.cam.DeInit()
        del self.cam

    def printDeviceInfo(self):
        """
        (Taken from Acquisition.py)

        This function prints the device information of the camera from the transport
        layer; please see NodeMapInfo example for more in-depth comments on printing
        device information from the nodemap.

        :returns: True if successful, False otherwise.
        :rtype: bool
        """

        print('*** DEVICE INFORMATION ***\n')

        try:
            result = True
            node_device_information = PySpin.CCategoryPtr(self.nodemap_tldevice.GetNode('DeviceInformation'))

            if PySpin.IsAvailable(node_device_information) and PySpin.IsReadable(node_device_information):
                features = node_device_information.GetFeatures()
                for feature in features:
                    node_feature = PySpin.CValuePtr(feature)
                    print('%s: %s' % (node_feature.GetName(),
                                      node_feature.ToString() if PySpin.IsReadable(node_feature) else 'Node not readable'))

            else:
                print('Device control information not available.')

        except PySpin.SpinnakerException as ex:
            print('Error: %s' % ex)
            return False

        return result

    def read(self, grayscale=True):
        """
        Return one image from the camera.
        """

        image_result = self.cam.GetNextImage()

        if image_result.IsIncomplete():
            raise RuntimeError('Image incomplete with image status %d ...' % image_result.GetImageStatus())

        # print('PixelFormat:', image_result.GetPixelFormatName())
        pixel_format = image_result.GetPixelFormat()
        if grayscale and pixel_format != PySpin.PixelFormat_BGR8:
            return image_result.Convert(PySpin.PixelFormat_BGR8).GetNDArray()
        else:
            return image_result.GetNDArray()


def main():
    controller = Spinnaker()
    cam = controller.getCamera()
    cam.printDeviceInfo()

    while cv2.waitKey(1) != ord(' '):
        img = cam.read()
        cv2.imshow('img', img)

    cv2.destroyWindow('img')
    del cam


if __name__ == '__main__':
    main()
