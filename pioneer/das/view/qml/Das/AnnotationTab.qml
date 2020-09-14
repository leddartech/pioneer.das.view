import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI2D 1.0
import Misc 1.0



Flickable {
    id: component
    property var annotations: []
    property var showAnnotations: ({})
    property var notify
    property var boxColors: []
    property bool useBoxColors: false

    Layout.preferredHeight: 75
    Layout.fillWidth: true
    contentWidth: gridLayout_.implicitWidth
    contentHeight: gridLayout_.implicitHeight
    clip: true
    flickableDirection: Flickable.VerticalFlick

    ScrollBar.vertical: ScrollBar {}
    ColumnLayout {
        RowLayout {
            TextField {
                id: filter_
                placeholderText: "Enter filter here, e.g., eagle*"
                text: ""
                Layout.preferredHeight: 25
            }
        }

        GridLayout {
            id: gridLayout_
            Layout.fillWidth: true
            Layout.fillHeight: true
            columns: 4
            rowSpacing: 0
            columnSpacing: 0

            Repeater {
                id: repeater_

                model: component.annotations.filter(function(annotation) {
                    if (filter_.text == "")
                        return true;
                    return new RegExp('^' + filter_.text.replace(/\*/g, '.*') + '$').test(annotation);
                })

                SmallCheckBox {
                    text: component.useBoxColors ? ('<font color="' + component.boxColors[modelData] + '">' + modelData + '</font>') : modelData
                    height: 15
                    Binding on checked {
                        value: component.showAnnotations[modelData]
                    }
                    onCheckedChanged: {component.showAnnotations[modelData] = checked; component.notify()}
                }
            }
        }
    }
}