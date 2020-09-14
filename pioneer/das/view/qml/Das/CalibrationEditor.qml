import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI2D 1.0
import Das 1.0

Window {
    id: component
    title: qsTr('Extrinsics calibration fine-tuner')

    property var windowsUIModel 

    /// Python API
    readonly property alias pose       : pose_
    readonly property alias icp        : icp_
    readonly property alias save       : save_
    readonly property alias reset      : reset_
    property alias sourceComboBox      : sourceComboBox_
    property alias destinationComboBox : destinationComboBox_
    property alias calibmodeComboBox   : calibmodeComboBox_
    
    width: controls_.implicitWidth
    height: controls_.implicitHeight

    onClosing:  windowsUIModel.calibEditorVisible = false
    
    Connections {
        target : windowsUIModel
        function onCalibEditorVisibleChanged() {
            if (component.windowsUIModel.calibEditorVisible)
                component.raise()
            else if(!component.closing)
                component.hide()
        }
    }
    ColumnLayout {
        id: controls_
        anchors.fill: parent
        RowLayout {
            Layout.fillWidth: true
            RowLayout {
                Text {text: 'from sensor '}
                ComboBox {id: sourceComboBox_}
                Text {text: ' to sensor '}
                ComboBox {id: destinationComboBox_}
            }
            RowLayout {
                Text {text: 'calibration mode: '}
                ComboBox {id: calibmodeComboBox_}
            }
            RowLayout {
                Button {
                    id: reset_
                    text: "reset"
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            PoseEditor {
                id: pose_
                scaleVisible: false
            }
            Button {
                id: save_
                text: "save"
            }
        }
        RowLayout {
            Layout.fillWidth: true
            CalibrationICP {
                id: icp_
                scaleVisible: false
            }  
        }
    }
}