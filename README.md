# ROSA Summit - LLM Robot Kontrol (Gemma 3 / OpenRouter)

Bu proje, bir Summit XL robotunu simülasyon ortamında Yapay Zeka (LLM) ile konuşarak kontrol etmenizi sağlar. En son güncellemelerle sistem **Manual JSON Parsing** moduna geçirilmiş ve OpenRouter üzerindeki en yeni modellerle (Gemma 3) uyumlu hale getirilmiştir.

---

## 🇹🇷 Türkçe Kullanım Kılavuzu (Hızlı Başlat)

### 1. Kurulum ve Hazırlık
1.  **API Anahtarı:**
    `api-key.txt` dosyasının içine OpenRouter API anahtarınızı (`sk-or-...`) yapıştırıp kaydedin.
2.  **Docker İmajını Oluşturma:**
    ```bash
    docker build -t llm-robot-control:latest .
    ```

### 2. Sistemi Başlatma (Adım Adım)
1.  **Konteyneri Çalıştırın:**
    ```bash
    docker run -it --rm \
        --gpus all \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -e NVIDIA_DRIVER_CAPABILITIES=all \
        -e DISPLAY=$DISPLAY \
        -e XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR \
        -e XAUTHORITY=$XAUTH \
        --device /dev/dri \
        --name robotcontrol \
        llm-robot-control:latest \
        /bin/bash
    ```
2.  **Kütüphaneleri Düzeltin (Hata Alınca):**
    ```bash
    pip3 uninstall -y jpl-rosa langchain langchain-community langchain-core langchain-openai --break-system-packages
    pip3 install jpl-rosa langchain-openai --break-system-packages
    ```
3.  **Güncel Kodu İçeri Aktarın (Masaüstü Terminalinden):**
    ```bash
    docker cp /home/enes/Desktop/llm-robot-control/project_source/rosa_summit/rosa_summit.py robotcontrol:/home/ros/rap/Gruppe2/project_source/rosa_summit/rosa_summit.py
    ```
4.  **Simülasyonu ve Ajanı Başlatın:**
    ```bash
    # Konteyner içinde:
    ros2 launch rosa_summit summit.launch.py
    ```
    ```bash
    # Konteyner içinde:
    python3 /rap/Gruppe2/rosa_summit/rosa_summit.py
    ```

---

## 🇺🇸 English Technical Documentation

This package provides a ROS2 interface for controlling a simulated Summit XL robot using a Large Language Model (LLM) through the ROSA framework. It is intended to be used inside a Container running a specific ROS 2 image (`robopaas/rap-jazzy:cuda12.5.0`).

### Setup
1.  **Clone the repository:**
    Clone this repository into the `~/rap/Gruppe2` directory inside your `rap-jazzy` container.
2.  **Initialize the environment:**
    Source the `init.sh` script to set up the ROS2 workspace and install dependencies.
    ```bash
    source ~/rap/Gruppe2/init.sh
    ```

### Dependencies
All required ROS 2 packages and Python libraries are automatically installed when you source the `init.sh` script. 
- **ROS 2 Packages:** Clones `m-explore-ros2`, builds Colcon workspace.
- **Python Packages:** Installs `jpl-rosa`, `langchain-openai`, etc.

### Running the Simulation
- **With SLAM (Mapping):**
  ```bash
  ros2 launch rosa_summit summit.launch.py slam:=True
  ```
- **With a pre-existing map (Navigation):**
  ```bash
  ros2 launch rosa_summit summit.launch.py slam:=False
  ```

### Available LLM Actions
The LLM can control the robot using the following actions:
- `send_vel(velocity: float)`: Sets forward velocity.
- `stop()`: Stops the robot.
- `toggle_auto_exploration(resume_exploration: bool)`: Starts/stops mapping.
- `navigate_to_pose(x, y, z, w)`: Moves to absolute coordinates.
- `navigate_relative(x, y, z, w)`: Moves relative to robot.
- `save_map(map_name: str)`: Saves SLAM map.
- `list_saved_maps()`: Lists saved maps.
- `get_location_names()`: Lists predefined locations.
- `navigate_to_location_by_name(location_name: str)`: Goes to names like 'kitchen', 'gym'.

---

### Simulation World
The simulation environment uses a modified version of the [AWS Robomaker Small House World](https://github.com/aws-robotics/aws-robomaker-small-house-world), optimized for ROS 2 Jazzy and the Summit XL robot.

### Demo Videos
- **Mapping:** [Link to mapping.mp4](./demo/mapping.mp4)
- **Navigation:** [Link to navigation.mp4](./demo/navigation.mp4)
