import time

# 初始化游戏参数和变量
snake = [(0, 1), (0, 2)]      # 蛇的身体位置列表，初始为两节身体在第一列第二行和第三行
food_position = (3, 4)       # 食物的位置，默认在第4行，第5列（从0开始计数）
directions = {0: 'up', 1: 'down', 2: 'left', 3: 'right'}   # 移动方向映射表
speed = {'slow': 0.5, 'medium': 0.2, 'fast': 0.1}           # 游戏速度
delay_time = speed['medium']                                   

# 游戏逻辑函数
def game():
    global snake
    
    print('贪吃蛇游戏开始！按任意键继续')
    input()
    
    while True:
        display_game_state()
        
        if collision_detected():   # 判断是否与边界或自己身体发生碰撞
            print('游戏结束！')
            break
            
        move_snake()              # 移动蛇
        
        snake.insert(0, tuple((snake[-1][0], snake[-1][1] + directions[last_direction])))    # 添加新部分到蛇头
                
        if (food_position == tuple((pos[0], pos[1]))):     # 检查是否吃到食物
            print('吃到了！生成新的食物...')
        else:
            snake.pop()                                  # 如果没吃到，移除蛇尾

def display_game_state():
    global food_position, snake
    
    board = [['-'] * 7 for _ in range(6)]                 # 创建游戏板状数组（6行7列）
    
    for pos in snake:                                     # 填充蛇身体
        board[pos[0]][pos[1]] = 'O'
        
    board[food_position[0]][food_position[1]] = '*'       # 添加食物位置
    
    print('\n'.join([' '.join(row) for row in zip(*board)]))   # 打印游戏状态
    
def move_snake():
    global snake, last_direction
    
    last_direction = snake[-1][1] - snake[-2][1]
    
    if last_direction == 0:
        snake.append((snake[-1][0], snake[-1][1] + 1))
    elif last_direction == 1:
        snake.append((snake[-1][0], snake[-1][1] - 1))
    elif last_direction == 2:
        snake.append((snake[-1][0] - 1, snake[-1][1]))
    else:                                                   # last_direction == 3
        snake.append((snake[-1][0] + 1, snake[-1][1]))

def collision_detected():
    global snake
    
    head_position = snake[0]
    
    return (head_position in snake[1:]) or \
           (head_position[0] < 0 or head_position[0] >= 6) or \
           (head_position[1] < 0 or head_position[1] >= 7)

if __name__ == '__main__':
    game()
