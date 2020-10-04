import QtQuick 2.12
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI2D 1.0
import Das 1.0
import MPLBackend 1.0


Window {
    id: component
    title: qsTr('Metadata Editor')

    property var windowsUIModel 

    /// Python API
    property alias firstFrameSelection             : firstFrameSelection_.text
    property alias lastFrameSelection              : lastFrameSelection_.text
    readonly property alias selectAllFrames        : selectAllFrames_
    readonly property alias currentFirstFrame      : currentFirstFrame_
    readonly property alias currentLastFrame       : currentLastFrame_
    property alias snapFirstFrame                  : snapFirstFrame_
    property alias snapLastFrame                   : snapLastFrame_
    readonly property alias nextFirstFrame         : nextFirstFrame_
    readonly property alias lastLastFrame          : lastLastFrame_

    readonly property alias fastbackwardFirstFrame : fastbackwardFirstFrame_
    readonly property alias backwardFirstFrame     : backwardFirstFrame_
    readonly property alias forwardFirstFrame      : forwardFirstFrame_
    readonly property alias fastforwardFirstFrame  : fastforwardFirstFrame_
    readonly property alias fastbackwardLastFrame  : fastbackwardLastFrame_
    readonly property alias backwardLastFrame      : backwardLastFrame_
    readonly property alias forwardLastFrame       : forwardLastFrame_
    readonly property alias fastforwardLastFrame   : fastforwardLastFrame_

    readonly property alias addSynchronizationData : addSynchronizationData_
    readonly property alias addSyncQualityData     : addSyncQualityData_
    readonly property alias addIMUQualityData      : addIMUQualityData_
    readonly property alias addObjectQuantityData  : addObjectQuantityData_

    readonly property alias save                   : save_

    property var tableView                         : tableView_
    property var entries                           : entries_
    property var entryDescription                  : entryDescription_

    property var input                             : input_
    property var keyword_input                     : keyword_input_
    readonly property alias commitInput            : commitInput_

    property var columnNames : []
    property var showColumn : ({})

    property bool isDirty : false
    
    property int playerCursor: 0
    

    width: controls_.implicitWidth
    height: controls_.implicitHeight

    onClosing:  windowsUIModel.metadataEditorVisible = false
    
    Connections {
        target : windowsUIModel
        function onMetadataEditorVisibleChanged()
        {
            if (component.windowsUIModel.metadataEditorVisible)
                component.raise()
            else if(!component.closing)
                component.hide()
        }
    }

    ColumnLayout {
        id: controls_
        anchors.fill: parent

        RowLayout {

            ColumnLayout {
                Text {
                    Layout.preferredWidth: 100
                    text: 'Frame(s):'
                }
            }
            ColumnLayout {
                Button {
                    Layout.preferredWidth: 35
                    id: fastbackwardFirstFrame_
                    text: '<<'
                }
                Button {
                    Layout.preferredWidth: 35
                    id: fastbackwardLastFrame_
                    text: '<<'
                }
            }
            ColumnLayout {
                Button {
                    Layout.preferredWidth: 35
                    id: backwardFirstFrame_
                    text: '<'
                }
                Button {
                    Layout.preferredWidth: 35
                    id: backwardLastFrame_
                    text: '<'
                }
            }
            ColumnLayout {
                TextField {
                    Layout.preferredWidth: 90.5
                    id: firstFrameSelection_
                    text: ''
                }
                TextField {
                    Layout.preferredWidth: 90.5
                    id: lastFrameSelection_
                    text: ''
                }
            }
            ColumnLayout {
                Button {
                    Layout.preferredWidth: 35
                    id: forwardFirstFrame_
                    text: '>'
                }
                Button {
                    Layout.preferredWidth: 35
                    id: forwardLastFrame_
                    text: '>'
                }
            }
            ColumnLayout {
                Button {
                    Layout.preferredWidth: 35
                    id: fastforwardFirstFrame_
                    text: '>>'
                }
                Button {
                    Layout.preferredWidth: 35
                    id: fastforwardLastFrame_
                    text: '>>'
                }
            }
            ColumnLayout {
                Button {
                    id: snapFirstFrame_
                    checkable: true
                    text: 'Snap'
                }
                Button {
                    id: snapLastFrame_
                    checkable: true
                    text: 'Snap'
                }
            }
            ColumnLayout {
                Button {
                    id: currentFirstFrame_
                    text: 'Current'
                }
                Button {
                    id: currentLastFrame_
                    text: 'Current'
                }
            }
            ColumnLayout {
                Button {
                    id: nextFirstFrame_
                    text: 'Next'
                }
                Button {
                    id: lastLastFrame_
                    text: 'Last'
                }
            }
            ColumnLayout {
                Button {
                    id: selectAllFrames_
                    text: 'All'
                }
            }      
        }

        RowLayout {
            id: autoFill_

            Text {
                Layout.preferredWidth: 100
                text: 'Auto fill:'
            }
            Button {
                id: addSynchronizationData_
                text: "Sync Data"
            }
            Button {
                id: addSyncQualityData_
                text: "Sync Quality"
            }
            Button {
                id: addIMUQualityData_
                text: "IMU Quality"
            }
            Button {
                id: addObjectQuantityData_
                text: "Objects"
            }
        }

        RowLayout {
            id: selection_

            Text {
                Layout.preferredWidth: 100
                text: 'Entry:'
            }
            ComboBox{
                Layout.preferredWidth: 207
                id: entries_
            }
            Text {
                id: entryDescription_
                text: ''
            }
        }

        RowLayout {
            id: manualFill_

            Text {
                Layout.preferredWidth: 100
                text: 'Input:'
            }
            ComboBox {
                Layout.preferredWidth: 207
                id: input_
                visible: true
            }
            TextField {
                Layout.preferredWidth: 207
                id: keyword_input_
                visible: false
            }
            Button {
                id: commitInput_
                text: 'Commit'
            }
        }

        Flickable {
            Layout.preferredWidth: 500
            Layout.fillWidth: true
            Layout.preferredHeight: 400
            Layout.fillHeight: true
            clip: true
            TableView {
                id: tableView_
                columnWidthProvider: function (column) { return 100; }
                rowHeightProvider: function (column) { return 30; }
                anchors.fill: parent
                leftMargin: rowsHeader.implicitWidth
                topMargin: columnsHeader.implicitHeight
                delegate: Rectangle {
                    Text {
                        text: display
                        anchors.fill: parent
                        anchors.margins: 10
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                Rectangle { // mask the headers
                    z: 3
                    color: "white"
                    y: tableView_.contentY
                    x: tableView_.contentX
                    width: tableView_.leftMargin
                    height: tableView_.topMargin
                }
                Row {
                    id: columnsHeader
                    z: 2
                    y: tableView_.contentY
                    clip: true
                    Repeater {
                        model: tableView_.columns > 0 ? tableView_.columns : 1
                        Label {
                            color: 'gray'
                            width: tableView_.columnWidthProvider(modelData)
                            height: 35
                            text: windowsUIModel.metadataEditorVisible ? tableView_.model.headerData(modelData, Qt.Horizontal) : ''
                            padding: 10
                            verticalAlignment: Text.AlignVCenter
                            background: Rectangle {color: 'white'}
                        }
                    }
                }
                Column {
                    id: rowsHeader
                    z:2
                    x: tableView_.contentX
                    Repeater {
                        model: tableView_.rows > 0 ? tableView_.rows : 1
                        Label {
                            color: 'gray'
                            width: 60
                            height: tableView_.rowHeightProvider(modelData)
                            text: windowsUIModel.metadataEditorVisible ? tableView_.model.headerData(modelData, Qt.Vertical) : ''
                            padding: 10
                            verticalAlignment: Text.AlignVCenter
                            background: Rectangle {color: 'white'}
                        }
                    }
                }
                ScrollBar.horizontal: ScrollBar {}
                ScrollBar.vertical: ScrollBar {}
            }
        }

        FigureWithToolbar {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.preferredHeight: 300
        }

        GridLayout {
            columns: 6
            
            Repeater
            {
                model: component.columnNames
                CheckBox
                {
                    Layout.preferredHeight: 30
                    text: modelData
                    visible: modelData != 'keywords' ? true : false //keywords can't be plotted, so remove its checkbox
                    Binding on checked
                    {
                        delayed: true
                        value: (modelData in component.showColumn) ? component.showColumn[modelData] : false;
                    }
                    onCheckedChanged: {component.showColumn[modelData] = checked; component.showColumnChanged()}
                }
            }
        }

        RowLayout {
            Button {
                id: save_
                text: "Save"
                palette {
                    button: component.isDirty ? "red" : "lightgray"
                }
            }
        }
    } 
}