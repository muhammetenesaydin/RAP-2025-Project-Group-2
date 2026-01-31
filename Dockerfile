FROM robopaas/rap-jazzy:cuda12.5.0

COPY . /home/ros/rap/Gruppe2
# api-key.txt should be copied manually via 'docker cp' to preserve security
RUN bash -c "source ~/rap/Gruppe2/init.sh"
ENV GZ_SIM_RESOURCE_PATH=/home/ros/rap/Gruppe2/project_source/world/models

# Build workspace
RUN /bin/bash -c "source /opt/ros/${ROS_DISTRO}/setup.bash && cd ~/colcon_ws && colcon build"

# Create entrypoint script
RUN sudo bash -c "touch /ros_entrypoint.sh && chown $USER /ros_entrypoint.sh && chmod +x /ros_entrypoint.sh"
RUN cat > /ros_entrypoint.sh <<'EOF'
#!/bin/bash
set -e

# setup ros2 environment
source "/opt/ros/$ROS_DISTRO/setup.bash"
source "/home/ros/colcon_ws/install/setup.bash"

exec "$@"
EOF

ENTRYPOINT ["/ros_entrypoint.sh"]
