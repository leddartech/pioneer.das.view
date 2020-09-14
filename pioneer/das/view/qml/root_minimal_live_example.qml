
import MPLBackend 1.0
import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI3D 1.0
import Leddar 1.0

import Das 1.0
import Misc 1.0 //contains Utils.js

ApplicationWindow {
    id: component

    //////////////// Python API ////////////////////////////
    property string key: ''
    property alias cloud: actor_.cloud
    
    Viewport {
        id: viewport_
        anchors.fill: parent
        
        Keys.onPressed: component.key = event.text // python support for wait_key()
        
        function resetCamera() {
            var up  = Qt.vector3d(0,-1,0)
            var eye = Qt.vector3d(0,0,-10)
            var tf_Ref_from_Local = Qt.matrix4x4()
            camera.center = tf_Ref_from_Local.times(Qt.vector3d(0,0,0))
            camera.up     = tf_Ref_from_Local.times(up.toVector4d()).toVector3d()
            camera.eye    = tf_Ref_from_Local.times(eye)
        }
        Component.onCompleted: resetCamera()

        actors: Actors {
            GridXZ{}
            LidarActor {
                id: actor_
                colorMap: 'viridis'
                method: 'quad_cloud'
                logScale: false
            }
        }
    }
}