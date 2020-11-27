/*
* Created on Dec 12, 2018
*
* \author: maxime
* \filename: LCAActor.qml
*/

import QtQuick 2.9
import Leddar 1.0
import Das 1.0
import UI3D 1.0
import QtQuick.Controls 2.4

Actors {
    id: component

    property alias minAmplitude : cloud_.minAmplitude 
    property alias maxAmplitude : cloud_.maxAmplitude 
    property alias amplitudeRatio : cloud_.amplitudeRatio 
    property alias amplitudeType : cloud_.amplitudeType
    property alias referential  : cloud_.referential
    property alias undistort    : cloud_.undistort
    property alias method       : cloud_.method
    property alias logScale     : cloud_.logScale
    property alias cloud        : cloud_
    property alias echoActor    : echoActor_
    
    readonly property alias packages: packages_;  //FIXME: fully transition 2d viewer to das.api (so it uses samples.Echo api)

    readonly property alias hasReferential : cloud_.hasReferential

    property alias transform : cloud_.transform

    property int pointSize: 4

    property string colorMap : 'jet'
    property string sensorColor: ''
    property bool useSeg3D: false
    property bool useRGB: false

    property bool visible: true

    property var clickEcho //(int v, int h)

    XYZ {
        transform: cloud_.transform
        visible: component.visible
    }

    XYZ {
        scale: 10
        visible: component.visible
    }

    property var cursor: Rectangle {
        id: cursor_
        property bool isEcho: true
    	property real distance: 0
        property real amplitude: 0
        property int timestamp: 0
        property int flag: 0
    	property int h: 0
        property int v: 0
        property int i: 0
        property string category: ''
        property vector3d point: Qt.vector3d(0,0,0)
    	border.width : 1
    	visible:false
    	onVisibleChanged: {
    		if(visible)
    			cursorTimer_.start();
    	}
    	color: 'gray'
    	Column {
    		id: column_
    		anchors.fill: parent
    		leftPadding: 5
    		rightPadding: 5
            Label{text: 'world: ' + [cursor_.point.x.toFixed(2), cursor_.point.y.toFixed(2), cursor_.point.z.toFixed(2)]}
            Label{visible: cursor_.isEcho; text:'channel (i,v,h): ' + cursor_.i + ', ' + cursor_.v + ', ' + cursor_.h}
    		Label{visible: cursor_.isEcho; text:'distance: ' + cursor_.distance.toFixed(2)}
            Label{visible: cursor_.isEcho; text:'amplitude: ' + cursor_.amplitude.toFixed(0)}
            Label{visible: cursor_.isEcho; text:'ts offset: ' + cursor_.timestamp}
            Label{visible: cursor_.isEcho; text:'flag: ' + cursor_.flag}
            Label {
                visible: component.useSeg3D
                text: 'category: ' + cursor_.category
            }
    	}
    	width: column_.implicitWidth
    	height: column_.implicitHeight
    	Timer {
    		id: cursorTimer_
    		interval: 100
    		onTriggered: cursor_.visible = false
        }
        VariantProduct{id: packages_} //ignore this
        PointsColorProgram {
            id: pointscolor_
        }
        AmplitudesProgram {
            id: ampl_
            color: component.sensorColor
        }
        ColorMapProgram {
            id: cmap_
            defaultColorMap.colorMap: component.colorMap
        }
        AmplitudeAttribs {
            id: amplitudeAttribs_
            vertices : DasSampleToCloud {
                id: cloud_
                objectName: "cloud"
                //minAmplitude : input alias 
                //maxAmplitude : input alias 
                //sample       : input alias
                //referential  : input alias
                //undistort    : input alias
                //logScale     : input alias
            }
            amplitude: cloud_.amplitudes
        }

        ColorsAttribs {
            id: colorsAttribs_
            vertices: cloud_
            colors: cloud_.colors
        }
    }
    Actor {
        id: echoActor_
        objectName: component.objectName + "_echoActor"
        visible: component.visible
        geometry: Geometry {
            id: geometry_
            primitiveType: cloud_.primitiveType
            indices: cloud_.indices
            attribs: component.useSeg3D | component.useRGB ? colorsAttribs_ : amplitudeAttribs_
        }
        onClicked: {
            var point = worldOrigin.plus(worldDirection.times(tuv.x))
            if (cloud_.primitiveType == Geometry.TRIANGLES) {
                var info = cloud_.channelInfo(id);
                if (component.clickEcho !== undefined)
                    component.clickEcho(info.v, info.h)
            }
        }
        onHovered: {
            var point = worldOrigin.plus(worldDirection.times(tuv.x))

            component.cursor.x = event.pos.x+5;
            component.cursor.y = event.pos.y;
            component.cursor.parent = viewport;
            component.cursor.point = point;

            // console.log("PT: " + cloud_.primitiveType + " tuv: " + tuv.toString())

            switch(cloud_.primitiveType) {
                case Geometry.TRIANGLES: {
                    component.cursor.isEcho = true;

                    var info = cloud_.channelInfo(id);
                    component.cursor.v = info.v;
                    component.cursor.h = info.h;
                    component.cursor.i = info.i;
                    component.cursor.distance = info.distance;
                    component.cursor.amplitude = info.amplitude;
                    component.cursor.timestamp = info.timestamp;
                    component.cursor.flag = info.flag;
                    component.cursor.category = info.category;
                    component.cursor.visible = true;
                    break;
                }
                case Geometry.POINTS: {
                    component.cursor.isEcho = false;
                    component.cursor.visible = true;
                    break;
                }
                default: 
                    component.cursor.visible = false;
            }
        }
        effect: Effect {
            pointSize: component.pointSize //for point clouds
            shader0: component.useSeg3D | component.useRGB ? pointscolor_ : (component.colorMap == '' ? ampl_ : cmap_)
        }
    }
}