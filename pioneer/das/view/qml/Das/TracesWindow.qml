import MPLBackend 1.0
import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.9
import UI2D 1.0


DatasourceWindow {
    id: component

    ////// python API
    property var selection: []
    property alias addToSelection : addToSelection_.text
    property alias addToSelectionSubmit : addToSelectionSubmit_

    property alias useVirtualEchoes : useVirtualEchoes_
    property var imageType : 'amplitude'

    property alias showRaw : showRaw_.checked
    property alias traceProcessing : traceProcessing_.checked
    property alias traceProcessingVisible : traceProcessingBoxes_.visible

    property alias fastTraceSelectionVisible : fastTraceSelection_.visible
    property alias showHighFastTrace: showHighFastTrace_.checked
    property alias showLowFastTrace: showLowFastTrace_.checked

    property alias desaturate : desaturate_.checked
    property alias removeStatic : removeStatic_.checked
    property alias removeStaticVisible: removeStatic_.visible
    property alias realign : realign_.checked
    property alias zeroBaseline : zeroBaseline_.checked
    property alias cutoff : cutoff_.checked
    property alias smoothTrace : smoothTrace_.checked
    ///////////////////////////////
    
    RowLayout {
        Button {
            text: "clear selection"
            onClicked: component.selection = []
        }
        Button {
            id: addToSelectionSubmit_
            text: 'Add to selection'
        }
        TextField {
            id: addToSelection_
            placeholderText: 'Channel'
        }
    }

    RowLayout {
        Button {
            id: useVirtualEchoes_
            visible: false
            text: 'Use virtual echoes'
            checkable: true
        }
        Button {
            text: "Amplitude"
            onClicked: imageType = 'amplitude'
        }
        Button {
            text: "Distance"
            onClicked: imageType = 'distance'
        }
        Button {
            text: "Width"
            onClicked: imageType = 'width'
        }
        Button {
            text: "Skew"
            onClicked: imageType = 'skew'
        }
    }

    RowLayout {
        SmallCheckBox {
            id: showRaw_
            text: "Raw"
            checked: true
        }
        SmallCheckBox {
            id: traceProcessing_
            text: "Processing"
            checked: false
        }
        RowLayout {
            id: traceProcessingBoxes_
            visible: true

            SmallCheckBox {
                id: desaturate_
                text: "Desaturate"
                checked: true
            }
            SmallCheckBox {
                id: removeStatic_
                visible: true
                text: "Static"
                checked: true
            }
            SmallCheckBox {
                id: realign_
                text: "Realign"
                checked: false
            }
            SmallCheckBox {
                id: zeroBaseline_
                text: "Zero"
                checked: true
            }
            SmallCheckBox {
                id: cutoff_
                text: "Cutoff"
                checked: false
            }
            SmallCheckBox {
                id: smoothTrace_
                text: "Smooth"
                checked: true
            }
        }
    }

    RowLayout {
        Text {text: 'Fast Traces: '}
        id: fastTraceSelection_
        visible: false
        
        SmallCheckBox {
            id: showHighFastTrace_
            text: "High"
            checked: true
        }
        SmallCheckBox {
            id: showLowFastTrace_
            text: "Low"
            checked: true
        }
    }
    
    FigureWithToolbar {
        Layout.fillWidth: true
        Layout.fillHeight: true
    }
}