import QtQuick 2.9
import QtQuick.Controls 2.5
import MPLBackend 1.0
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import Das 1.0

DatasourceWindow {
    id: component

    property alias controls      : controls_
    property alias viewports     : controls_.viewports
    property alias showActor     : controls_.showActor
    property alias bboxes2D      : controls_.bboxes2D
    property alias bboxes3D      : controls_.bboxes3D
    property alias seg2D         : controls_.seg2D
    property alias seg3D         : controls_.seg3D
    property alias lanes         : controls_.lanes

    PCLUI2D {
        id: controls_

        sensorName : component.sensorName
        Layout.fillHeight: true
        Layout.preferredWidth: component.width

        hasReferential: {
            var m = {};
            for(var i in component.viewports) {
                var vp = component.viewports[i]
                m[vp] = {hasReferential: true} //until proven wrong
            }
            return m;
        }
        showImageSettings: true
    }

    FigureWithToolbar {
        Layout.fillWidth: true
        Layout.fillHeight: true
    }
}
