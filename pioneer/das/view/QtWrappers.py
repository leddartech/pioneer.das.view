from pioneer.common import clouds, linalg
from pioneer.common.gui import Array, Product, Transforms, Geometry, Image
from pioneer.das.api import categories, platform, sensors
try:
    from pioneer.das.calibration import intrinsics
except: pass

from datetime import datetime
from matplotlib import colors
from PyQt5.QtCore import pyqtSlot as Slot, pyqtSignal as Signal, pyqtProperty as Property, Q_ENUMS, QVariant, QObject, QSize
from PyQt5.QtGui import QQuaternion, QVector2D, QVector3D, QMatrix4x4

import cv2
import numpy as np
import time

'''
This file contains a set of tools for future use.  They where used in the first version of the QML-based das viewer.
'''

class Platform(Product.Product):
    def __init__(self, parent = None, path = ''):
        super(Platform, self).__init__(parent)
        self._path = path
        self._platform = None


    Product.InputProperty(vars(), str, 'path')

    sensorNamesChanged = Signal()
    @Property(QVariant, notify = sensorNamesChanged)
    def sensorNames(self):
        if self._platform is None:
            return QVariant([])
        return QVariant(list(self._platform.sensors.keys()))

    datasourcesNamesChanged = Signal()
    @Property(QVariant, notify = datasourcesNamesChanged)
    def datasourcesNames(self):
        if self._platform is None:
            return QVariant([])
        return QVariant(self._platform.datasource_names())


    orientationChanged = Signal()
    @Property(QVariant, notify = orientationChanged)
    def orientation(self):
        if self._platform is None:
            return QVariant([])
        return QVariant(self._platform.orientation)


    @Slot(list, result = list)
    def expandWildcards(self, labels):
        if self._platform is not None:
            return self._platform.expand_wildcards(labels)

    def _update(self):
        if self._platform is None:
            self._platform = platform.Platform(dataset=self._path)

        self.orientationChanged.emit()
        self.sensorNamesChanged.emit()
        self.datasourcesNamesChanged.emit()

    def __getitem__(self, key):
        return self._platform[key]

class Synchronized(Product.Product):
    def __init__(self, parent = None, platform = None, params = {'sync_labels' : ['*'], 'interp_labels' : [], 'tolerance_us' : -1e3}):
        super(Synchronized, self).__init__(parent)
        self._platform = platform
        self._parameters = params
        self._nIndices = 0
        self._synchronized = None


    def cb_parameters(self):
        self._dataset = None

    Product.InputProperty(vars(), QVariant, 'parameters', cb_parameters)

    def cb_platform(self):
        self._synchronized = None

    Product.InputProperty(vars(), Platform, 'platform', cb_platform)
    

    sensorNamesChanged = Signal()
    @Property(QVariant, notify = sensorNamesChanged)
    def sensorNames(self):
        if self._synchronized is None:
            return QVariant([])

        names = set()
        for k in self._synchronized.keys():
            sensor_type, position, _ = platform.parse_datasource_name(k)
            names.add('{}_{}'.format(sensor_type, position))

        return QVariant(list(names))

    @Slot(list, result = list)
    def expandWildcards(self, labels):
        if self._synchronized is not None:
            return self._synchronized.expand_wildcards(labels)

    datasourcesChanged = Signal()
    @Property(QVariant, notify = datasourcesChanged)
    def datasources(self):
        if self._synchronized is None:
            return QVariant([])
        return QVariant(self._synchronized.keys())

    nIndicesChanged = Signal()
    @Property(int, notify = nIndicesChanged)
    def nIndices(self):
        return self._nIndices

    def __getitem__(self, key):
        return self._synchronized[key]

    def _update(self):
        if self._platform is not None:
            self._synchronized = self._platform._platform.synchronized(**self._parameters)
            self._nIndices = len(self._synchronized)

        self.nIndicesChanged.emit()
        self.datasourcesChanged.emit()
        self.sensorNamesChanged.emit()

class Selector(Product.VariantProduct):
    def __init__(self, parent = None):
        super(Selector, self).__init__(parent)
        self._index = 0
        self._data = 0
        self._label = ""
        self._referential = None
        self._sample = None
        self._transform = Transforms.MatrixTransform(self)
        self._transform.set_producer(self)


    def cb_data(self):
        if not isinstance(self._data, (Platform, Synchronized)):
            raise RuntimeError('You can assign a Platform or a Synchronized')

    Product.InputProperty(vars(), Product.Product, 'parameters', cb_data)

    Product.InputProperty(vars(), str, 'label')

    Product.InputProperty(vars(), int, 'index')

    Product.InputProperty(vars(), str, 'referential')

    Product.ConstProperty(vars(), Transforms.MatrixTransform, 'transform')


    prettyPrintedChanged = Signal()
    @Property(QVariant, notify = prettyPrintedChanged)
    def prettyPrinted(self):
        if self._sample is not None:
            return self._sample.pretty_print()
        return ""

    def _update(self):
        if isinstance(self._data, Synchronized):
            self._sample = self._data[self._index][self._label]
        elif isinstance(self._data, Platform):
            self._sample = self._data[self._label][self._index]

        if self._sample is not None:
            self._variant = self._sample.raw
            t = self._sample.compute_transform(self._referential)
            if t is None:
                self._transform.matrix = QMatrix4x4()
            else:
                self._transform.matrix = QMatrix4x4(t.flatten().tolist())

            self.prettyPrintedChanged.emit()


class ExtractImage(Array.Array):
    def __init__(self, parent = None):
        super(ExtractImage, self).__init__(parent)
        self._packages = None
        self.productClean.connect(self.sizeChanged)


    Product.InputProperty(vars(), Product.VariantProduct, 'packages')

    sizeChanged = Signal()
    @Property(QSize, notify = sizeChanged)
    def size(self):
        return QSize(self.ndarray.width, self.ndarray.height)

    def _update(self):
        if self._packages is not None and self._packages._variant is not None:
            self.ndarray = self._packages._variant.copy()



class DasSampleToCloud(Array.ArrayDouble3):
    def __init__(self, parent = None):
        super(DasSampleToCloud, self).__init__(parent)
        self._sample = None
        self._seg3DSample = None
        self._referential = None
        self._undistort = False
        self._undistortRefTs = -1
        self._primitiveType = Geometry.PrimitiveType.POINTS
        
        self._indices = Array.ArrayUInt1()
        self._indices.set_producer(self)
        self._amplitudes = Array.ArrayFloat1()
        self._amplitudes.set_producer(self)

        self._colors = Array.ArrayFloat4()
        self._colors.set_producer(self)

        self._transform = Transforms.Transform()
        self._transform.set_producer(self)

        self._minAmplitude = np.nan
        self._maxAmplitude = np.nan
        self._hasReferential = True
        self._logScale = False

        self._method = None

        self._amplitudeRatio = 100

        #call setters:
        self.method = 'point_cloud'
        self.sample = Product.VariantProduct()
        self.seg3DSample = Product.VariantProduct()

# inputs:

    Product.InputProperty(vars(), Product.VariantProduct, 'sample')

    Product.InputProperty(vars(), Product.VariantProduct, 'seg3DSample')

    Product.InputProperty(vars(), str, 'referential')

    Product.InputProperty(vars(), bool, 'undistort')

    Product.InputProperty(vars(), int, 'undistortRefTs')



    def cb_method(self):
        if self._method not in ['point_cloud', 'quad_cloud']:
            raise RuntimeError(f"Unexpected method: {self._method}")

        self.set_primitiveType(self, Geometry.PrimitiveType.POINTS if self._method == 'point_cloud' else Geometry.PrimitiveType.TRIANGLES)
    
    Product.InputProperty(vars(), str, 'method', cb_method)

    Product.InputProperty(vars(), float, 'minAmplitude')

    Product.InputProperty(vars(), float, 'maxAmplitude')

    Product.InputProperty(vars(), float, 'amplitudeRatio')

    Product.InputProperty(vars(), str, 'amplitudeType')

    Product.InputProperty(vars(), bool, 'logScale')

#outputs:

    Product.ConstProperty(vars(), Array.ArrayUInt1, 'indices')

    Product.ConstProperty(vars(), Array.ArrayFloat1, 'amplitudes')

    Product.ConstProperty(vars(), Array.ArrayFloat4, 'colors')

    Product.ConstProperty(vars(), Transforms.Transform, 'transform')

    Product.ROProperty(vars(), bool, 'hasReferential')

    Product.ROProperty(vars(), int, 'primitiveType')

#slots:
    @Slot(int, result = int)
    def channel(self, n):
        if self._primitiveType == Geometry.PrimitiveType.TRIANGLES:
            triangle = self._triangle_at(n)
            data  = self.filter_banks()
            return data['indices'][clouds.triangle_to_echo_index(triangle)]
        elif self._primitiveType == Geometry.PrimitiveType.POINTS:
            return self.indices.ndarray[n]
        else:
            raise RuntimeError(f"Unsupported primitiveType {self._primitiveType}")

    @Slot(int, result = QVariant)
    def channelInfo(self, n):
        triangle = self._triangle_at(n)
        echo_i = clouds.triangle_to_echo_index(triangle)
        sample = self._get_sample().masked
        data = sample['data']
        channel_i = data['indices'][echo_i]

        h = sample['h']
        try:
            coeff = sample['timestamps_to_us_coeff']
        except:
            coeff = 1
        rv = {'v': int(channel_i//h), 'h': int(channel_i%h), 'i' : int(channel_i)
            , 'distance': float(data['distances'][echo_i])
            , 'amplitude': float(data['amplitudes'][echo_i])
            , 'timestamp': int(data['timestamps'][echo_i] * coeff)
            , 'flag': int(data['flags'][echo_i])
            , 'category': ''}

        if self._seg3DSample._variant is not None:
            seg_source = categories.get_source(self._seg3DSample._variant.datasource.ds_type)
            category_number = self._seg3DSample._variant.raw['data'][int(echo_i)]['classes']
            category_name, _ = categories.get_name_color(seg_source, category_number)
            rv['category'] = category_name

        return QVariant(rv)

# private:

    def _triangle_at(self, n):
        return self._indices.ndarray[n * 3 : n * 3 + 3]

    def _normalize_amplitudes(self):

        min_ = self._minAmplitude if not np.isnan(self._minAmplitude) or self._amplitudes.ndarray.size == 0 else self._amplitudes.ndarray.min()
        max_ = self._maxAmplitude if not np.isnan(self._maxAmplitude) or self._amplitudes.ndarray.size == 0 else self._amplitudes.ndarray.max()

        
        if self._logScale:
            norm = colors.LogNorm(1 + min_, 1 + min_ + max_)
        else:
            norm = colors.Normalize(min_, max_)

        self._amplitudes.ndarray = norm(self._amplitudes.ndarray + ((1 + min_) if self._logScale else 0))

    def _get_sample(self):
        if self._sample is None or self._sample._variant is None:
            raise RuntimeError("No sample found!")
        return self._sample._variant

    def _update(self):

        sample = self._get_sample()

        f = getattr(sample, self._method) #point_cloud() or quad_cloud()
        tf_Ref_from_Local = linalg.tf_eye(np.float64)

        try:
            rv = f(referential=self._referential, ignore_orientation=False, undistort=self._undistort, reference_ts=self._undistortRefTs, 
                        dtype=np.float64)
            self.set_hasReferential(self, True)
            tf_Ref_from_Local = sample.compute_transform(self._referential, ignore_orientation = True, dtype = np.float64)
        except sensors.Sensor.NoPathToReferential as e:
            rv = f(referential=None, undistort=self._undistort, dtype = np.float64)
            self.set_hasReferential(self, False)

        self._transform.set_local_transform(QMatrix4x4(tf_Ref_from_Local.astype(np.float32).flatten().tolist()))
        
        if self._method == "quad_cloud":
            v,a,i = rv
            self.set_ndarray(v)
            self._amplitudes.set_ndarray(a)
            self._indices.set_ndarray(i)
            self._normalize_amplitudes()
            
        elif self._method == "point_cloud":
            amp = sample.amplitudes
            nb_points = np.max([1, int(amp.shape[0] * self._amplitudeRatio / 100.0)])
            self.set_ndarray(rv[-nb_points:])
            self._amplitudes.set_ndarray(amp[-nb_points:])
            self._indices.set_ndarray(np.arange(rv[-nb_points:].shape[0], dtype = np.uint32))
            if self._logScale and np.min(self._amplitudes.ndarray)< 0 :
                self._amplitudes.set_ndarray(self._amplitudes.ndarray - np.min(self._amplitudes.ndarray))
            self._normalize_amplitudes()

        if self._seg3DSample._variant is not None:
            self._colors.set_ndarray(self._seg3DSample._variant.colors(self._method))


class ROSCalibratorFilter(Image.ImageFilter):
    def __init__(self, parent = None):
        super(ROSCalibratorFilter, self).__init__(parent)

        self._patternSpecs = {'nx': 13, 'ny': 10, 'size' : 0.145}
        self._camSpecs = {'h': 1440, 'v' : 1080, 'f' : 3.1e-3, 'pixel_size' : 3.45e-6}

        self._xCoverage = 0
        self._yCoverage = 0
        self._sizeCoverage = 0
        self._skewCoverage = 0
        self._nImages = 0
        self._matrix = ''
        self._distortion = ''
        self._calibrated = False

        self._name = "camera_name"
        self._intrinsics_hints = None
        self._calibration = None

        self._init()

    def _init(self):
        self._images = []
        self._params = []
        self._intrinsics_hints = None
        self._calibration = None
        self._intrinsics_hints = np.eye(3, dtype=np.float64)
        self._intrinsics_hints[0,0] = self._intrinsics_hints[1,1] = self._camSpecs['f'] / self._camSpecs['pixel_size']
        self._intrinsics_hints[0,2] = self._camSpecs['h']/2
        self._intrinsics_hints[1,2] = self._camSpecs['v']/2

    #inputs:
    Product.InputProperty(vars(), str, 'name')
    Product.InputProperty(vars(), QVariant, 'patternSpecs')
    Product.InputProperty(vars(), QVariant, 'camSpecs')

    #outputs:
    Product.ROProperty(vars(), int, 'nImages')
    Product.ROProperty(vars(), float, 'sizeCoverage')
    Product.ROProperty(vars(), float, 'skewCoverage')
    Product.ROProperty(vars(), float, 'xCoverage')
    Product.ROProperty(vars(), float, 'yCoverage')
    Product.ROProperty(vars(), float, 'skewCoverage')
    Product.ROProperty(vars(), bool, 'calibrated')
    Product.ROProperty(vars(), str, 'matrix')
    Product.ROProperty(vars(), str, 'distortion')

    def _pattern(self):
        return (self._patternSpecs['nx'], self._patternSpecs['ny'])

    def _image_size(self):
        if self._images:
            return tuple(reversed(self._images[0].shape[:2]))
        else:
            return (self._camSpecs['h'], self._camSpecs['v'])

    @Slot()
    def calibrate(self):
        if self._images:
            proc = intrinsics.ChessboardFinderProc(4)
            corners_list = proc(self._images, self._pattern())
            self._calibration  = intrinsics.calibrate_camera(corners_list
            , intrinsics.make_object_points(self._pattern(), self._patternSpecs['size'])
            , self._image_size())
            self._update_outputs(None)

    @Slot(str, str, str)
    def save(self, name, pos, path):
        intrinsics.save_as_datasource(self._images, path, name, pos, self._calibration, self._camSpecs, self._patternSpecs)

    @Slot(str)
    def load(self, path):
        self._init()
        with tarfile.open(path) as tar:
            for filename in tar.getmembers():
                if filename.name[-4:] == ".png" :
                    byte_arr = bytearray(tar.extractfile(filename).read())
                    arr = np.asarray(byte_arr, dtype=np.uint8)
                    self._handle_new_image(cv2.imdecode(arr, cv2.IMREAD_GRAYSCALE))


    def _update_outputs(self, params):
        if params is not None:
            x, y, size, skew = ([float(p[3]) for p in params])
            self.set_yCoverage   (self, y                 )
            self.set_xCoverage   (self, x                 )
            self.set_sizeCoverage(self, size              )
            self.set_skewCoverage(self, skew              )
            self.set_nImages     (self, len(self._images) )

        if self._calibration is not None:
            self.set_calibrated(self, True)
            for label in ['matrix', 'distortion']:
                getattr(self, f'set_{label}')(self, str(self._calibration[label]))


    def _handle_new_image(self, gray, try_add_to_db = True):

        scrib_mono, corners, downsampled_corners, _ = intrinsics.downsample_and_detect(gray, self._pattern())
        scrib = cv2.cvtColor(scrib_mono, cv2.COLOR_GRAY2BGR)
        if corners is not None:
            # Draw (potentially downsampled) corners onto display image
            cv2.drawChessboardCorners(scrib, self._pattern(), downsampled_corners, True)

            if try_add_to_db:
                # Add sample to database only if it's sufficiently different from any previous sample.
                params = intrinsics.get_parameters(corners, self._pattern(), reversed(gray.shape[:2]))
                if intrinsics.is_good_sample(params, self._params):
                    self._images.append(gray)
                    self._params.append(params)
                    self._update_outputs(intrinsics.compute_progress(self._params))

                return scrib # only return scrip if sample was added
            else:
                return scrib

        return gray

    def _update(self):

        if self._imageArray is not None and self._imageArray.ndarray.size > 0:
            image = self._imageArray.ndarray

            now = datetime.utcnow()
            now = time.mktime(now.timetuple()) + float(now.microsecond)/1e6

            delta_t = time.time() - self._imageArray.timestamp
            #if delta_t < 0.5:
            self.ndarray = self._handle_new_image(cv2.cvtColor(image, cv2.COLOR_RGB2GRAY))
            
            
            #else:
            #    self.ndarray = image
            #    print(f'image too late {delta_t}')


class ROSStereoCalibratorFilter(ROSCalibratorFilter):
    def __init__(self, parent=None):
        super(ROSStereoCalibratorFilter, self).__init__(parent=parent)
        self._imageArrayRight = None
        self._images_right = []
        self._leftCalibPath = ""
        self._rightCalibPath = ""
        self._rightImageResult = Array.Array()
        self._rightImageResult.set_producer(self)

    
    Product.InputProperty(vars(), Array.Array, "imageArrayRight")
    
    Product.InputProperty(vars(), str, "leftCalibPath")
    Product.InputProperty(vars(), str, "rightCalibPath")

    Product.ConstProperty(vars(), Array.Array, 'rightImageResult') #leftImageResult is self

    @Slot()
    def calibrate(self):
        if self._images:
            proc = intrinsics.ChessboardFinderProc(4)
            corners_list_left = proc(self._images, self._pattern())

            proc = intrinsics.ChessboardFinderProc(4)
            corners_list_right = proc(self._images_right, self._pattern())

            with open(self._leftCalibPath, 'rb') as f:
                left_calib = pickle.load(f)

            with open(self._rightCalibPath, 'rb') as f:
                right_calib = pickle.load(f)            
            
            self._calibration  = intrinsics.calibrate_camera_stereo(corners_list_left, corners_list_right
            , intrinsics.make_object_points(self._pattern(), self._patternSpecs['size'])
            , self._image_size()
            , left_calib['matrix'], left_calib['distortion']
            , right_calib['matrix'], right_calib['distortion'])

            self._update_outputs(None)

    def _update(self):
        if self._left is None or self._imageArray is None:
            return
        
        if self._left._imageArray.ndarray.size > 0 and self._imageArray.ndarray.size > 0:

            self.ndarray = self._imageArray.ndarray
            self._rightImageResult.ndarray = self._imageArray.ndarray

            if abs(self._imageArray.timestamp - self._left._imageArray.timestamp) < 1e-4: #100us appart

                left = self._imageArray.ndarray
                right = self._imageArrayRight.ndarray
                gray_left = cv2.cvtColor(left, cv2.COLOR_RGB2GRAY)
                gray_right = cv2.cvtColor(right, cv2.COLOR_RGB2GRAY)

                rv_right = self._handle_new_image(gray_right)
                if rv_right != gray_right:
                    #chessboard found in right image, let's look in left image:
                    self._rightImageResult.ndarray = rv_right
                    rv_left = self._handle_new_image(gray_left)
                    if rv_left != gray_left:
                        #left image was added to the database, let's add right image too
                        self.ndarray = rv_left
                        self._images_right.append(right)




        return super()._update()

class Undistort(Image.ImageFilter):
    def __init__(self, parent = None):
        super(Undistort, self).__init__(parent)
        self._path = None
        self._yaml = None
        self._map = None
        self._roi = []
        self._shape = []



    def path_cb(self):
        with tarfile.open(self._path) as tar:
            try:
                calib = pickle.loads(tar.extractfile(tar.getmember('calib.pkl')).read())
                cam_specs = pickle.loads(tar.extractfile(tar.getmember('cam_specs.pkl')).read())

                w = cam_specs['h']
                h = cam_specs['v']
                self._shape = (h, w)
                mtx = calib['matrix']
                dist = calib['distortion']
                newcameramtx, self._roi=cv2.getOptimalNewCameraMatrix(mtx,dist,(w,h),1,(w,h))
                self._map = cv2.initUndistortRectifyMap(mtx,dist,None,newcameramtx,(w,h),5)
            except:
                print(traceback.format_exc())

    Product.InputProperty(vars(), str, 'path', path_cb)

    def _update(self):
        if self._imageArray is not None and self._map is not None:
            image = self._imageArray.ndarray
            if self._shape == image.shape[:2]:

                dst = cv2.remap(image,self._map[0],self._map[1],cv2.INTER_LINEAR)
                # crop the image
                x,y,w,h = self._roi
                self.ndarray = np.copy(dst[y:y+h, x:x+w])