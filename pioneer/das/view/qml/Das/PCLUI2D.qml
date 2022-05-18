import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI2D 1.0
import Misc 1.0

ColumnLayout {
    id: component

    property var sensorName: ""
    property var viewports: []
    property var bboxes2D: []
    property var seg2D: []
    property var bboxes3D: []
    property var seg3D: []
    property var lanes: []

    property alias undistort            : undistort_.checked
    property alias undistortimage       : undistortimage_.checked
    property alias world                : world_.checked
    property alias worldCheckBoxVisible : world_.visible
    property alias pointSize            : pointSize_.value
    property alias useColors            : useColors_.checked
    property alias useBoxColors         : useBoxColors_.checked
    property alias boxLabelsSize        : boxLabelsSize_.value
    property alias logScale             : logScale_.checked
    property alias amplitudeRatio       : amplRatio_.value
    property alias confThreshold        : confThreshold_.value
    property alias video                : video_.checked
    property alias categoryFilter       : categoryFilter_.text
    property alias showImageSettings    : image_settings_.visible
    property alias aspectRatio          : aspectRatio_.value
    property alias cropLeft             : cropLeft_.text
    property alias cropRight            : cropRight_.text
    property alias cropTop              : cropTop_.text
    property alias cropBottom           : cropBottom_.text

    property var showActor  : Utils.makeVisibilityDict(component.viewports)
    property var showBBox2D : Utils.makeVisibilityDict(component.bboxes2D)
    property var showSeg2D  : Utils.makeVisibilityDict(component.seg2D)
    property var showBBox3D : Utils.makeVisibilityDict(component.bboxes3D)
    property var showSeg3D  : Utils.makeVisibilityDict(component.seg3D)
    property var showLanes  : Utils.makeVisibilityDict(component.lanes)
    
    readonly property var dsColors   : Utils.makeColorsDict(viewports)
    readonly property var box2DColors: Utils.makeColorsDict(bboxes2D)
    readonly property var box3DColors: Utils.makeColorsDict(bboxes3D)
    
    property var hasReferential: ({})
    
    Layout.fillWidth: true
    

    TabBar {
        id: bar
        height: 15
        Layout.preferredWidth: bar.implicitWidth
        TabButton {
            text: qsTr("3d clouds")
            font.pointSize: 8
            height: 15
            width: visible ? implicitWidth : 0
        }
        TabButton {
            text: qsTr("2d boxes")
            font.pointSize: 8
            height: 15
            visible: bboxes2D.length > 0
            width: visible ? implicitWidth : 0
        }
        TabButton {
            text: qsTr("2d segmentation")
            font.pointSize: 8
            height: 15
            visible: seg2D.length > 0
            width: visible ? implicitWidth : 0
        }
        TabButton {
            text: qsTr("3d boxes")
            font.pointSize: 8
            height: 15
            visible: bboxes3D.length > 0
            width: visible ? implicitWidth : 0
        }
        TabButton {
            text: qsTr("3d segmentation")
            font.pointSize: 8
            height: 15
            visible: seg3D.length > 0
            width: visible ? implicitWidth : 0
        }
        TabButton {
            text: qsTr("lanes")
            font.pointSize: 8
            height: 15
            visible: lanes.length > 0
            width: visible ? implicitWidth : 0
        }
        TabButton {
            text: qsTr("settings")
            font.pointSize: 8
            height: 15
            width: visible ? implicitWidth : 0
        }
    }

    StackLayout {
        Layout.preferredHeight: 125
        Layout.fillWidth: true
        Layout.fillHeight: false
        currentIndex: bar.currentIndex

        AnnotationTab {
            annotations: component.viewports
            showAnnotations: component.showActor
            notify: component.showActorChanged
            boxColors: component.dsColors
            useBoxColors: component.useColors
        }
        AnnotationTab {
            annotations: component.bboxes2D.filter(function(bboxName){return bboxName.startsWith(component.sensorName)})
            showAnnotations: component.showBBox2D
            notify: component.showBBox2DChanged
        }
        AnnotationTab {
            annotations: component.seg2D.filter(function(segName){return segName.startsWith(component.sensorName)})
            showAnnotations: component.showSeg2D
            notify: component.showSeg2DChanged
            boxColors: component.box2DColors
            useBoxColors: component.useBoxColors
        }
        AnnotationTab {
            annotations: component.bboxes3D
            showAnnotations: component.showBBox3D
            notify: component.showBBox3DChanged
            boxColors: component.box3DColors
            useBoxColors: component.useBoxColors
        }
        AnnotationTab {
            annotations: component.seg3D
            showAnnotations: component.showSeg3D
            notify: component.showSeg3DChanged
        }
        AnnotationTab {
            annotations: component.lanes
            showAnnotations: component.showLanes
            notify: component.showLanesChanged
        }
        ColumnLayout {
            id: settings_
            Layout.preferredHeight: 75

            RowLayout {
                Layout.maximumHeight: 25
                Text {text: '3d clouds:'}
                SmallCheckBox {
                    id: logScale_
                    Layout.alignment: Qt.AlignRight
                    text: "log scale"
                    checked: true
                }
                SmallCheckBox {
                    id: useColors_
                    Layout.alignment: Qt.AlignRight
                    text: "colors"
                    checked: false
                }
                SmallCheckBox {
                    id: undistort_
                    Layout.alignment: Qt.AlignRight
                    text: "motion compensation"
                    checked: false
                }
                SmallCheckBox {
                    id: world_
                    Layout.alignment: Qt.AlignRight
                    text: "world"
                    checked: false
                    visible: false
                }
                Text {
                    Layout.alignment: Qt.AlignRight
                    text: "Point size (xyzit): "
                    font.pointSize: 8
                }
                Slider {
                    id: pointSize_
                    Layout.alignment: Qt.AlignRight
                    value: 4
                    from: 1
                    to: 20
                    Layout.preferredWidth: 150
                }
                Text {
                    Layout.alignment: Qt.AlignRight
                    text: "ampl ratio: "
                    font.pointSize: 8
                }
                Slider {
                    id: amplRatio_
                    Layout.alignment: Qt.AlignRight
                    value: 100
                    from: 0
                    to: 100
                    Layout.preferredWidth: 150
                }
            }

            RowLayout {
                id: image_settings_
                visible: false
                Layout.maximumHeight: 25

                Text {text: 'Image: '}
                SmallCheckBox {
                    id: undistortimage_
                    Layout.alignment: Qt.AlignRight
                    text: "undistort image"
                    checked: false
                }
                Text {
                    Layout.alignment: Qt.AlignRight
                    text: "Aspect ratio: "
                    font.pointSize: 8
                }
                Slider {
                    id: aspectRatio_
                    Layout.alignment: Qt.AlignRight
                    value: 1
                    from: 0.2
                    to: 5
                    Layout.preferredWidth: 150
                }
                Text {text: 'Crop:'}
                TextField {
                    id: cropLeft_
                    placeholderText: 'left'
                    Layout.preferredHeight: 30
                    Layout.preferredWidth: 50
                }
                TextField {
                    id: cropRight_
                    placeholderText: 'right'
                    Layout.preferredHeight: 30
                    Layout.preferredWidth: 50
                }
                TextField {
                    id: cropTop_
                    placeholderText: 'top'
                    Layout.preferredHeight: 30
                    Layout.preferredWidth: 50
                }
                TextField {
                    id: cropBottom_
                    placeholderText: 'bottom'
                    Layout.preferredHeight: 30
                    Layout.preferredWidth: 50
                }
            }

            RowLayout {
                Layout.maximumHeight: 25
                Text {text: 'Annotations: '}
                SmallCheckBox {
                    id: useBoxColors_
                    Layout.alignment: Qt.AlignRight
                    text: "box colors"
                    checked: false
                }
                RowLayout {
                    Text {text: "3D labels size"}
                    SpinBox {
                        id: boxLabelsSize_
                        value: 10
                        from: 0
                        to: 20
                        Layout.preferredHeight: 30
                    }
                }
                TextField {
                    id: categoryFilter_
                    placeholderText: "category filter"
                    text: ""
                    Layout.preferredHeight: 30
                }
                Text {
                    Layout.alignment: Qt.AlignRight
                    text: "conf threshold: "
                    font.pointSize: 8
                }
                Slider {
                    id: confThreshold_
                    Layout.alignment: Qt.AlignRight
                    value: 50
                    from: 0
                    to: 100
                    Layout.preferredWidth: 150
                    Binding on value {
                        delayed: true
                        value: confThresholdSB_.value
                    }
                }
                SpinBox {
                    id: confThresholdSB_
                    from: confThreshold_.from
                    to: confThreshold_.to
                    value: confThreshold_.value
                    editable: true
                    Binding on value {
                        delayed: true
                        value: confThreshold_.value
                    }
                    property int decimals: 2
                    property real realValue: value / 100
                    textFromValue: function(value, locale) {
                        return Number(value / 100).toLocaleString(locale, 'f', decimals)
                    }
                    valueFromText: function(text, locale) {
                        return Number.fromLocaleString(locale, text) * 100
                    }
                    Layout.preferredHeight: 30
                }
            }

            RowLayout {
                Layout.maximumHeight: 25
                SmallCheckBox {
                    id: video_
                    Layout.alignment: Qt.AlignRight
                    text: checked ? "recording..." : "start recording"
                    checked: false
                }
            }
        }
    }
}
