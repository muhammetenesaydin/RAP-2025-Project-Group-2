from langchain.agents import tool
import os
import pathlib
import time
import subprocess
import requests
import json
from typing import Tuple
from geometry_msgs.msg import Twist
from std_msgs.msg import Bool
from nav2_msgs.action import NavigateToPose
import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter

# Global değişkenlerin tanımlanması
node = None
vel_publisher = None
explore_publisher = None
navigate_to_pose_action_client = None


def execute_ros_command(command: str) -> Tuple[bool, str]:
    """
    Bir ROS2 komutunu terminal üzerinden çalıştırır.
    """
    cmd = command.split(" ")
    if len(cmd) < 2 or cmd[0] != "ros2":
        raise ValueError(f"'{command}' geçerli bir ROS2 komutu değil.")

    try:
        output = subprocess.check_output(command, shell=True).decode()
        return True, output
    except Exception as e:
        return False, str(e)


def _get_maps_dir() -> str:
    """Harita dosyalarının kaydedileceği dizini döndürür."""
    maps_dir = "/home/ros/rap/Gruppe2/maps"
    pathlib.Path(maps_dir).mkdir(parents=True, exist_ok=True)
    return maps_dir


# Robot için önceden tanımlanmış sabit konumlar (Koordinat ve Yönelim değerleri)
LOCATIONS = {
    "gym": {
        "position": {"x": 1.9517535073729964, "y": 4.359393291484201, "z": 0.0},
        "orientation": {"x": 1.6302566310137402e-08, "y": 2.9703213238180324e-08, "z": -0.07945176214102775, "w": 0.9968387118750377},
    },
    "kitchen": {
        "position": {"x": 7.353217566768062, "y": -3.458078519447155, "z": 0.0},
        "orientation": {"x": 1.611930208234276e-08, "y": 2.980589390984495e-08, "z": -0.07325043342926793, "w": 0.997313578571165},
    },
    "living room": {
        "position": {"x": 1.084137940689, "y": -0.383112079564818, "z": 0.0},
        "orientation": {"x": 3.316520260505064e-08, "y": 6.931688679143018e-09, "z": -0.8089064668855616, "w": 0.5879373502599718},
    },
    "office": {
        "position": {"x": -4.9521764504716765, "y": -3.573205806403106, "z": 0.0},
        "orientation": {"x": -3.238093524948138e-08, "y": 9.961584542476143e-09, "z": 0.9923116132365216, "w": -0.1237645435329962},
    },
    "bedroom": {
        "position": {"x": -4.002267652240865, "y": -0.060121871401907084, "z": 0.0},
        "orientation": {"x": -2.1636165143756515e-08, "y": 2.6069771799291994e-08, "z": 0.8980250477792399, "w": 0.43994433007039957},
    },
}


@tool
def send_vel(velocity: float) -> str:
    """Robotun ileri/geri hızını ayarlar."""
    global vel_publisher
    twist = Twist()
    twist.linear.x = velocity
    vel_publisher.publish(twist)
    return "Hız %s olarak ayarlandı." % velocity


@tool
def stop() -> str:
    """Robotun tüm hareketini durdurur."""
    global vel_publisher
    twist = Twist()
    vel_publisher.publish(twist)
    return "Robot durduruldu."


@tool
def toggle_auto_exploration(resume_exploration: bool) -> str:
    """Otonom keşif modunu (explore_lite) başlatır veya durdurur."""
    global explore_publisher
    msg = Bool()
    msg.data = resume_exploration
    explore_publisher.publish(msg)
    return "Otonom keşif " + ("başlatıldı." if resume_exploration else "durduruldu.")


@tool
def navigate_to_pose(x: float, y: float, z_orientation: float, w_orientation: float) -> str:
    """
    YOL PLANLAMA BURADA BAŞLAR:
    Robotu harita üzerindeki kesin bir koordinata gönderir. Nav2 (Navigation Stack) 
    bu hedefi aldığında, mevcut konumdan hedefe engel aşarak giden bir rota planlar.
    """
    global navigate_to_pose_action_client, node

    goal_msg = NavigateToPose.Goal()
    goal_msg.pose.header.frame_id = "map"
    goal_msg.pose.header.stamp = node.get_clock().now().to_msg()
    goal_msg.pose.pose.position.x = x
    goal_msg.pose.pose.position.y = y
    goal_msg.pose.pose.orientation.z = z_orientation
    goal_msg.pose.pose.orientation.w = w_orientation

    # Asenkron olarak hedefi Nav2 stack'ine gönderiyoruz.
    # Gerçek yol planlama algoritması Nav2 düğümü (Planner Server) içinde çalışır.
    navigate_to_pose_action_client.send_goal_async(goal_msg)
    return f"Hedef koordinatlara gönderildi: x: {x}, y: {y}"


@tool
def navigate_relative(x: float, y: float, z_orientation: float, w_orientation: float) -> str:
    """Robotun bulunduğu konuma göre bağıl hareket etmesini sağlar."""
    global navigate_to_pose_action_client, node
    goal_msg = NavigateToPose.Goal()
    goal_msg.pose.header.frame_id = "base_link"
    goal_msg.pose.header.stamp = node.get_clock().now().to_msg()
    goal_msg.pose.pose.position.x = x
    goal_msg.pose.pose.position.y = y
    goal_msg.pose.pose.orientation.z = z_orientation
    goal_msg.pose.pose.orientation.w = w_orientation
    navigate_to_pose_action_client.send_goal_async(goal_msg)
    return f"Bağıl hedef gönderildi: x: {x}, y: {y}"


@tool
def save_map(map_name: str) -> str:
    """Mevcut haritayı bir dosya olarak kaydeder."""
    maps_dir = _get_maps_dir()
    filepath_prefix = os.path.join(maps_dir, map_name)
    cmd = f"ros2 run nav2_map_server map_saver_cli -f '{filepath_prefix}' --ros-args -r map:=/summit/map"
    success, output = execute_ros_command(cmd)
    return f"Harita kaydedildi: {map_name}" if success else f"Hata: {output}"


@tool
def list_saved_maps() -> str:
    """Kaydedilmiş tüm haritaları listeler."""
    maps_dir = _get_maps_dir()
    try:
        files = os.listdir(maps_dir)
        map_files = [f[:-5] for f in files if f.endswith(".yaml")]
        return f"Mevcut haritalar: {', '.join(map_files)}"
    except Exception as e:
        return f"Hata: {e}"


@tool
def get_location_names() -> str:
    """Önceden kaydedilmiş konum isimlerini getirir."""
    return f"Kayıtlı konumlar: {', '.join(LOCATIONS.keys())}"


@tool
def navigate_to_location_by_name(location_name: str) -> str:
    """
    YOL PLANLAMA BURADA TETİKLENİR:
    İsimle verilen konumu alıp koordinatlarını `NavigateToPose` mesajına paketler.
    Bu mesaj Nav2 stack'ine gittiğinde yol planlayıcı (Planner) devreye girer.
    """
    global navigate_to_pose_action_client, node
    location_name_lower = location_name.lower()
    if location_name_lower not in LOCATIONS:
        return f"'{location_name}' bulunamadı."

    loc_data = LOCATIONS[location_name_lower]
    goal_msg = NavigateToPose.Goal()
    goal_msg.pose.header.frame_id = "map"
    goal_msg.pose.header.stamp = node.get_clock().now().to_msg()
    goal_msg.pose.pose.position.x = loc_data["position"]["x"]
    goal_msg.pose.pose.position.y = loc_data["position"]["y"]
    goal_msg.pose.pose.orientation.z = loc_data["orientation"]["z"]
    goal_msg.pose.pose.orientation.w = loc_data["orientation"]["w"]

    navigate_to_pose_action_client.send_goal_async(goal_msg)
    return f"'{location_name}' konumuna yol planlanıyor..."


def main():
    global node, vel_publisher, explore_publisher, navigate_to_pose_action_client
    print("ROSA Summit Başlatılıyor...")

    # ROS2 rclpy kütüphanesini başlatıyoruz
    rclpy.init()
    sim_time_param = Parameter("use_sim_time", rclpy.Parameter.Type.BOOL, True)
    node = rclpy.create_node("rosa_summit_node", parameter_overrides=[sim_time_param])

    # Yayıncılar (Publishers) ve Eylem İstemcileri (Action Clients)
    vel_publisher = node.create_publisher(Twist, "/summit/cmd_vel", 10)
    explore_publisher = node.create_publisher(Bool, "/summit/explore/resume", 10)
    navigate_to_pose_action_client = ActionClient(node, NavigateToPose, "/summit/navigate_to_pose")

    # OpenRouter API Anahtarı Okuma
    try:
        with open("/home/ros/rap/Gruppe2/api-key.txt", "r") as f:
            lines = f.read().strip().split("\n")
            api_key = lines[-1] if not lines[-1].startswith("#") else lines[0]
    except Exception as e:
        print(f"API Anahtarı Okunamadı: {e}")
        return

    # Yapay Zeka için Sistem Prompt'u (Yapay Zekanın Kimliği ve Kuralları)
    system_prompt = f"""Summit XL robotu için kontrolcüsün. Görevin kullanıcı isteklerini JSON komutlarına çevirmektir.
    Kayıtlı konumlar: {', '.join(LOCATIONS.keys())}
    
    KURALLAR:
    - SADECE JSON objesi döndür.
    - Açıklama veya konuşma metni EKLEME.
    - Mevcut aksiyonlar: 'navigate_to_location', 'stop', 'move_forward', 'move_backward'.
    
    Örnek Format:
    - "mutfağa git" -> {{"action": "navigate_to_location", "params": {{"name": "kitchen"}}}}
    """

    print("Çıkmak için 'exit' veya 'quit' yazın.")

    while True:
        user_input = input("\nKomut girin: ")
        if user_input.lower() in ["exit", "quit"]:
            break

        print("LLM Komutu Çözümleniyor (Raw HTTP)...")
        try:
            # Gemma/OpenRouter için sistem ve kullanıcı mesajlarını birleştiriyoruz
            messages_payload = f"{system_prompt}\n\nKullanıcı İsteği: {user_input}"
            
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/jpl-rosa",
                    "X-Title": "ROSA Summit Agent",
                },
                data=json.dumps({
                    "model": "google/gemma-3n-e2b-it:free",
                    "messages": [
                        {"role": "user", "content": messages_payload}
                    ]
                })
            )
            
            res_data = response.json()
            if "error" in res_data:
                print(f"API Hatası: {res_data['error']}")
                continue
                
            content = res_data['choices'][0]['message']['content'].strip()
            
            # JSON kısmını ayıklama
            json_content = content
            if "```json" in json_content:
                json_content = json_content.split("```json")[1].split("```")[0].strip()
            elif "```" in json_content:
                json_content = json_content.split("```")[1].split("```")[0].strip()
            
            try:
                cmd = json.loads(json_content)
                action = cmd.get("action")
                params = cmd.get("params", {})

                # JSON'da gelen komuta göre Python fonksiyonlarını tetikleme
                if action == "navigate_to_location":
                    print(res_data['choices'][0]['message']['content']) # Düşünce sürecini görme
                    res = navigate_to_location_by_name(params.get("name"))
                    print(res)
                elif action == "stop":
                    res = stop()
                    print(res)
                elif action == "move_forward":
                    res = send_vel(params.get("velocity", 0.5))
                    print(res)
                elif action == "move_backward":
                    res = send_vel(-params.get("velocity", 0.5))
                    print(res)
                else:
                    print(f"Bilinmeyen aksiyon: {action}")
            except Exception as json_err:
                print(f"JSON Çözümleme Hatası: {json_err}\nLLM Cevabı: {content}")

        except Exception as e:
            print(f"API Çağrı Hatası: {e}")

    print("Görüşmek üzere!")


if __name__ == "__main__":
    main()