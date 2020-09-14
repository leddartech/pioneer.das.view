import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.9
import QtQuick.Dialogs 1.0
import Misc 1.0
import UI2D 1.0

ColumnLayout {
    id: component

    property int nIndices
    property var sensors
    property var synchDatasources
    property var customDatasources
    property var windowsUIModel
    property var allWindows
    property bool isLive : false
    property bool recording : false

    property alias cursor : slider_.value
    property alias cursors : cursors_.cursors
    property alias saveSlices: saveSlices_
    
    Keys.onRightPressed: cursor += (event.modifiers & Qt.ShiftModifier) ? 10 : 1
    Keys.onLeftPressed : cursor -= (event.modifiers & Qt.ShiftModifier) ? 10 : 1

    Label {
        text: component.isLive ? "Recording Live" : "Synchronized cursor"
        font.bold: true
        font.underline: true
    }

    RowLayout {
        visible: !component.isLive
        GridLayout {
            columns: 2
            Button {
                id: play_
                Timer {
                    id: timer_
                    interval: 100
                    running: false
                    repeat: true
                    onTriggered: {
                        if(intervalsOnly_.checked) {
                            var index = Utils.upperBound(cursors_.cursors, component.cursor)
                            if (index == -1)
                                component.cursor = cursors_.cursors[0]
                            else if(index%2 == 0) //then the next cursor opens an interval
                                component.cursor = cursors_.cursors[index]
                            else { //the the nex cursor closes an interval
                                var candidate = component.cursor + stride_.value
                                if(candidate > cursors_.cursors[index])
                                    candidate = cursors_.cursors[(index < cursors_.cursors.length-1) ? index+1 : 0]
                                component.cursor = candidate
                            }
                        }
                        else
                            component.cursor = (component.cursor + stride_.value) % component.nIndices
                    }
                }
                text: (timer_.running ? 'pause' : 'play') + (intervalsOnly_.checked ? " (itrvls)" : "")
                onClicked: timer_.running = ! timer_.running
            }

            TextField {
                Binding on text {
                    delayed: true
                    value: slider_.valueAt(slider_.position)
                }
                Layout.preferredWidth: 100
                onEditingFinished: component.cursor = text
                validator: IntValidator{bottom: 0; top: slider_.to}
                selectByMouse: true
                mouseSelectionMode: TextInput.SelectWords
            }
            Button {
                text: '-10'
                onClicked: component.cursor = Math.max(0, (component.cursor - 10))
            }
            Button {
                text: '+10'
                onClicked: component.cursor = Math.min((component.cursor + 10), component.nIndices)
            }
            Button {
                text: 'add current'
                onClicked: cursors_.addCursor(cursors_.positionToX(slider_.position))
            }
            Button {
                text: 'go to next'
                enabled: nSamples_.nSamples > 0
                onClicked: {
                    var index = Utils.upperBound(cursors_.cursors, component.cursor)
                    component.cursor = cursors_.cursors[(index == -1) ? 0 : index]
                }
            }
        }

        ColumnLayout {
            Slider {
                id: slider_
                Layout.fillWidth: true
                height: implicitHeight
                value: 0
                to: component.nIndices-1
                stepSize: stride_.value
                snapMode: Slider.SnapAlways
                wheelEnabled: true
                live: false
            }
            Rectangle {
                id: cursors_
                Layout.fillWidth: true

                Layout.leftMargin: slider_.leftPadding
                Layout.rightMargin: slider_.rightPadding
                color: "lightgrey"
                height: 10
                radius: 2
                property int cursorsWidth: 6
                property var cursors: []

                function positionToX(position) {
                    return position * width;
                }
                function xToPostion(x) {
                    return (x + cursorsWidth/2)/width
                }
                function valueToPosition(v) {
                    return v/(component.nIndices)
                }
                function valueToX(v) {
                    return positionToX(valueToPosition(v))
                }
                function addCursor(x) {
                    var v = slider_.valueAt(xToPostion(x))
                    cursors.push(v); 
                    Utils.sort(cursors);
                    cursorsChanged();
                }
                function removeCursor(index) {
                    cursors.splice(index, 1);
                    cursorsChanged();
                }
                function moveCursor(index, x) {
                    var v = slider_.valueAt(xToPostion(x))
                    cursors[index] = v; 
                    Utils.sort(cursors);
                    cursorsChanged();
                }

                MouseArea {
                    anchors.fill: parent
                    onClicked: cursors_.addCursor(mouse.x)
                }
                Text {
                    anchors.fill: parent
                    text: "click on that bar to select slices of dataset"
                    font.italic: true
                    visible: cursors_.cursors.length == 0
                }
                Repeater {
                    anchors.fill: parent
                    model: cursors_.cursors.length
                    Rectangle {
                        id: rect
                        width: cursors_.cursorsWidth
                        height: cursors_.height
                        radius: cursors_.radius
                        color: index%2 ? "red" : "green"
                        x: cursors_.valueToX(cursors_.cursors[index])
                        Binding on x{value: cursors_.valueToX(cursors_.cursors[index])}
                        Drag.active: cursorArea_.drag.active
                        MouseArea {
                            id: cursorArea_
                            anchors.fill: parent
                            drag.target: parent
                            drag.axis: Drag.XAxis
                            acceptedButtons: Qt.LeftButton | Qt.RightButton
                            onReleased: cursors_.moveCursor(index, parent.x)
                            onClicked: {   
                                console.log(mouse.button, Qt.RightButton)
                                if(mouse.button == Qt.RightButton)
                                    cursors_.removeCursor(index)
                            }
                        }
                    }
                }

                Repeater {
                    anchors.fill: parent
                    model: cursors_.cursors.length/2|0
                    Rectangle {
                        id: rect
                        readonly property real a: cursors_.valueToX(cursors_.cursors[index*2])
                        readonly property real b: cursors_.valueToX(cursors_.cursors[index*2+1])
                        width: b-a - cursors_.cursorsWidth
                        height: cursors_.height/2
                        radius: cursors_.radius
                        color: "grey"
                        x: a + cursors_.cursorsWidth
                        y: cursors_.height/4
                    }
                }
            }

            RowLayout {
                Text {text: "Sliced intervals: "}
                IntervalsEditor {
                    id: cursorsText_
                    Layout.fillWidth: true
                    cursorsOwner: cursors_
                    Layout.preferredHeight: 30
                }
                Text {text: "stride: "}
                SpinBox {
                    id: stride_
                    value: 1
                    from: 1
                    to: 100
                    Layout.preferredHeight: 30
                    Layout.preferredWidth: 120
                }
                Text {
                    id: nSamples_
                    visible: intervalsOnly_.visible
                    readonly property int nSamples: {
                        var nSamples = 0;
                        for (var i = 1; i < component.cursors.length; i+=2) {
                            nSamples += Math.floor((component.cursors[i] - component.cursors[i-1])/stride_.value)
                        }
                        return nSamples
                    }
                    text: "Total samples: " + nSamples
                }
                CheckBox {
                    id: intervalsOnly_
                    text: "play intervals only"
                    visible: nSamples_.nSamples > 0
                    checked: false
                }
                Button {
                    id: saveSlices_
                    enabled: nSamples_.nSamples > 0
                    text: "save slices"
                }
            }
        }
    }

    RowLayout {
        visible: component.isLive
        GridLayout {
            columns: 1
            id: recorder_
            Button {
                text: component.recording? 'Recording...' : 'Record'
                onClicked: component.recording =! component.recording
            }
        }
    }
    
    Label {
        text: "Sensors and datasources displays" 
        font.bold: true
        font.underline: true
    }

    Repeater {
        model: Object.keys(component.sensors)
        delegate: RowLayout {
            id: sensorRow_
            readonly property var sensor: component.sensors[modelData]
            Text {   
                Layout.preferredWidth: 100
                text: modelData
            }
            Repeater {
                model: Object.keys(sensorRow_.sensor)
                Button {
                    readonly property var datasource: sensorRow_.sensor[modelData]

                    Layout.preferredWidth: 100
                    readonly property string dsName: datasource['full_ds_name']
                    readonly property bool synch : datasource['full_ds_name'] in component.synchDatasources
                    text: datasource['ds_name'] + (synch ? "*" : "")
                    enabled: dsName in component.allWindows
                    Binding on checked {
                        value: enabled ? component.windowsUIModel.model[dsName].visible : false
                    }
                    onClicked: {
                        component.windowsUIModel.setValue(dsName, "visible", !component.windowsUIModel.model[dsName].visible)
                        var window = allWindows[dsName]
                        if(component.windowsUIModel.model[dsName].visible)
                            window.raise();
                        else
                            window.hide();
                    }
                }
            }
        }
    }

    RowLayout {
        Text {   
            Layout.preferredWidth: 200
            text: "Other views"
        }
        Repeater {
            model: Object.keys(component.customDatasources)
            delegate:  Button {
                Layout.preferredWidth: 100
                text: modelData
                Binding on checked {
                    value: component.windowsUIModel.model[modelData].visible
                }
                onClicked: {
                    component.windowsUIModel.setValue(modelData, "visible", !component.windowsUIModel.model[modelData].visible)
                    var window = allWindows[modelData]
                    if(component.windowsUIModel.model[modelData].visible)
                        window.raise();
                    else
                        window.hide();
                }
            }
        }
    }

    RowLayout {
        Text {   
            Layout.preferredWidth: 100
            text: "Editors"
        }
        Button {
            id: calibVisible_
            Layout.preferredWidth: 100
            text: "Calibration"
            checkable: true
            Binding on checked {
                delayed: true
                value: component.windowsUIModel.calibEditorVisible
            }
        }
        Binding {
            delayed: true
            target: component.windowsUIModel
            property: "calibEditorVisible"
            value: calibVisible_.checked
        }
        Button {
            id: metadataVisible_
            Layout.preferredWidth: 100
            text: "Metadata"
            checkable: true
            Binding on checked {
                delayed: true
                value: component.windowsUIModel.metadataEditorVisible
            }
        }
        Binding {
            delayed: true
            target: component.windowsUIModel
            property: "metadataEditorVisible"
            value: metadataVisible_.checked
        }
    }
}