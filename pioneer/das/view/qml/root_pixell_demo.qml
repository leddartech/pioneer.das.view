
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
    property alias amplitudeUp: amplitudeUp_
    property alias amplitudeDown: amplitudeDown_
    property alias settings: settings_
    width: 800
    height: 600

    ColumnLayout {
        anchors.fill: parent
        Viewport {
            id: viewport_
            Layout.fillWidth: true
            Layout.preferredHeight: component.height/2
            visible: showVP_.checked
            Keys.onPressed: component.key = event.text // python support for wait_key()
            
            function resetCamera() {
                var up  = Qt.vector3d(0,-1,0)
                var eye = Qt.vector3d(0,-5,-10)
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

        QImagePainter {
            visible: showRef_.checked
            Layout.fillWidth: true
            Layout.fillHeight: true
            imageArray: ArrayUByte4{id:amplitudeUp_}
        } 
        QImagePainter {
            Layout.fillWidth: true
            Layout.fillHeight: true
            imageArray: ArrayUByte4{id:amplitudeDown_}
        }
    }

    Window {
        id: settings_

        property alias bicubic: bicubic_.checked
        property alias deblur: deblur.checked
        property alias n: n_.value
        property alias ampMax: ampMax_.value
        property alias dynamicAmp: dynamicAmp_.checked

        width: 500
        height: 300
        visible: true

        ColumnLayout {
            anchors.fill: parent
            CheckBox {
                id: bicubic_
                text: "bicubic"
                checked: true
            }
            CheckBox {
                id: deblur
                text: "deblur"
                checked: true
            }
            RowLayout {
                Layout.fillWidth: true
                Text {text: "n"}
                SpinBox {
                    id: n_
                    value: 2
                    from: 0
                    to: 4
                }
            }
            RowLayout {
                Layout.fillWidth: true
                Text {text: "max amplitude"}
                Slider {
                    id: ampMax_
                    enabled: !dynamicAmp_.checked
                    value: 50000
                    from: 0
                    to: 75000
                }
                Text {text: ampMax_.value}
            }
            CheckBox {
                id: dynamicAmp_
                text: "dynamic max"
                checked: false
            }
            CheckBox {
                id: showRef_
                text: "show ref"
                checked: true
            }
            CheckBox {
                id: showVP_
                text: "show vp"
                checked: false
            }
        }
    }
}