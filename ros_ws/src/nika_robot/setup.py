from setuptools import setup

setup(name='nika_robot', version='0.1.0', packages=['nika_robot'],
      data_files=[('share/ament_index/resource_index/packages', ['resource/nika_robot']),
                  ('share/nika_robot', ['package.xml']),
                  ('share/nika_robot/launch', ['launch/robot.launch.py'])],
      install_requires=['setuptools'],
      entry_points={'console_scripts': [
          'diagnostics = nika_robot.nodes:diagnostics',
          'motion = nika_robot.nodes:motion',
          'odometry = nika_robot.nodes:odometry',
          'server_bridge = nika_robot.bridge:main']})
