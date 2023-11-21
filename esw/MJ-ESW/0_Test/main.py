import time
import random
from colorsys import hsv_to_rgb
import board
from digitalio import DigitalInOut, Direction
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7789
import numpy as np

class Joystick:
    def __init__(self):
        self.cs_pin = DigitalInOut(board.CE0)
        self.dc_pin = DigitalInOut(board.D25)
        self.reset_pin = DigitalInOut(board.D24)
        self.BAUDRATE = 24000000

        self.spi = board.SPI()
        self.disp = st7789.ST7789(
                    self.spi,
                    height=240,
                    y_offset=80,
                    rotation=180,
                    cs=self.cs_pin,
                    dc=self.dc_pin,
                    rst=self.reset_pin,
                    baudrate=self.BAUDRATE,
                    )

        # Input pins:
        self.button_A = DigitalInOut(board.D5)
        self.button_A.direction = Direction.INPUT

        self.button_B = DigitalInOut(board.D6)
        self.button_B.direction = Direction.INPUT

        self.button_L = DigitalInOut(board.D27)
        self.button_L.direction = Direction.INPUT

        self.button_R = DigitalInOut(board.D23)
        self.button_R.direction = Direction.INPUT

        self.button_U = DigitalInOut(board.D17)
        self.button_U.direction = Direction.INPUT

        self.button_D = DigitalInOut(board.D22)
        self.button_D.direction = Direction.INPUT

        self.button_C = DigitalInOut(board.D4)
        self.button_C.direction = Direction.INPUT

        # Turn on the Backlight
        self.backlight = DigitalInOut(board.D26)
        self.backlight.switch_to_output()
        self.backlight.value = True

        # Create blank image for drawing.
        # Make sure to create image with mode 'RGB' for color.
        self.width = self.disp.width
        self.height = self.disp.height

class Ball:
    def __init__(self, width, height):
        self.appearance = 'circle'
        self.state = None
        self.has_jump_item = False
        self.has_shoot_item = False
        self.position = np.array([width/2 - 8, height/2 - 8, width/2 + 8, height/2 + 8])
        self.speed = 5
        self.velocity = 0
        self.acceleration = 1
        self.outline = "#000000"

    def move(self, command = None):
        self.velocity += self.acceleration
        self.position[3] += self.velocity
        self.position[1] += self.velocity

        if (self.position[3] >= 240 and self.velocity > 0):
            self.velocity = -10

        if self.has_jump_item and not joystick.button_B.value:
            self.velocity = -10
            self.has_jump_item = False

        if self.has_shoot_item and not joystick.button_B.value:
            self.speed = 10
            self.has_shoot_item = False

        if command['move'] == False:
            self.state = None
            self.outline = "#000000" #검정색상 코드!
        
        else:
            self.state = 'move'
            self.outline = "#000000" #빨강색상 코드!
                
            if command['left_pressed']:
                self.position[0] -= self.speed
                self.position[2] -= self.speed
                
            if command['right_pressed']:
                self.position[0] += self.speed
                self.position[2] += self.speed

    def collision_check(self, items):
        for item in items:
            collision = self.overlap(self.position, item.position)

            if collision:
                item.use(self)
                items.remove(item)
                    

    def overlap(self, ego_position, other_position):
        return ego_position[0] > other_position[0] and ego_position[1] > other_position[1] \
            and ego_position[2] < other_position[2] and ego_position[3] < other_position[3]

class Item:
    def __init__(self, spawn_position):
        self.appearance = 'rectangle'
        self.position = np.array([spawn_position[0] - 25, spawn_position[1] - 25, spawn_position[0] + 25, spawn_position[1] + 25])
        self.outline = "#00FF00"
        self.is_collected = False

    def use(self, ball):
        self.is_collected = True
        ball.has_jump_item = True

class Jump(Item):
    pass

class Shoot(Item):
    pass

joystick = Joystick()
my_image = Image.new("RGB", (joystick.width, joystick.height)) #도화지!
my_draw = ImageDraw.Draw(my_image) #그리는 도구!

my_circle = Ball(joystick.width, joystick.height)
my_draw.rectangle((0, 0, joystick.width, joystick.height), fill=(255, 255, 255, 100))

# 게임 세계에 Jump 아이템 추가
items = [Jump((200, 200)), Shoot((0, 200))]  # 필요한 만큼 추가

while True:
    command = {'move': False, 'up_pressed': False, 'down_pressed': False, 'left_pressed': False, 'right_pressed': False}

    if not joystick.button_L.value:  # 왼쪽 버튼이 눌린 경우
        command['left_pressed'] = True
        command['move'] = True

    if not joystick.button_R.value:  # 오른쪽 버튼이 눌린 경우
        command['right_pressed'] = True
        command['move'] = True

    my_circle.move(command)
    my_circle.collision_check(items)  # 아이템과의 충돌 확인 및 아이템 사용

    # 그리기 로직 (순서가 중요함)
    my_draw.rectangle((0, 0, joystick.width, joystick.height), fill=(255, 255, 255, 100))
    my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 255, 0))

    # Jump 아이템 그리기
    for jump_item in items:
        if not jump_item.is_collected:
            my_draw.rectangle(tuple(items.position), outline=items.outline, fill=None)

    # Update display
    joystick.disp.image(my_image)