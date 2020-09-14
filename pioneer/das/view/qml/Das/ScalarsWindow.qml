import MPLBackend 1.0
import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.9
import UI2D 1.0


DatasourceWindow {
    id: component

    ////// python API
    property var columnNames          : []
    property var showColumn           : ({})
    readonly property alias markers   : markers_.checked
    property alias startTime          : startTime_.text
    property alias endTime            : endTime_.text
    ///////////////////////////////

    RowLayout {
        Text {text: 'Time interval: '}
        TextField {
            Layout.preferredHeight: 30
            Layout.preferredWidth: 60
            id: startTime_
            text: '-5'
        }
        TextField {
            Layout.preferredHeight: 30
            Layout.preferredWidth: 60
            id: endTime_
            text: '5'
        }
        Text {text: 'seconds'}
    }

    RowLayout {
        SmallCheckBox {
            id: markers_
            text: "Markers"
            checked: false
        }
    }

    FigureWithToolbar {
        Layout.fillWidth: true
        Layout.fillHeight: true
    }

    GridLayout {
        id: controls_
        columns: 4
        
        Repeater {
            model: component.columnNames
            CheckBox {
                text: modelData
                Binding on checked {
                    delayed: true
                    value: (modelData in component.showColumn) ? component.showColumn[modelData] : false;
                }
                onCheckedChanged: {component.showColumn[modelData] = checked; component.showColumnChanged()}
            }
        }
    }
}