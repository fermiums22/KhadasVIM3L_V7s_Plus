#!/usr/bin/env bash
# Run on the confirmed VIM3L, after installing Ubuntu and configuring networking/SSH.
set -Eeuo pipefail
[[ $EUID == 0 ]] || { echo 'Run with sudo'; exit 1; }
source /etc/os-release
[[ $ID == ubuntu && $VERSION_ID == 24.04 && $(dpkg --print-architecture) == arm64 ]] || {
  echo 'Requires Ubuntu 24.04 ARM64'; exit 1;
}
model=$(tr -d '\0' </proc/device-tree/model)
[[ $model == *VIM3L* ]] || { echo "Unexpected board: $model"; exit 1; }
if ip -o link show | grep -Eiq '(tun[0-9]|tap[0-9]|wg[0-9]|tailscale|vpn)'; then
  echo 'VPN interface detected; verify direct networking before installation'; exit 1
fi
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY all_proxy
export DEBIAN_FRONTEND=noninteractive
export LANG=C.UTF-8
apt-get -o Acquire::http::Proxy=DIRECT -o Acquire::https::Proxy=DIRECT update
apt-get -o Acquire::http::Proxy=DIRECT -o Acquire::https::Proxy=DIRECT install -y \
  ca-certificates curl software-properties-common locales openssh-server unattended-upgrades
locale-gen en_US.UTF-8
add-apt-repository -y universe
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT
curl --noproxy '*' --fail --location --proto '=https' \
  https://api.github.com/repos/ros-infrastructure/ros-apt-source/releases/latest -o "$stage/release.json"
version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["tag_name"])' "$stage/release.json")
[[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo 'Unexpected ROS source release'; exit 1; }
curl --noproxy '*' --fail --location --proto '=https' \
  "https://github.com/ros-infrastructure/ros-apt-source/releases/download/${version}/ros2-apt-source_${version}.noble_all.deb" \
  -o "$stage/ros2-apt-source.deb"
dpkg -i "$stage/ros2-apt-source.deb"
apt-get -o Acquire::http::Proxy=DIRECT -o Acquire::https::Proxy=DIRECT update
apt-get -o Acquire::http::Proxy=DIRECT -o Acquire::https::Proxy=DIRECT upgrade -y
apt-get -o Acquire::http::Proxy=DIRECT -o Acquire::https::Proxy=DIRECT install -y \
  ros-jazzy-ros-base ros-jazzy-launch-ros python3-colcon-common-extensions python3-paho-mqtt
id nika-robot >/dev/null 2>&1 || useradd --system --home-dir /var/lib/nika-robot --shell /usr/sbin/nologin nika-robot
source_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
install -d /opt/nika-robot/ros_ws/src /etc/nika-robot
cp -a "$source_dir/ros_ws/src/nika_robot" /opt/nika-robot/ros_ws/src/
install -m 0755 "$source_dir/start.sh" /opt/nika-robot/start.sh
install -m 0755 "$source_dir/verify.sh" /opt/nika-robot/verify.sh
install -m 0644 "$source_dir/systemd/nika-robot.service" /etc/systemd/system/nika-robot.service
install -m 0644 "$source_dir/config/robot.env.example" /etc/nika-robot/robot.env.example
set +u
source /opt/ros/jazzy/setup.bash
cd /opt/nika-robot/ros_ws
python3 -c "from catkin_pkg.package import parse_package; assert parse_package('src/nika_robot/package.xml').get_build_type() == 'ament_python'"
colcon build --event-handlers console_direct+
set -u
systemctl enable --now ssh
systemctl daemon-reload
systemctl enable nika-robot
if [[ -f /etc/nika-robot/robot.env && -f /etc/nika-robot/mqtt-password ]]; then
  systemctl restart nika-robot
else
  echo 'Installed. Configure /etc/nika-robot/robot.env and mqtt-password before starting.'
fi
