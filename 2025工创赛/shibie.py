# Untitled - By: LQL - 周四 3月 13 2025
import sensor, image, time
import lcd
from hiwonder import hw_uart

# 初始化LCD屏幕
lcd.init()

# 初始化摄像头
sensor.reset()
# 设置像素格式为RGB565
sensor.set_pixformat(sensor.RGB565)
# 设置帧大小为QVGA (320x240)
sensor.set_framesize(sensor.QVGA)
# 跳过前2000毫秒的帧，让摄像头稳定
sensor.skip_frames(time=2000)
# 关闭自动增益，保证颜色识别的稳定性
sensor.set_auto_gain(False)
# 关闭自动白平衡，保证颜色识别的稳定性
sensor.set_auto_whitebal(False)

# 定义颜色阈值
# 红色阈值，由于红色在HSV空间不连续，这里用一个区间表示
red_threshold = [(100, 0, 6, 59, -3, 62)]
# 绿色阈值
green_threshold = [(30, 100, -64, -8, -32, 32)]
# 蓝色阈值
blue_threshold = [(86, 23, -2, 49, -88, -11)]

# 将所有颜色阈值存放在一个列表中
color_thresholds = [red_threshold, green_threshold, blue_threshold]
# 定义颜色名称，与阈值列表顺序对应
color_names = ["Red", "Green", "Blue"]
# 定义颜色代码，与阈值列表顺序对应
color_codes = [1, 2, 3]
# 定义颜色的RGB值，用于在图像上绘制
color_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255)]

# 初始化时钟对象，用于计算帧率
clock = time.clock()
# 记录上一次发送数据的时间
last_send_time = time.ticks_ms()
# 发送数据间隔，单位为毫秒，即 0.4 秒
SEND_INTERVAL = 400

# 初始化串口
serial = hw_uart()

while True:
    # 更新时钟，记录帧率
    clock.tick()
    # 拍摄一张图像
    img = sensor.snapshot()

    # 获取图像的宽度和高度
    width = img.width()
    height = img.height()

    # 计算图像中心的坐标
    center_x = width // 2
    center_y = height // 2

    # 在图像中心绘制一个白色的十字线，标记中心位置
    cross_size = 10
    img.draw_line(center_x - cross_size, center_y, center_x + cross_size, center_y, color=(255, 255, 255))
    img.draw_line(center_x, center_y - cross_size, center_x, center_y + cross_size, color=(255, 255, 255))

    detected_objects = []
    # 遍历每种颜色的阈值
    for i, threshold in enumerate(color_thresholds):
        # 在图像中查找符合当前颜色阈值的色块
        blobs = img.find_blobs(threshold, pixels_threshold=200, area_threshold=200, merge=True)

        # 遍历找到的每个色块
        for blob in blobs:
            # 获取色块的宽度和高度
            blob_width = blob.w()
            blob_height = blob.h()
            # 计算色块的宽高比，用于判断是否接近圆形
            aspect_ratio = min(blob_width, blob_height) / max(blob_width, blob_height)

            # 如果宽高比大于0.8，认为是接近圆形的色块
            if aspect_ratio > 0.8:
                # 获取色块的中心坐标
                blob_x = blob.cx()
                blob_y = blob.cy()
                # 计算色块的近似半径
                radius = int((blob_width + blob_height) / 4)

                # 在图像上绘制圆形轮廓，颜色为对应颜色
                img.draw_circle(blob_x, blob_y, radius, color=color_colors[i], thickness=2)
                # 在圆心位置绘制颜色名称
                img.draw_string(blob_x, blob_y, color_names[i], color=(255, 255, 255))

                # 计算色块中心相对于图像中心的坐标
                relative_x = blob_x - center_x
                relative_y = blob_y - center_y

                detected_objects.append((color_codes[i], relative_x, relative_y))

    # 检查是否到了发送数据的时间
    current_time = time.ticks_ms()
    if current_time - last_send_time >= SEND_INTERVAL:
        if detected_objects:
            for color_code, relative_x, relative_y in detected_objects:
                # 按照包头、颜色代号、坐标、包尾的格式组织数据
                payload = "{},{},{}".format(color_code, relative_x, relative_y).encode('utf-8')
                data_to_send = bytearray([0xFF]) + payload + bytearray([0xFE])
                serial.send_bytearray(data_to_send)
        else:
            # 当检测不到物体时，发送颜色代码为0，坐标为(0, 0)的数据
            payload = "{},{},{}".format(0, 0, 0).encode('utf-8')
            data_to_send = bytearray([0xFF]) + payload + bytearray([0xFE])
            serial.send_bytearray(data_to_send)
        last_send_time = current_time

    # 在LCD屏幕上显示处理后的图像
    lcd.display(img)
