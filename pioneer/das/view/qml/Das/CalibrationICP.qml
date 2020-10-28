import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.9


ColumnLayout {
    id: component

    property string key : "" // support for wait_key()
    property alias modeComboBox        : modeComboBox_
    property alias correspDistMax      : correspDistMax_.text
    property alias nbIterMax           : nbIterMax_.text
    property alias allFrames           : allFrames_
    property alias sourceFrameNo       : sourceFrameNo_.text
    property alias runicp              : runicp_
    property alias resultx             : resultx_.text
    property alias resulty             : resulty_.text
    property alias resultz             : resultz_.text
    property alias resultrx            : resultrx_.text
    property alias resultry            : resultry_.text
    property alias resultrz            : resultrz_.text
    property alias applyicp            : applyicp_
    
    readonly property var result : ({x: parseFloat(resultx), y: parseFloat(resulty), z: parseFloat(resultz), rx: parseFloat(resultrx), ry: parseFloat(resultry), rz: parseFloat(resultrz)})
    
    property bool rxVisible: true
    property bool ryVisible: true
    property bool scaleVisible: false
   
    Text {text: 'Iterative closest point (ICP) registration'}
    RowLayout {      
        Text {text: 'icp mode: '}
        ComboBox {id: modeComboBox_}
    }
    RowLayout {
        Text {text: 'max correspondence distance: '}
        TextField {
            id: correspDistMax_
            text: "0.50"
            Layout.preferredHeight: 25
            Layout.preferredWidth: 50
            font.pointSize: 8
        }          
    }
    RowLayout {
        Text {text: 'max iterations: '}
        TextField {
            id: nbIterMax_
            text: "35"
            Layout.preferredHeight: 25
            Layout.preferredWidth: 50
            font.pointSize: 8
        }       
    }
    RowLayout {
        Text {text: 'Frames: '}
        CheckBox {
            id: allFrames_
            text: "All"
            checked: true
        }
        Text {text: '  Enter source frame number: '}
        TextField {
            id: sourceFrameNo_
            text: "1"
            Layout.preferredHeight: 25
            Layout.preferredWidth: 50
            font.pointSize: 8
        }       
    }
    RowLayout {
        Button {
            id: runicp_
            text: "icp!"
        }
        Text {text: 'Results:  '}
        Text {text: 'x='}
        TextField {
            id: resultx_
            text: "0"
            enabled: false
            Layout.preferredHeight: 25
            Layout.preferredWidth: 100
            font.pointSize: 8
        } 
        Text {text: 'y='}
        TextField {
            id: resulty_
            text: "0"
            enabled: false
            Layout.preferredHeight: 25
            Layout.preferredWidth: 100
            font.pointSize: 8
        }
        Text {text: 'z='}
        TextField {
            id: resultz_
            text: "0"
            enabled: false
            Layout.preferredHeight: 25
            Layout.preferredWidth: 100
            font.pointSize: 8
        }
        Text {text: 'rx='}
        TextField {
            id: resultrx_
            text: "0"
            enabled: false
            Layout.preferredHeight: 25
            Layout.preferredWidth: 100
            font.pointSize: 8
        }
        Text {text: 'ry='}
        TextField {
            id: resultry_
            text: "0"
            enabled: false
            Layout.preferredHeight: 25
            Layout.preferredWidth: 100
            font.pointSize: 8
        }
        Text {text: 'rz='}
        TextField {
            id: resultrz_
            text: "0"
            enabled: false
            Layout.preferredHeight: 25
            Layout.preferredWidth: 100
            font.pointSize: 8
        }
        Button {
            id: applyicp_
            text: "apply"
        }
    }
}
