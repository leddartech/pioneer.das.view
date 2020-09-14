/*
* Created on Feb 14, 2018
*
* \author: maxime
* \filename: Example1.qml
*/

import MPLBackend 1.0
import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import Leddar 1.0
import UI3D 1.0
import UI2D 1.0
import Misc 1.0

ApplicationWindow {
    id: component
    /// support for wait_key()
    property string key: ''
    
    /// Python API
    readonly property alias viewport   : viewport_
    readonly property alias imgWindow  : imgWindow_
    readonly property alias pose       : pose_
    readonly property alias slider     : slider_
    readonly property alias plot       : plot_
    readonly property alias save       : save_
    readonly property alias icp        : icp_
    readonly property alias colors     : color_
    readonly property alias filters    : filter_

    ///
    width: 1320
    height: 600

    ColumnLayout {
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true

            Slider {
                id: slider_
                Layout.fillWidth: true
                height: implicitHeight
                value: 0
                snapMode: Slider.SnapAlways
                wheelEnabled: true
                live: false
            }

        }
        Viewport {
            id: viewport_
            Layout.fillWidth: true
            Layout.fillHeight: true
            focus: true
            Keys.onPressed: component.key = event.text // support for wait_key()
            actors: Actors {}
        }
        RowLayout {
            id: controls_
            Layout.preferredHeight: controls_.implicitHeight

            PoseEditor {
                id: pose_
                Layout.fillWidth: true
                onKeyChanged: component.key = pose_.key // support for wait_key()
                scaleVisible: false
            }
            Button {
                id: plot_
                text: "point cloud/surface cloud"
                checkable: true
            }
            Button {
                id: save_
                text: "save"
            }
            Button {
                id: icp_
                text: "icp"
            }
            Button {
                id: color_
                text: "colors"
                checkable: true
            }
            TextField {
                id: filter_
                placeholderText: "Provide infos (e.g timestamps)"
                text: ""
                Layout.preferredHeight: 40
            }
        }
    }

    Window {
        id: imgWindow_
        x:800
        width: 1200
        height: 900
        visible: true
        readonly property alias figure: imgFigure_
        FigureWithToolbar {
            id: imgFigure_
            anchors.fill: parent
            Keys.onPressed: component.key = event.text/// support for wait_key()
        }
    }
}