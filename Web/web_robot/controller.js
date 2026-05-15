var ros = new ROSLIB.Ros({
  url: 'ws://localhost:9090'
});

ros.on('connection', function () {
  var statusEl = document.getElementById("status");
  statusEl.textContent = "연결됨";
  statusEl.style.color = "green";
  statusEl.setAttribute("data-state", "connected");
});

ros.on('error', function () {
  var statusEl = document.getElementById("status");
  statusEl.textContent = "연결 안됨";
  statusEl.style.color = "red";
  statusEl.setAttribute("data-state", "error");
});

var cmdVel = new ROSLIB.Topic({
  ros: ros,
  name: '/turtle1/cmd_vel',
  messageType: 'geometry_msgs/Twist'
});

function move(linear, angular) {
  var twist = new ROSLIB.Message({
    linear: { x: linear, y: 0, z: 0 },
    angular: { x: 0, y: 0, z: angular }
  });
  cmdVel.publish(twist);
}

document.addEventListener("DOMContentLoaded", function () {

  var initialStatus = document.getElementById("status");
  if (initialStatus && !initialStatus.getAttribute("data-state")) {
    initialStatus.setAttribute("data-state", "connecting");
  }

  document.getElementById("btn-forward")
    .addEventListener("click", function () {
      move(1.0, 0.0);
    });

  document.getElementById("btn-back")
    .addEventListener("click", function () {
      move(-1.0, 0.0);
    });

  document.getElementById("btn-left")
    .addEventListener("click", function () {
      move(0.0, 1.0);
    });

  document.getElementById("btn-right")
    .addEventListener("click", function () {
      move(0.0, -1.0);
    });

  document.getElementById("btn-stop")
    .addEventListener("click", function () {
      move(0.0, 0.0);
    });

});