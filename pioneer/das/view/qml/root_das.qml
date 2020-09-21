import MPLBackend 1.0
import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Window 2.7
import QtQuick.Layouts 1.9
import UI3D 1.0
import Leddar 1.0

import Das 1.0
import Misc 1.0 //contains Utils.js

ApplicationWindow {
    id: component

    //////////////// Python API ////////////////////////////
    property string key: ''
    
    property var rgb              : []
    property var scalars          : []
    property var traces           : []
    property var viewports        : []
    property var customViewports  : []
    property var bboxes2D         : []
    property var seg2D            : []
    property var bboxes3D         : []
    property var seg3D            : []
    property var lanes            : []

    property var sensors          : ({})
    property var datasources      : ({})
    property var synchDatasources : ({})
    property var customDatasources: ({})
    property bool isLive          : false

    property alias cursor: player_.cursor
    property alias cursors: player_.cursors
    property alias recording: player_.recording
    signal clicked()

    property int nIndices: 0
    
    readonly property var rgbWindows            : Utils.listOfInstances(rgbWindows_)
    readonly property var scalarsWindows        : Utils.listOfInstances(scalarsWindows_)
    readonly property var tracesWindows         : Utils.listOfInstances(tracesWindows_)
    readonly property var viewportWindows       : Utils.listOfInstances(viewportWindows_)
    readonly property var customViewportWindows : Utils.listOfInstances(customViewportWindows_) 

    readonly property var allWindows            : Utils.merge(rgbWindows, scalarsWindows, tracesWindows, viewportWindows, customViewportWindows)
    
    readonly property alias calibWindow         : calib_
    readonly property alias metadataWindow      : metadata_
   
    /////////////////// End Python API /////////////////////
    
    onClosing: {
        for (var w in allWindows)
            allWindows[w].close()
    } 

    readonly property QtObject windowsUIModel: QtObject {
        id: model_
        function addModel(windows) {
            var models = {};
            for (var ds in windows)
                models[ds] = {ds: ds, window: windows[ds], visible: false};
            return models
        }
        function setValue(ds, property, value) {
            // changing a value inside an object (a.k.a. dict) of an array (a.k.a. list) does not trigger qml notification signal
            // this is an unfortunate qml limitation
            model[ds][property] = value;
            model_.modelChanged();
        }
        readonly property var model : addModel(allWindows)
        property bool calibEditorVisible: false
        property bool metadataEditorVisible: false
    }
    /// end of interactive public API

    height: player_.implicitHeight
    width: player_.implicitWidth
    
    Player {
        id: player_
        Keys.onPressed: component.key = event.text
        focus: true
        isLive           : component.isLive
        nIndices         : component.nIndices           
        sensors          : component.sensors           
        synchDatasources : component.synchDatasources
        customDatasources : component.customDatasources           
        windowsUIModel   : component.windowsUIModel           
        allWindows       : component.allWindows           

        anchors.topMargin: 10
        anchors.fill: parent

        saveSlices.onClicked: component.clicked()
    }
    CalibrationEditor {
        id: calib_
        visible: component.windowsUIModel.calibEditorVisible
        windowsUIModel: component.windowsUIModel
    }
    MetadataEditor {
        id: metadata_
        visible: component.windowsUIModel.metadataEditorVisible
        windowsUIModel: component.windowsUIModel
    }
    
    Instantiator {
        id: rgbWindows_
        model: component.rgb
        delegate: RGBDatasourceWindow {
            datasources: component.datasources
            windowsUIModel: component.windowsUIModel

            //for pcl projection:
            viewports: component.viewports
            
            bboxes2D: component.bboxes2D
            seg2D: component.seg2D
            bboxes3D: component.bboxes3D
            seg3D: component.seg3D
            lanes: component.lanes
        }
    }

    Instantiator {
        id: scalarsWindows_
        model: component.scalars
        delegate: ScalarsWindow {
            datasources: component.datasources
            windowsUIModel: component.windowsUIModel
        }
    }

    Instantiator {
        id: tracesWindows_
        model: component.traces
        delegate: TracesWindow {
            datasources: component.datasources
            windowsUIModel: component.windowsUIModel
        }
    }

    Instantiator {
        id: viewportWindows_
        model: component.viewports
        delegate: ViewportWindow {
            id: vpWindow_
            datasources: component.datasources
            windowsUIModel: component.windowsUIModel
            viewports: component.viewports
            bboxes3D: component.bboxes3D
            seg3D: component.seg3D
            lanes: component.lanes
        }
    }

    Instantiator {
        id: customViewportWindows_
        model: component.customViewports
        delegate: DatasourceWindow {
            datasources: component.customDatasources
            windowsUIModel: component.windowsUIModel

            readonly property alias viewport: viewport_ //API
            
            Viewport {
                id: viewport_
                Layout.fillWidth: true
                Layout.fillHeight: true
                actors: Actors{}
            }
        }
    }
}