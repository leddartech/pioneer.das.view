/*
* Created on Feb 14, 2018
*
* \author: maxime
* \filename: Example1.qml
*/


import QtQuick 2.9
import QtQuick.Controls 2.5
import QtQuick.Layouts 1.11

import Leddar 1.0
import Das 1.0
import UI3D 1.0
import UI2D 1.0

ApplicationWindow {
    id: component
    property int serialNumber : -1
    property var patternSpecs : ({nx: 13, ny: 10, size : 0.028, name: serialNumber})
    property var camSpecs : ({h: 1440, v: 1080, pixel_size : 3.45e-6, f: 3.1e-3})

    width: 600
    height: 800

    function date2str(x, y) {
        var z = {
            M: x.getMonth() + 1,
            d: x.getDate(),
            h: x.getHours(),
            m: x.getMinutes(),
            s: x.getSeconds()
        };
        y = y.replace(/(M+|d+|h+|m+|s+)/g, function(v) {
            return ((v.length > 1 ? "0" : "") + eval('z.' + v.slice(-1))).slice(-2)
        });

        return y.replace(/(y+)/g, function(v) {
            return x.getFullYear().toString().slice(-v.length)
        });
    }

    Item {
        id: content_

        anchors.fill: parent
        Column {
            Text{text: "nImages: " +  calibrator_.nImages}
            Text{text: "specs: " + JSON.stringify(calibrator_.patternSpecs); wrapMode: Text.WordWrap}
            Repeater {
                model: ['yCoverage', 'xCoverage', 'sizeCoverage', 'skewCoverage']
                Row {
                    Text{text: modelData; width: 100}
                    ProgressBar{value: calibrator_[modelData]}
                }
            }
            Button {
                text: "calibrate"
                onClicked: calibrator_.calibrate()
            }
            Button {
                text: "save"
                onClicked: calibrator_.save(name_.text, pos_.text, path_.text)
            }
            Button {
                text: "load"
                onClicked: calibrator_.load(path_.text)
            }

            Column {
                visible: calibrator_.calibrated

                Text{text: "matrix: " +  calibrator_.matrix}

                Text{text: "distortion: " +  calibrator_.distortion}
            }

            TextField{id: name_; text: "flir"}
            TextField{id: pos_; text: "tfl"}
            TextField{id: path_; width: component.width; text: "/nas/cam_intrinsics/" + component.date2str(new Date(), 'yyyy-MM-dd_hh-mm') + "/"}

            Row {
                QImagePainter {
                    imageArray: ROSCalibratorFilter {
                        id: calibrator_;
                        imageArray: PySpinCamera {
                            id: cam0_
                            serialNumber: component.serialNumber
                            assynchronous: true
                        }
                        patternSpecs: component.patternSpecs
                        camSpecs: component.camSpecs
                        name: component.serialNumber.toString()
                    }
                    width: 640
                    height: 480
                    opacity: 0.8
                }
            }
        }
    }
}