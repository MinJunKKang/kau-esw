import time
import random
from colorsys import hsv_to_rgb
import board
from digitalio import DigitalInOut, Direction
from PIL import Image, ImageDraw, ImageFont
from adafruit_rgb_display import st7789
import numpy as np
from collections import deque

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

joystick = Joystick()
my_image = Image.new("RGB", (joystick.width, joystick.height)) #도화지!
my_draw = ImageDraw.Draw(my_image) #그리는 도구!

class Ball:
    def __init__(self, spawn_position, size = 5):
        self.appearance = 'circle'
        self.state = None
        self.items_queue = deque()
        self.position = np.array([spawn_position[0] - size, spawn_position[1] - size, spawn_position[0] + size, spawn_position[1] + size])
        self.speed = 3
        self.velocity = 0
        self.acceleration = 1
        self.outline = "#000000"
        self.bottom_floor_ranges = []
        self.size = size
        self.stage = 0

    # 죽은 경우에
    def reset_game(self, spawn_position):
        self.items_queue.clear()
        self.velocity = 0
        self.set_position((spawn_position[0], spawn_position[1]))

    def set_position(self, spawn_position, size = 5):
        self.position = np.array([spawn_position[0] - size, spawn_position[1] - size, spawn_position[0] + size, spawn_position[1] + size])

    def move(self, command=None):
        self.velocity += self.acceleration
        self.position[3] += self.velocity
        self.position[1] += self.velocity

        if command['move'] == False:
            self.state = None
        else:
            self.state = 'move'
            if command['left_pressed']:
                self.position[0] -= self.speed
                self.position[2] -= self.speed
            if command['right_pressed']:
                self.position[0] += self.speed
                self.position[2] += self.speed

        # shoot 아이템을 위해 만든 조건
        if self.speed > 3:
            self.speed -= self.acceleration

        # 왼쪽 벽에 부딪히는지 확인
        self.check_left_collision()

        # 오른쪽 벽에 부딪히는지 확인
        self.check_right_collision()
        
        # 바닥에 부딪히는지 확인
        self.check_bottom_collision()
        
        # 라즈베리 파이의 높이보다 낮아지면 다시 시작
        if self.position[3] >= 240:
            self.state = 'die'

        if not joystick.button_A.value:
            self.state = 'die'


        # 아이템 사용을 queue로 구현
        if self.items_queue and not joystick.button_B.value:
            current_item = self.items_queue[0]
            current_item.use(self)
            self.items_queue.popleft()

    # 바닥들을 정의해주는 코드
    def set_bottom_floor_ranges(self, bottom_floor_ranges):
        self.bottom_floor_ranges = bottom_floor_ranges

    # 바닥 부딪힘 확인 함수 정의
    def check_bottom_collision(self):
        for bottom_floor_range in self.bottom_floor_ranges:
            x_range, y_value = bottom_floor_range
            if (
                x_range[0] <= (self.position[0] + self.position[2]) / 2  < x_range[1]
                and self.position[3] >= y_value[0]
                and self.position[1] <= y_value[1]
            ):
                # 시간이 안맞아서 바닥 위에서 튕기지 않아 위치를 수정해주는 코드를 추가
                self.position[3] = y_value[0]
                self.position[1] = y_value[0] - 2 * self.size
                self.velocity = -9

    # 벽의 왼쪽에 충돌 확인 함수
    def check_left_collision(self):
        for bottom_floor_range in self.bottom_floor_ranges:
            x_range, y_range = bottom_floor_range
            if (
            self.position[2] >= x_range[0]  # 현재 위치의 오른쪽이 벽의 왼쪽보다 크거나 같을 때
            and self.position[0] <= x_range[0]
            and self.position[1] >= y_range[0]
            and self.position[3] <= y_range[1]
            ):
                self.position[0] = x_range[0] - 3 * self.size 
                self.position[2] = x_range[0] - self.size
    
    def check_right_collision(self):
        for bottom_floor_range in self.bottom_floor_ranges:
            x_range, y_range = bottom_floor_range
            if (
            self.position[0] <= x_range[1]  # 현재 위치의 왼쪽이 벽의 오른쪽보다 작거나 같을 때
            and self.position[2] >= x_range[1]
            and self.position[1] >= y_range[0]
            and self.position[3] <= y_range[1]
            ):
                self.position[0] = x_range[1] + self.size
                self.position[2] = x_range[1] + 3 * self.size


    # 아이템과의 충돌을 확인하기 위한 코드, TA-ESW의 코드 활용
    def collision_check(self, items):
        for item in items:
            collision = self.overlap(self.position, item.position)
            if collision:
                self.items_queue.append(item)
                items.remove(item)
    # 위와 마찬가지
    def overlap(self, ego_position, other_position):
        return (
            ego_position[0] < other_position[2]
            and ego_position[1] < other_position[3]
            and ego_position[2] > other_position[0]
            and ego_position[3] > other_position[1]
        )
    
class Item:
    def __init__(self, spawn_position, size = 12, image_path=None):
        self.appearance = 'image'
        self.state = True
        self.position = np.array([spawn_position[0] - size, spawn_position[1] - size, spawn_position[0] + size, spawn_position[1] + size])
        self.outline = "#00FF00"
        self.is_collected = False
        self.image = None

        # 만약 image_path가 존재한다면 그걸 사용해라
        if image_path:
            self.image = Image.open(image_path)

    def use(self, ball):
        self.is_collected = True

# 점프아이템에 대한 정의
class Jump(Item):
    def __init__(self, spawn_position):
        super().__init__(spawn_position, image_path="/home/kau-esw/esw/MJ-ESW/0_Test/Jump.png")

    #높게 뛰게
    def use(self, ball):
        super().use(ball)
        ball.velocity = -9

# 슛아이템에 대한 정의
class Shoot(Item):
    def __init__(self, spawn_position):
        super().__init__(spawn_position, image_path="/home/kau-esw/esw/MJ-ESW/0_Test/Shoot.png")

    # 빠르게 날아가기
    def use(self, ball):
        super().use(ball)
        ball.speed = 11
        ball.velocity -= 3

class Teleport(Item):
    def __init__(self, spawn_position, command = None):
        super().__init__(spawn_position, image_path="/home/kau-esw/esw/MJ-ESW/0_Test/Teleport.png")

    def use(self, ball):
        super().use(ball)
        if command['left_pressed']:
            ball.position[0] -= 20
            ball.position[2] -= 20
        if command['right_pressed']:
            ball.position[0] += 20
            ball.position[2] += 20

class Star(Item):
    def __init__(self, spawn_position):
        super().__init__(spawn_position, image_path="/home/kau-esw/esw/MJ-ESW/0_Test/Star.png")

    def use(self, ball):
        super().use(ball)
        ball.stage += 1

class Dark_Star(Item):
    def __init__(self, spawn_position):
        super().__init__(spawn_position, image_path="/home/kau-esw/esw/MJ-ESW/0_Test/Dark_Star.png")

    def use(self, ball):
        super().use(ball)
        ball.stage += 1

my_circle = Ball((10, 140))


while True:
    if my_circle.stage == 0:
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/Start.png")
        joystick.disp.image(background_image)

    if my_circle.stage == 0 and not joystick.button_A.value:
        # 게임 세계에 아이템 추가
        items = [Shoot((30, joystick.height - 22)), Star((220, joystick.height - 24))]  # 필요한 만큼 추가
        # 배경 이미지 불러오기
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/Tutorial_shoot.png")

        # 바닥 영역 정의
        bottom_floor_ranges = [((0, 60), (230, 240)), ((120,240), (230,240))]
        my_circle.set_bottom_floor_ranges(bottom_floor_ranges)

        while my_circle.stage == 0:

            if my_circle.state == 'die':
                my_circle.reset_game((10,140))
                items = [Shoot((30, joystick.height - 22)), Star((220, joystick.height - 24))]  # 필요한 만큼 추가
                my_circle.state = None

            command = {'move': False, 'left_pressed': False, 'right_pressed': False}

            if not joystick.button_L.value:  # 왼쪽 버튼이 눌린 경우
                command['left_pressed'] = True
                command['move'] = True

            if not joystick.button_R.value:  # 오른쪽 버튼이 눌린 경우
                command['right_pressed'] = True
                command['move'] = True

            my_circle.move(command)
            my_circle.collision_check(items)  # 아이템과의 충돌 확인 및 아이템 사용
            
                
            # 배경 이미지로 설정
            my_image.paste(background_image, (0, 0))
            

            # 아이템을 가지고 있다면 주황색으로, 아니면 노란색으로
            if my_circle.items_queue:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 165, 0, 255))
            else:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 255, 0))


            # 아이템 그리기
            for _item in items:
                if not _item.is_collected:
                    # 아이템 이미지를 그리기
                    if _item.image:
                        my_image.paste(_item.image, (int(_item.position[0]), int(_item.position[1])))
                    else:
                        my_draw.rectangle(tuple(_item.position), outline=_item.outline, fill=None)

            # Update display
            joystick.disp.image(my_image)

    if my_circle.stage == 1:
        
        
        # 게임 세계에 아이템 추가
        items = [Star((30, joystick.height - 24)), Jump((200, joystick.height - 22))]  # 필요한 만큼 추가

        # 배경 이미지 불러오기
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/Tutorial_jump.png")

        # 바닥 영역 정의
        bottom_floor_ranges = [((0, 116), (230,239)), ((116, 157), (166,239)), ((116,239), (230, 239))]

        my_circle.set_bottom_floor_ranges(bottom_floor_ranges)

        my_circle.set_position((230,140))
        my_circle.velocity = 0

        while my_circle.stage == 1:

            if my_circle.state == 'die':
                my_circle.reset_game((230,140))
                items = [Star((30, joystick.height - 24)), Jump((200, joystick.height - 22))]  # 필요한 만큼 추가
                my_circle.state = None

            if my_circle.state == 'die':
                items = [Shoot((30, joystick.height - 22)), Star((220, joystick.height - 24))]  # 필요한 만큼 추가
                my_circle.state = None
            
            command = {'move': False, 'left_pressed': False, 'right_pressed': False}

            if not joystick.button_L.value:  # 왼쪽 버튼이 눌린 경우
                command['left_pressed'] = True
                command['move'] = True

            if not joystick.button_R.value:  # 오른쪽 버튼이 눌린 경우
                command['right_pressed'] = True
                command['move'] = True

            my_circle.move(command)
            my_circle.collision_check(items)  # 아이템과의 충돌 확인 및 아이템 사용
                
            # 배경 이미지로 설정
            my_image.paste(background_image, (0, 0))
            

            # 아이템을 가지고 있다면 주황색으로, 아니면 노란색으로
            if my_circle.items_queue:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 165, 0, 255))
            else:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 255, 0))


            # 아이템 그리기
            for _item in items:
                if not _item.is_collected:
                    # 아이템 이미지를 그리기
                    if _item.image:
                        my_image.paste(_item.image, (int(_item.position[0]), int(_item.position[1])))
                    else:
                        my_draw.rectangle(tuple(_item.position), outline=_item.outline, fill=None)

            # Update display
            joystick.disp.image(my_image)

    if my_circle.stage == 2:
        
        
        items = [Teleport((150, joystick.height - 22)), Star((220, joystick.height - 24))]  # 필요한 만큼 추가

        # 배경 이미지 불러오기
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/Tutorial_teleport.png")

        # 바닥 영역 정의
        bottom_floor_ranges = [((0, 17), (230, 240)), ((50,60), (230,240)), ((93,103), (230,240)), ((136,240), (230,240)), ((164, 170), (151, 230))]

        my_circle.set_bottom_floor_ranges(bottom_floor_ranges)

        my_circle.set_position((8,140))
        my_circle.velocity = 0

        while my_circle.stage == 2:

            if my_circle.state == 'die':
                my_circle.reset_game((8,140))
                items = [Teleport((150, joystick.height - 22)), Star((220, joystick.height - 24))]  # 필요한 만큼 추가
                my_circle.state = None
                
            command = {'move': False, 'left_pressed': False, 'right_pressed': False}

            if not joystick.button_L.value:  # 왼쪽 버튼이 눌린 경우
                command['left_pressed'] = True
                command['move'] = True

            if not joystick.button_R.value:  # 오른쪽 버튼이 눌린 경우
                command['right_pressed'] = True
                command['move'] = True

            my_circle.move(command)
            my_circle.collision_check(items)  # 아이템과의 충돌 확인 및 아이템 사용
                
                    
            # 배경 이미지로 설정
            my_image.paste(background_image, (0, 0))
                

            # 아이템을 가지고 있다면 주황색으로, 아니면 노란색으로
            if my_circle.items_queue:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 165, 0, 255))
            else:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 255, 0))


            # 아이템 그리기
            for _item in items:
                if not _item.is_collected:
                    # 아이템 이미지를 그리기
                    if _item.image:
                        my_image.paste(_item.image, (int(_item.position[0]), int(_item.position[1])))
                    else:
                        my_draw.rectangle(tuple(_item.position), outline=_item.outline, fill=None)

            # Update display
            joystick.disp.image(my_image)

    

    if my_circle.stage == 3:
        
        
        items = [Teleport((60, joystick.height - 22)), Dark_Star((12, joystick.height - 24)), Teleport((12, joystick.height - 60)), Teleport((100, joystick.height - 22)), Dark_Star((joystick.width / 2, joystick.height / 2)), Shoot((joystick.width - 12, 121))]  # 필요한 만큼 추가

        # 배경 이미지 불러오기
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/map_1.png")

        # 바닥 영역 정의
        bottom_floor_ranges = [((0, 146), (230, 240)), ((147, 158), (218,230)), ((159,170), (206,218)), ((171,182), (194,206)), ((183, 194), (182, 194)), ((195,206), (170,182)), ((207,218), (158,170)), ((219,240), (134,158))
                           , ((26, 31 ), (127, 229)), ((126, 131), (127, 229))]

        my_circle.set_bottom_floor_ranges(bottom_floor_ranges)

        my_circle.set_position((60, 160))
        my_circle.velocity = 0

        while (my_circle.stage == 3 or my_circle.stage == 4):

            if my_circle.state == 'die':
                my_circle.reset_game((60, 160))
                my_circle.stage = 3
                items = [Teleport((60, joystick.height - 22)), Dark_Star((12, joystick.height - 24)), Teleport((12, joystick.height - 60)), Teleport((100, joystick.height - 22)), Dark_Star((joystick.width / 2, joystick.height / 2)), Shoot((joystick.width - 12, 121))]  # 필요한 만큼 추가
                my_circle.state = None
                
            command = {'move': False, 'left_pressed': False, 'right_pressed': False}

            if not joystick.button_L.value:  # 왼쪽 버튼이 눌린 경우
                command['left_pressed'] = True
                command['move'] = True

            if not joystick.button_R.value:  # 오른쪽 버튼이 눌린 경우
                command['right_pressed'] = True
                command['move'] = True

            my_circle.move(command)
            my_circle.collision_check(items)  # 아이템과의 충돌 확인 및 아이템 사용
                
                    
            # 배경 이미지로 설정
            my_image.paste(background_image, (0, 0))
                

            # 아이템을 가지고 있다면 주황색으로, 아니면 노란색으로
            if my_circle.items_queue:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 165, 0, 255))
            else:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 255, 0))


            # 아이템 그리기
            for _item in items:
                if not _item.is_collected:
                    # 아이템 이미지를 그리기
                    if _item.image:
                        my_image.paste(_item.image, (int(_item.position[0]), int(_item.position[1])))
                    else:
                        my_draw.rectangle(tuple(_item.position), outline=_item.outline, fill=None)

            # Update display
            joystick.disp.image(my_image)

    if my_circle.stage == 5:
        
        
        # 게임 세계에 아이템 추가
        items = [Jump((120, 217)), Jump((220, 140)), Jump((180, 105)), Jump((220, 70)), Shoot((180, 35)), Shoot((120, 70)), Jump((90, 70)), Dark_Star((20, 50))]  # 필요한 만큼 추가

        # 배경 이미지 불러오기
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/map_2.png")

        # 바닥 영역 정의
        bottom_floor_ranges = [((0, 240), (230, 240))]

        my_circle.set_bottom_floor_ranges(bottom_floor_ranges)

        my_circle.set_position((60, 160))
        my_circle.velocity = 0

        while my_circle.stage == 5:

            if my_circle.state == 'die':
                my_circle.reset_game((60, 160))
                items = [Jump((120, 217)), Jump((220, 140)), Jump((180, 105)), Jump((220, 70)), Shoot((180, 35)), Shoot((120, 70)), Jump((90, 70)), Dark_Star((20, 50))]  # 필요한 만큼 추가
                my_circle.state = None
                
            command = {'move': False, 'left_pressed': False, 'right_pressed': False}

            if not joystick.button_L.value:  # 왼쪽 버튼이 눌린 경우
                command['left_pressed'] = True
                command['move'] = True

            if not joystick.button_R.value:  # 오른쪽 버튼이 눌린 경우
                command['right_pressed'] = True
                command['move'] = True

            my_circle.move(command)
            my_circle.collision_check(items)  # 아이템과의 충돌 확인 및 아이템 사용
                
                    
            # 배경 이미지로 설정
            my_image.paste(background_image, (0, 0))
                

            # 아이템을 가지고 있다면 주황색으로, 아니면 노란색으로
            if my_circle.items_queue:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 165, 0, 255))
            else:
                my_draw.ellipse(tuple(my_circle.position), outline=my_circle.outline, fill=(255, 255, 0))


            # 아이템 그리기
            for _item in items:
                if not _item.is_collected:
                    # 아이템 이미지를 그리기
                    if _item.image:
                        my_image.paste(_item.image, (int(_item.position[0]), int(_item.position[1])))
                    else:
                        my_draw.rectangle(tuple(_item.position), outline=_item.outline, fill=None)

            # Update display
            joystick.disp.image(my_image)

    if my_circle.stage == 6:
        background_image = Image.open("/home/kau-esw/esw/MJ-ESW/0_Test/Finish.png")
        joystick.disp.image(background_image)
        
        if not joystick.button_B.value:
            my_circle.state = 'die'
            my_circle.stage = 0