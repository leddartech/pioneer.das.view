import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI3D 1.0
import Leddar 1.0
import Das 1.0
import Misc 1.0
import MultiSensorViewer 1.0

DatasourceWindow {
    id: component

    property var viewports

    readonly property alias viewport: viewport_  //Python API
    property alias bboxes3D      : controls_.bboxes3D
    property alias seg3D         : controls_.seg3D
    property alias lanes         : controls_.lanes

    property alias controls: controls_

    readonly property real bad_measure: -1.0   
    property real  measure : bad_measure
    
    menuBar: MenuBar {
        Menu {
            title: "View"
            MenuItem {id: menu_; text: "2d images"; onTriggered: {component.viewer2d.visible = true; component.viewer2d.raise()} }
        }
    }

    property Window viewer2d : Window {
        title: component.dsName + "_2d_view"
        width: component.width; 
        height: component.height
        x: component.x + component.width
        y: component.y
        Echoes2dViewer {
            anchors.fill: parent
            provider.packages: component.dsName in viewport_.pclActors ? viewport_.pclActors[component.dsName].packages : null
        }
    }
    
    PCLUI2D {
        id: controls_
        viewports: component.viewports
        Layout.fillHeight: true
        Layout.preferredWidth: component.width
        showActor: {
            var m = {};
            for(var i in component.viewports) {
                var vp = component.viewports[i]
                m[vp] = (vp == component.dsName);
            }
            return m;
        }
        showIntervals: component.dsName.includes('_ech')
        showVoxelMapSettings: component.dsName.includes('_xyzit-voxmap')
        worldCheckBoxVisible: true
        hasReferential: viewport_.allActors
        onWorldChanged: timer_.start()
        Timer {
            id: timer_
            interval: 1
            running: false
            repeat: false
            onTriggered: viewport_.resetCamera()
        }
    }

    Viewport {
        id: viewport_
        Layout.fillHeight: true
        Layout.fillWidth: true

        RowLayout {
            Button {
                id: reset_
                Layout.preferredHeight: 25
                text: "reset camera"
                onClicked: viewport_.resetCamera()
            }
            TextField {
                selectByMouse: true
                text: line_.visible ? component.measure.toFixed(3) : "Measure: Ctrl + Right Click, to start, then hold Ctrl and move mouse over a point"
                Layout.preferredWidth: line_.visible ? 100 : viewport_.width - reset_.width
                Layout.preferredHeight: 25
            }
            Button {
                text: "clear measure"
                Layout.preferredHeight: 25
                visible: line_.visible
                onClicked: {
                    line_.visible = false
                    component.measure = component.bad_measure
                }
            }
        }
        
        //TODO: find a cleaner way to do that
        readonly property bool isZUp : !component.dsName.includes('_ech') || component.dsName.includes('pixell_') || controls_.world

        Behavior on camera.eye {
            SequentialAnimation {
                Vector3dAnimation { duration:  300; easing.type:   "OutQuad"; }
                Vector3dAnimation { duration: 1000; easing.type: "InOutQuad" }
            }
        }
        Behavior on camera.up {
            SequentialAnimation {
                Vector3dAnimation { duration:  300; easing.type:   "OutQuad"; }
                Vector3dAnimation { duration: 1000; easing.type: "InOutQuad" }
            }
        }
        Behavior on camera.center {
            SequentialAnimation {
                Vector3dAnimation { duration:  300; easing.type:   "OutQuad"; }
                Vector3dAnimation { duration: 1000; easing.type: "InOutQuad" }
            }
        }

        function resetCamera() {
            var up  = viewport_.isZUp ? Qt.vector3d(0,0,1)   : Qt.vector3d(0,component.bad_measure,0)
            var eye = viewport_.isZUp ? Qt.vector3d(-10,0,0) : Qt.vector3d(0,0,-10)
            var tf_Ref_from_Local = controls_.world ? allActors[component.dsName].transform.worldTransform(true) : Qt.matrix4x4()
            camera.center = tf_Ref_from_Local.times(Qt.vector3d(0,0,0))
            camera.up     = tf_Ref_from_Local.times(up.toVector4d()).toVector3d()
            camera.eye    = tf_Ref_from_Local.times(eye)
        }
        Component.onCompleted: resetCamera()

        readonly property var pclActors: {
            var m = {};
            for(var i = 0; i < pclInstanciator_.count; i++) {
                var a = pclInstanciator_.objectAt(i);
                m[a.objectName] = {
                      actor         : a
                    , hasReferential: a.hasReferential
                    , transform     : a.transform
                    , packages      : a.packages
                    , cloud         : a.cloud
                };
            }
            return m;
        }

        readonly property var segActors: {
            var m = {};
            for(var i = 0; i < segInstanciator_.count; i++) {
                var a = segInstanciator_.objectAt(i);
                m[a.objectName] = {
                      actor         : a
                    , hasReferential: a.hasReferential
                    , transform     : a.transform
                    , packages      : a.packages
                    , cloud         : a.cloud
                };
            }
            return m;
        }

        readonly property var bboxActors: {
            var m = {};
            for(var i = 0; i < bboxInstantiator_.count; i++) {
                var a = bboxInstantiator_.objectAt(i);
                m[a.objectName] = {hasReferential: a.hasReferential, actor: a, cursor: a.cursor};
            }
            return m;
        }

        readonly property var laneActors: {
            var m = {};
            for(var i = 0; i < laneInstantiator_.count; i++) {
                var a = laneInstantiator_.objectAt(i);
                m[a.objectName] = {hasReferential: a.hasReferential, actor: a};
            }
            return m;
        }

        readonly property var allActors : Utils.merge(pclActors, segActors, bboxActors, laneActors)

        actors: Actors {
            GridXZ{isXY: viewport_.isZUp}
            Box{filled: false}
            Actors {
                instanciator: Instantiator {
                    id: pclInstanciator_
                    model: component.viewports.filter(function(ds){return ds.includes("_ech") || ds.includes("_xyzit") || ds.includes("_xyzvcfar");});
                    
                    delegate: LidarActor {
                        id: actor_
                        objectName: modelData

                        visible: controls_.showActor[modelData]
                        referential: controls_.world ? 'world' : component.sensorName
                        sensorColor: controls_.dsColors[modelData]
                        colorMap: controls_.useColors ? '' : 'viridis'
                        method: modelData.includes("_ech") ? 'quad_cloud' : 'point_cloud'
                        undistort: controls_.undistort
                        pointSize: controls_.pointSize
                        amplitudeRatio: controls_.amplitudeRatio
                        amplitudeType: controls_.amplitudeType
                        logScale: controls_.logScale
                        useRGB: modelData.includes("-rgb") // This is dirty. The way the point clouds are colored should be refactored at some point.

                        property var c: Connections {
                            target: actor_.echoActor
                            onHovered: {
                                var point = worldOrigin.plus(worldDirection.times(tuv.x));
                                
                                if (event.modifiers & Qt.ControlModifier) {
                                    if(line_.visible) {
                                        line_.to = point
                                        component.measure = line_.to.minus(line_.from).length()
                                    }
                                }
                            }

                            onClicked: {
                                var point = worldOrigin.plus(worldDirection.times(tuv.x))
                                if (event.modifiers & Qt.ControlModifier) {
                                    line_.visible = true
                                    line_.to = line_.from = point
                                    component.measure = component.bad_measure
                                }
                            }
                        }
                    }
                }
            }

            Actors {
                instanciator: Instantiator {
                    id: segInstanciator_
                    model: component.seg3D.filter(function(ds){return ds.includes("_seg3d");});
                    
                    delegate: LidarActor {
                        objectName: modelData
                        visible: controls_.showSeg3D[modelData]
                        referential: controls_.world ? 'world' : component.sensorName
                        undistort: controls_.undistort
                        pointSize: controls_.pointSize
                        useSeg3D: true
                    }
                }
            }

            Actors {
                
                instanciator: Instantiator {
                    id: bboxInstantiator_
                    model: component.bboxes3D
                    
                    delegate: Actors {
                        id: bbox_
                        objectName: modelData
           
                        property bool hasReferential: true
                        property var cursor: Rectangle {
                            id: cursor_
                            property string truncation: ''
                            property string occlusion: ''
                            property string vehicleActivity: ''
                            property string humanActivity: ''
                            property string onTheRoad: ''
                            border.width : 1
                            parent: viewport_
                            y:25
                            visible:false
                            onVisibleChanged: {
                                if(visible)
                                    cursorTimer_.start();
                            }
                            color: 'white'
                            Column {
                                id: column_
                                anchors.fill: parent
                                leftPadding: 5
                                rightPadding: 5
                                Label{visible: cursor_.truncation != ''; text: 'Truncation: ' + cursor_.truncation}
                                Label{visible: cursor_.occlusion != ''; text: 'Occlusion: ' + cursor_.occlusion}
                                Label{visible: cursor_.onTheRoad != ''; text: 'On the road: ' + cursor_.onTheRoad}
                                Label{visible: cursor_.vehicleActivity != ''; text: 'Vehicle activity: ' + cursor_.vehicleActivity}
                                Label{visible: cursor_.humanActivity != ''; text: 'Human activity: ' + cursor_.humanActivity}
                            }
                            width: column_.implicitWidth
                            height: column_.implicitHeight
                            Timer {
                                id: cursorTimer_
                                interval: 100
                                onTriggered: cursor_.visible = false
                            }
                        }
                    }
                }
            }

            Actors {
                instanciator: Instantiator {
                    id: laneInstantiator_
                    model: component.lanes
                   
                    delegate: Actors {
                        objectName: modelData
                        property bool hasReferential: true
                    }
                }
            }

            Actor {
                id: line_
                visible: false
                property vector3d from: Qt.vector3d(0,0,0)
                property vector3d to: Qt.vector3d(0,0,0)
                geometry: Geometry {
                    primitiveType: Geometry.LINES
                    indices: ArrayUInt1 {input: [0,1]}
                    attribs: Attribs {
                        vertices: ArrayFloat3 {
                            input: [line_.from, line_.to]
                        }
                    }
                }
                effect: Effect {
                    lineWidth: 4
                    shader0: EmissiveProgram{color: "white"}
                }
            }
        }
    }
}