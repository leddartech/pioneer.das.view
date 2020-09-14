
import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9

ApplicationWindow {
    id: component

    // python API
    property alias extraContent: extraContent_
    property alias cursor: slider_.value //API
    property int synchronizedCursor: -1  //API
    property int playerCursor: -1
    /////////////

    property var windowsUIModel
    property var datasources

    readonly property alias slider: slider_
    default property alias children: columnLayout_.children

    readonly property string dsName: modelData   //meant to be used in an Instantiator
    readonly property string sensorName: {var l = dsName.split('_'); return l[0] + "_" + l[1]}
    
    title: dsName 


    onSynchronizedCursorChanged: cursor = synchronizedCursor
    readonly property bool synch: synchronizedCursor == cursor
    Binding on visible {
        //this make the window visible when Player's buttons are selected:
        value: dsName in component.windowsUIModel.model ? component.windowsUIModel.model[dsName].visible : false 
    }
    onClosing: {
        //this will make Player's buttons unselected when the window is closed:
        windowsUIModel.setValue(dsName, "visible", false)
    } 
    width: 800; height: 600

    ColumnLayout {
        id: columnLayout_
        anchors.fill: parent
        RowLayout {
            Layout.fillHeight: true
            Slider {
                Layout.fillWidth: true
                id: slider_
                value: 0
                to: component.dsName in component.datasources ? component.datasources[component.dsName]['size']-1 : 0
                stepSize: 1
                snapMode: Slider.SnapAlways
                wheelEnabled: true
                live: false
            }
            Text {text: slider_.valueAt(slider_.visualPosition)}
            Button {
                text: component.synchronizedCursor == -1 ? "not synchronized" : (component.synch ? "synchronized" : "resynchronize")
                enabled: !component.synch && component.synchronizedCursor != -1
                onClicked: component.synchronizedCursorChanged()
                font.bold: !component.synch
            }
        }
        RowLayout {
            visible: false
            id: extraContent_
        }
    }
}