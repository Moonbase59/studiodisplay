// minifyOnSave, minifierOptions: "charset = utf-8"

// clock.js
//
// A beautiful Javascript canvas clock.
//
// Copyright © 2018 Matthias C. Hormann (@Moonbase59, mhormann@gmx.de)
// Maintained at: https://github.com/Moonbase59/studiodisplay
//
// This file is part of StudioDisplay.
//
// StudioDisplay is free software: you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// StudioDisplay is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with StudioDisplay.  If not, see <http://www.gnu.org/licenses/>.
//
// ---
//
// Diese Datei ist Teil von StudioDisplay.
//
// StudioDisplay ist Freie Software: Sie können es unter den Bedingungen
// der GNU General Public License, wie von der Free Software Foundation,
// Version 3 der Lizenz oder (nach Ihrer Wahl) jeder neueren
// veröffentlichten Version, weiter verteilen und/oder modifizieren.
//
// StudioDisplay wird in der Hoffnung, dass es nützlich sein wird, aber
// OHNE JEDE GEWÄHRLEISTUNG, bereitgestellt; sogar ohne die implizite
// Gewährleistung der MARKTFÄHIGKEIT oder EIGNUNG FÜR EINEN BESTIMMTEN ZWECK.
// Siehe die GNU General Public License für weitere Details.
//
// Sie sollten eine Kopie der GNU General Public License zusammen mit diesem
// Programm erhalten haben. Wenn nicht, siehe <http://www.gnu.org/licenses/>.


// inner variables
var canvas, ctx;
var clockImage;

// draw functions :
function clear() { // clear canvas function
    ctx.canvas.width = document.getElementById('canvas').clientWidth;
    ctx.canvas.height = document.getElementById('canvas').clientHeight;
    ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
}

function drawScene() { // main drawScene function
    clear(); // clear canvas

    // get current time for the timezone given in global "timezoneLong" (IANA format)
    var date = new Date();
    // var hours = date.getHours();
    // var minutes = date.getMinutes();
    // var seconds = date.getSeconds();

    // use locale-aware parts formatter to get values
    var formatter = new Intl.DateTimeFormat(locale, {
      hour: '2-digit',
      hour12: false,
      minute: '2-digit',
      second: '2-digit',
      timeZone: timezoneLong
    });
    // deconstruct localized time to find hours/mins/secs parts
    // needed because local time strings contain unexpected literals
    var dateString = formatter.formatToParts(date).map(({type, value}) => {
      switch (type) {
        case 'dayPeriod': return `<b>${value}</b>`;
        case 'hour':
          hours = Number(value);
          return value;
        case 'minute':
          minutes = Number(value);
          return value;
        case 'second':
          seconds = Number(value);
          return value;
        default : return value;
      }
    }).reduce((string, part) => string + part);
    // console.log(hours, minutes, seconds, dateString);

    hours = hours > 12 ? hours - 12 : hours;
    var hour = hours + minutes / 60;
    var minute = minutes + seconds / 60;

    var clockRadius = Math.min(canvas.width, canvas.height) / 2;

    // some thicknesses and lengths we will use often
    // width of dots & bars, max. width of hand
    var dotWidth = clockRadius * 0.04;
    // length of 5-minute bars, overhang of hands, font size
    var barLength = clockRadius * 0.15;
    // get the current canvas color and use it (except the seconds hand which is always red)
    var clockColor = window.getComputedStyle(canvas, null).getPropertyValue('color');
    // length of hands
    var secondsCircle = clockRadius * 0.9;
    var minutesCircle = clockRadius * 0.85;
    var hoursCircle = clockRadius * 0.5;

    // save current context
    ctx.save();

    // translate origin (0,0) to be in the center
    ctx.translate(canvas.width / 2, canvas.height / 2);

    // draw clock image (as background)
    //ctx.fillStyle = '#000';
    ctx.fillStyle = clockColor;

    // draw minute dots
    for (var n = 0; n <= 59; n++) {
      if (n % 5 == 0) continue; // skip 5-minute bars
      var theta = (n - 15) * (Math.PI * 2) / 60;
      var x = clockRadius * 0.9 * Math.cos(theta);
      var y = clockRadius * 0.9 * Math.sin(theta);
      ctx.beginPath();
      ctx.arc(x, y, dotWidth / 2, 0, 2*Math.PI);
      ctx.fill();
    }
    // draw 5-minute bars (from center & rotate canvas)
    var rLength = clockRadius * 0.15;
    var rWidth = clockRadius * 0.04;
    var x = 0;
    var y = 0;
    for (var n = 0; n <= 11; n++) {
      ctx.save();
      ctx.rotate((n - 3)*30 * Math.PI / 180); // degress to radians
      ctx.fillRect(x-dotWidth/2, y-barLength/2-clockRadius*0.9, dotWidth, barLength);
      ctx.restore();
    }

    ctx.beginPath();

    // draw numbers
    ctx.font = Math.round(barLength).toString() + 'px sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (var n = 1; n <= 12; n++) {
        var theta = (n - 3) * (Math.PI * 2) / 12;
        var x = clockRadius * 0.7 * Math.cos(theta);
        var y = clockRadius * 0.7 * Math.sin(theta);
        ctx.fillText(n, x, y);
    }

    // draw hour
    ctx.save();
    var theta = (hour - 3) * 2 * Math.PI / 12;
    ctx.rotate(theta);
    ctx.beginPath();
    ctx.moveTo(-barLength/2, -dotWidth);
    ctx.lineTo(-barLength/2, dotWidth);
    ctx.lineTo(hoursCircle, dotWidth/3);
    ctx.lineTo(hoursCircle, -dotWidth/3);
    ctx.fill();
    ctx.restore();

    // draw minute
    ctx.save();
    var theta = (minute - 15) * 2 * Math.PI / 60;
    ctx.rotate(theta);
    ctx.beginPath();
    ctx.moveTo(-barLength/2, -dotWidth);
    ctx.lineTo(-barLength/2, dotWidth);
    ctx.lineTo(minutesCircle, dotWidth/3);
    ctx.lineTo(minutesCircle, -dotWidth/3);
    ctx.fill();
    ctx.restore();

    // draw second
    ctx.save();
    var theta = (seconds - 15) * 2 * Math.PI / 60;
    ctx.rotate(theta);
    ctx.beginPath();
    ctx.moveTo(-barLength, -dotWidth/2);
    ctx.lineTo(-barLength, dotWidth/2);
    ctx.lineTo(secondsCircle, dotWidth/4);
    ctx.lineTo(secondsCircle, -dotWidth/4);
    ctx.fillStyle = '#a00';
    ctx.fill();
    ctx.restore();

    ctx.restore();

    // update current date, if it exists
    var el = document.getElementById("clock/date");
    var dateoptions = {
      weekday: "long", // narrow/short/long
      year: "numeric", // numeric/2-digit
      month: "2-digit", // numeric/2-digit/narrow/short/long
      day: "2-digit", // numeric/2-digit
      timeZone: timezoneLong
    };
    if (el) {
      el.innerHTML = date.toLocaleString(locale, dateoptions);
    }
}

// initialization
document.addEventListener("DOMContentLoaded", function(event) {
    canvas = document.getElementById('canvas');
    ctx = canvas.getContext('2d');
    setInterval(drawScene, 1000); // loop drawScene
});
